#!/usr/bin/env python3

# Author: daverona
# Inspired by megaclisas-status
# @see https://raw.githubusercontent.com/eLvErDe/hwraid/master/wrapper-scripts/megaclisas-status

import argparse
import datetime
import functools
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser


storcli_path = None
colorize = True
cdata = None
edata = None
vdata = None
sdata = None
time_difference_data = None
slot_to_topology_data = None
slot_to_virtual_disk_data = None
slot_to_foreign_config_data = None
controller_schedule_data = None


###############################################################################
# API calls
###############################################################################


def standardize(data, key_name='Ctrl_Prop', value_name='Value'):
    # [ { key_name: k, value_name: v }, ... ] => { k: v, ... }
    return { e[key_name]: e[value_name] for e in data }


def storcli_call(command, text=False):
    suffix = ' nolog' if text else ' J nolog'
    proc = subprocess.Popen([storcli_path + ' ' + command + suffix], stdout=subprocess.PIPE, shell=True)
    (stdout, stderr) = proc.communicate()
    return stdout.decode('utf-8') if text else json.loads(stdout)


def controller_count_json():
    return storcli_call('show ctrlcount')


def controller_json():
    global cdata
    if not cdata: cdata = storcli_call('/call show all')
    return cdata


def time_difference_json():
    global time_difference_data
    if not time_difference_data:
        time_difference_data = {}
        cdata = controller_json()
        for controller in _get(cdata, 'Controllers', []):
            cid = getcid(controller)
            controller_clock = strstrip(_get(controller, 'Response Data.Basics.Current Controller Date/Time', None))
            system_clock = strstrip(_get(controller, 'Response Data.Basics.Current System Date/time', None))
            diff = None
            if controller_clock is not None and controller_clock != 'None' and system_clock is not None and system_clock != 'None':
                diff = parse_datetime(system_clock) - parse_datetime(controller_clock)
            time_difference_data[cid] = diff  # datetime.timedelta object
    return time_difference_data


def slot_to_topology_json():
    global slot_to_topology_data
    if not slot_to_topology_data:
        slot_to_topology_data = {}
        cdata = controller_json()
        for controller in _get(cdata, 'Controllers', []):
            cid = getcid(controller)
            for e in _get(controller, 'Response Data.TOPOLOGY', {}):
                try:
                    (eid, sid) = e['EID:Slot'].split(':')
                    key = f'{cid}/e{eid}/s{sid}'
                    value = f'dg={e["DG"]} array={e["Arr"]} row={e["Row"]}'
                    slot_to_topology_data[key] = value
                except:
                    continue
    return slot_to_topology_data


def controller_schedule_json():
    global controller_schedule_data
    if not controller_schedule_data: controller_schedule_data = storcli_call('/call show cc pr')
    return controller_schedule_data


def enclosure_json():
    global edata
    if not edata: edata = storcli_call('/call/eall show all')
    return edata


def virtual_disk_json():
    global vdata
    global slot_to_virtual_disk_data
    if not vdata: vdata = storcli_call('/call/vall show all')
    return vdata


def slot_to_virtual_disk_json():
    global slot_to_virtual_disk_data
    if not slot_to_virtual_disk_data:
        slot_to_virtual_disk_data = {}
        vdata = virtual_disk_json()
        for controller in _get(vdata, 'Controllers', []):
            cid = getcid(controller)
            for k, v in _get(controller, 'Response Data', {}).items():
                if re.match('^/c\d+/v\d+$', k):
                    vid = k
                elif re.match('^PDs for VD \d+$', k):
                    for p in v:
                        (eid, sid) = p['EID:Slt'].split(':')
                        key = f'{cid}/e{eid}/s{sid}'
                        slot_to_virtual_disk_data[key] = vid
    return slot_to_virtual_disk_data


def virtual_disk_operation_json(vid, operation):
    return storcli_call(f'{vid} show {operation}')


def slot_json():
    global sdata
    if not sdata: sdata = storcli_call('/call/eall/sall show all')
    return sdata


def slot_to_foreign_config_json():
    global slot_to_foreign_config_data
    if not slot_to_foreign_config_data:
        slot_to_foreign_config_data = {}
        fdata = storcli_call(f'/call/fall show all')
        for controller in _get(fdata, 'Controllers', []):
            cid = getcid(controller)
            for t in _get(controller, 'Response Data.Foreign Topology', []):
                sid = wordmap(t['EID:Slot'])
                if sid != '' and t['State'] == 'Frgn':
                    (eid, sid) = sid.split(':')
                    key = f'{cid}/e{eid}/s{sid}'
                    slot_to_foreign_config_data[key] = True
    return slot_to_foreign_config_data


def event_text(cid, filters=None, type=None):
    filters = '' if not filters else f' filter={filters}'
    type = '' if not type else f' type="{type}"'
    return storcli_call(f'{cid} show events' + type + filters, True)


def getcid(controller):
    cid = _get(controller, 'Command Status.Controller', None)
    return '' if cid == None else f'/c{cid}'


###############################################################################
# Color functions
###############################################################################


'''
@see https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797#colors--graphics-mode
+---------------+---------+---------+
|               | set     | reset   | 
+---------------+---------+---------+
| reset         | ESC[0m  | ESC[0m  |
| bold          | ESC[1m  | ESC[21m |
| dim           | ESC[2m  | ESC[22m |
| underline     | ESC[4m  | ESC[24m |
| blinking      | ESC[5m  | ESC[25m |
| inverse       | ESC[7m  | ESC[27m |
| strikethrough | ESC[9m  | ESC[29m |
+---------------+---------+---------+
|               |    fore |   back  | 
+---------------+---------+---------+
| black         | ESC[30m | ESC[40m |
| red           | ESC[31m | ESC[41m |
| green         | ESC[32m | ESC[42m |
| yellow        | ESC[33m | ESC[43m |
| blue          | ESC[34m | ESC[44m |
| magenta       | ESC[35m | ESC[45m |
| cyan          | ESC[36m | ESC[46m |
| white         | ESC[37m | ESC[47m |
| default       | ESC[39m | ESC[49m |
+---------------+---------+---------+
'''

code_escape = '\033'
code_reset = f'{code_escape}[0m'
code_bold = f'{code_escape}[1m'
code_dim = f'{code_escape}[2m'
code_inverse = f'{code_escape}[7m'
code_green = f'{code_escape}[32m'
code_yellow = f'{code_escape}[33m'
code_red = f'{code_escape}[31m'


ansi_color_code = {
    'text': '',
    'info': code_green,
    'warn': code_yellow,
    'error': code_red,
    'fatal': code_red + code_inverse,
}


def mark_text(text, tag=None): return text if not tag else f'<{tag}>{text}</{tag}>'


def color_text(text, tag=None):
    lower_tag = tag.lower()
    if (not colorize) or (lower_tag not in ansi_color_code): return text
    return f'{code_bold}{ansi_color_code[lower_tag]}{text}{code_reset}'


class ColorTagParser(HTMLParser):
    ''' 
    There are two cases on which this parser cannot handle the input:
    1. emptry string (e.g. '')
    2. tags with empty string (e.g. <blah></blah>)

    To handle the first case, feed is overriden.
    To handle the second case, self.curr_data is defined and checked in handle_endtag.
    '''
    def __init__(self):
        super().__init__()
        self.parsed = []
        self.curr_tag = None
        self.curr_data = None

    def feed(self, text):
        super().feed(text)
        if text == '': self.parsed = [['', None]]

    def handle_starttag(self, tag, attrs):
        if self.curr_tag is not None:
            print('Cannot process malformed tags.', file=sys.stderr)
            sys.exit(1)
        self.curr_tag = tag

    def handle_data(self, data):
        self.parsed.append([data, self.curr_tag])
        self.curr_data = data

    def handle_endtag(self, tag):
        if self.curr_tag != tag:
            print('Cannot process malformed tags.', file=sys.stderr)
            sys.exit(1)
        if self.curr_data is None:
            self.parsed.append(['', self.curr_tag])
        self.curr_tag = None
        self.curr_data = None


def parse_mark_text(text):
    parser = ColorTagParser()
    parser.feed(text)
    return parser.parsed


def mark_to_color(text):
    p = parse_mark_text(text)
    return functools.reduce(lambda r, e: r + (e[0] if not e[1] else color_text(e[0], e[1])), p, '')


def mark_text_len(text):
    p = parse_mark_text(text)
    return functools.reduce(lambda r, e: r + len(e[0]), p, 0)


def justify_mark_text(text, width, char=' ', just='left'):
    strtext = str(text)
    count = width - mark_text_len(strtext)
    if count == 0: return strtext
    p = parse_mark_text(strtext)
    if just == 'left' or just == 'l':
        if not p[-1][1]: pos = len(strtext)
        else: pos = (len(strtext) - (len(p[-1][1]) + 3))
    elif just == 'right' or just == 'r':
        if not p[0][1]: pos = 0
        else: pos = len(p[0][1]) + 2
    return strtext[0:pos] + (char * count) + strtext[pos:]


###############################################################################
# Information processing
###############################################################################


default_words = {
    '': '',
    '-': '',
    'None': '',
}


def strstrip(s): return str(s).strip()


def wordmap(s, words=default_words): 
    dictionary = { **words, **default_words }
    return s if s not in dictionary else dictionary[s]


def delcols(cols, header, aligns, values):
    indices = sorted([header.index(col) for col in cols], reverse=True)
    for index in indices:
        header.pop(index)
        aligns.pop(index)
        [v.pop(index) for v in values]


def parse_datetime(s):
    for format in ['%m/%d/%Y, %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%c']:
        try: return datetime.datetime.strptime(s, format)
        except: continue
    return s


def parse_to_system_datetime(cid, s):
    time_difference_data = time_difference_json()
    if cid not in time_difference_data or not time_difference_data[cid]: return s
    return parse_datetime(s) + time_difference_data[cid]

def format_datetime(s, fine_resolution=True):
    if not fine_resolution: return s.strftime('%a %Y-%m-%d %H')
    return s.strftime('%a %Y-%m-%d %H:%M:%S')


def parse_duration(s):
    match = re.match(r'\s*((?P<days>-?\d+) day[s]?)?\s*((?P<hours>-?\d+) hour[s]?)?\s*((?P<minutes>-?\d+) minute[s]?)?\s*', s, re.IGNORECASE)
    if match: return { **{ 'days': None, 'hours': 0, 'minutes': 0, 'seconds': 0 }, **{ k: int(v) for k, v in match.groupdict().items() if v }}


def format_duration(s):
    return ('' if not s['days'] else f'{s["days"]}d ') + f'{str(s["hours"]).rjust(2, "0")}:{str(s["minutes"]).rjust(2, "0")}:{str(s["seconds"]).rjust(2, "0")}'


def _get(o, k, d=''):
    # Inspired by lodash _.get()
    r = o
    for key in k.split('.'):
        try: r = r[key]
        except:
            if not (isinstance(r, list) or isinstance(r, tuple)): return d
            try:
                if len(r) >= int(key): r = r[int(key)]
                else: return d
            except: return d
    return r


def convert_to_bytes(size_string):
    # @see https://stackoverflow.com/a/44307814
    short_suffixes = [f'{e}b' for e in ['', 'k', 'm', 'g', 't', 'p', 'e', 'z']]
    long_suffixes = [f'{e}byte' for e in ['', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa', 'zetta', 'yotta']]
    multipliers = {**{f'{i}': 1024 ** p for p, i in enumerate(short_suffixes)}, **{f'{i}': 1024 ** p for p, i in enumerate(long_suffixes)}}
    size_regex = re.compile("\s*(\d*[\.]?\d*)\s*({})s?\s*".format('|'.join(short_suffixes + long_suffixes)), re.IGNORECASE)
    def subst(m): return str(float(m.group(1)) * multipliers[m.group(2).lower()])

    return float(size_regex.sub(subst, size_string))


def get_controller_info():
    header = ['CID', 'Controller (serial, firmware)', 'RAM', 'Tpr', 'BBU', 'Alarm', 'Clock (system)', 'Clock (controller)']
    aligns = ['l', 'l', 'r', 'r', 'l', 'l', 'l', 'l']
    values = []
    footer = []

    cdata = controller_json()
    for controller in _get(cdata, 'Controllers', []):
        cid = getcid(controller)
        r = _get(controller, 'Response Data', {})
        controller_model = strstrip(_get(r, 'Basics.Model'))
        controller_serial_number = strstrip(_get(r, 'Basics.Serial Number'))
        controller_firmware_version = strstrip(_get(r, 'Version.Firmware Package Build'))
        controller_clock = strstrip(_get(r, 'Basics.Current Controller Date/Time'))
        system_clock = strstrip(_get(r, 'Basics.Current System Date/time'))
        ram = strstrip(_get(r, 'HwCfg.On Board Memory Size'))
        temperature = strstrip(_get(r, 'HwCfg.Ctrl temperature(Degree Celsius)', strstrip(_get(r, 'HwCfg.ROC temperature(Degree Celsius)'))))
        bbu = strstrip(_get(r, 'HwCfg.BBU'))
        if bbu == 'Present': bbu = 'Good' if 0 == _get(r, 'Status.BBU Status') else mark_text('Bad', 'error')
        alarm = strstrip(_get(r, 'HwCfg.Alarm'))
        # Sanitize
        if controller_clock != '': controller_clock = format_datetime(parse_datetime(controller_clock))
        if system_clock != '': system_clock = format_datetime(parse_datetime(system_clock))
        if temperature != '': temperature = f'{temperature}C'
        if alarm == 'Disable': alarm = 'Disabled'
        # Colorize
        if alarm == 'Disabled': alarm = mark_text(alarm, 'warn')
        # Register
        values.append([cid, f'{controller_model} ({controller_serial_number}, {controller_firmware_version})', ram, temperature, bbu, alarm, system_clock, controller_clock])

    # Filter columns
    delcols(['Clock (system)'], header, aligns, values)
    values = sorted(values, key=lambda e: e[0])
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


def get_controller_schedule_info():
    header = ['CID', 'Task', 'Excl VIDs', 'Mode', 'Delay', 'Next start (system)', 'Next start (controller)', 'Status']
    aligns = ['l', 'l', 'l', 'l', 'r', 'l', 'l', 'l']
    values = []
    footer = []

    time_difference_data = time_difference_json()
    controller_schedule_data = controller_schedule_json()
    for controller in _get(controller_schedule_data, 'Controllers', []):
        cid = getcid(controller)
        r = standardize(_get(controller, 'Response Data.Controller Properties', []))
        if len(r) == 0: continue
        cc_name = 'Consistency Check'
        cc_mode = r['CC Operation Mode']
        cc_delay = r['CC Execution Delay']
        cc_next_controller = cc_next_system = r['CC Next Starttime']
        cc_status = r['CC Current State']
        cc_exclusion = wordmap(r['CC Excluded VDs'])
        cc_iterations = r['CC Number of iterations']  # the number of consistency checks ever done
        cc_done_vds = r['CC Number of VD completed']  # the number of virtual disks done consistency check
        pr_name = 'Patrol Read'
        pr_mode = 'Disabled' if r['PR Mode'] == 'Disable' else r['PR Mode']
        pr_delay = r['PR Execution Delay']
        pr_next_controller = pr_next_system = r['PR Next Start time']
        pr_status = r['PR Current State']
        pr_exclusion = wordmap(r['PR Excluded VDs'])
        pr_iterations = r['PR iterations completed']                                        # the number of patrol reads every done
        if pr_status.startswith('Active'): (pr_status, pr_done_pds) = pr_status.split(' ')  # the number of physical disks done patrol read
        # The *number* following "Active" in PR Current State is the number of physical disks done patrol read
        # @see https://techdocs.broadcom.com/content/dam/broadcom/techdocs/data-center-solutions/tools/generated-pdfs/StorCLI-12Gbs-MegaRAID-Tri-Mode.pdf
        # Sanitize
        if cc_exclusion != '': cc_exclusion = ', '.join([f'{cid}/v{e}' for e in cc_exclusion.split(',')])
        if pr_exclusion != '': pr_exclusion = ', '.join([f'{cid}/v{e}' for e in pr_exclusion.split(',')])
        # The total number of physical disks for patrol read however is not fixed at all. Some are excluded for various reason.
        # If this wasn't true, I wish to print like this: "s/t physical disk(s) done", where t is the total number of disks to patrol read.
        # @see https://www.dell.com/support/kbdoc/en-us/000127841/dell-perc-controller-disk-patrol-read
        if cc_status.startswith('Active'): cc_status = cc_status + ' (' + ('no' if cc_done_vds == '0' else cc_done_vds) + ' VDs done)'
        if pr_status.startswith('Active'): pr_status = pr_status + ' (' + ('no' if pr_done_pds == '0' else pr_done_pds) + ' PDs done)'
        if cc_next_controller != '':
            cc_next_controller = format_datetime(parse_datetime(cc_next_controller))
            cc_next_system = format_datetime(parse_to_system_datetime(cid, cc_next_system))
        if pr_next_controller != '':
            pr_next_controller = format_datetime(parse_datetime(pr_next_controller))
            pr_next_system = format_datetime(parse_to_system_datetime(cid, pr_next_system))
        # Colorize
        if cc_status.startswith('Active'): cc_status = mark_text(cc_status, 'info')
        if pr_status.startswith('Active'): pr_status = mark_text(pr_status, 'info')
        elif pr_status.startswith('Paused'): pr_status = mark_text(pr_status, 'warn')
        # Register
        values.append([cid, cc_name, cc_exclusion, cc_mode, cc_delay, cc_next_system, cc_next_controller, cc_status])
        values.append([cid, pr_name, pr_exclusion, pr_mode, pr_delay, pr_next_system, pr_next_controller, pr_status])

    values = sorted(values, key=lambda e: e[0])
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


def get_enclosure_info():
    header = ['EID', 'Enclosure (serial, rev.)', 'Type', 'Status', '#Slt', '#Dsk']
    aligns = ['l', 'l', 'l', 'l', 'r', 'r']
    values = []
    footer = []

    edata = enclosure_json()
    for controller in _get(edata, 'Controllers', []):
        r = _get(controller, 'Response Data', {})
        for k, v in r.items():
            if re.match('^Enclosure /c\d+/e\d+\s*$', k):
                eid = k.split(' ')[1]
                vendor = strstrip(_get(v, 'Inquiry Data.Vendor Identification'))
                product = strstrip(_get(v, 'Inquiry Data.Product Identification'))
                serial_number = strstrip(_get(v, 'Information.Enclosure Serial Number'))
                if serial_number == '': serial_number = 'N/A'
                revision = strstrip(_get(v, 'Inquiry Data.Product Revision Level'))
                device = strstrip(_get(v, 'Information.Device Type'))
                status = strstrip(_get(v, 'Properties.0.State'))
                slots = _get(v, 'Properties.0.Slots')
                disks = _get(v, 'Properties.0.PD')
                # Colorize
                # Register
                values.append([eid, f'{vendor} {product} ({serial_number}, {revision})', device, status, slots, disks])

    values = sorted(values, key=lambda e: e[0])
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


def get_virtual_disk_operation_info(vid):
    op_words = {
        'BGI': 'Background Initialization',
        'CC': 'Consistency Check',
        'ERASE': 'Erasure',
        'Migrate': 'Migration',
        'INIT': 'Initialization',
    }

    operations = [
        virtual_disk_operation_json(vid, 'bgi'),
        virtual_disk_operation_json(vid, 'cc'),
        virtual_disk_operation_json(vid, 'erase'),
        virtual_disk_operation_json(vid, 'init'),
        virtual_disk_operation_json(vid, 'migrate'),
    ]

    values = []
    for op in operations:
        operation = wordmap(strstrip(_get(op, 'Controllers.0.Response Data.VD Operation Status.0.Operation', '')), op_words)
        status = strstrip(_get(op, 'Controllers.0.Response Data.VD Operation Status.0.Status', ''))
        time_left = strstrip(_get(op, 'Controllers.0.Response Data.VD Operation Status.0.Estimated Time Left', None))
        if time_left: time_left = format_duration(parse_duration(time_left))
        progress = strstrip(_get(op, 'Controllers.0.Response Data.VD Operation Status.0.Progress%', None))
        # Colorize
        if status == 'In progress': values.append(mark_text(f'{operation} ({progress}%, {time_left} left)', 'info'))
        elif status == 'Paused': values.append(mark_text(f'{operation} (paused)', 'warn'))
    return values


def get_virtual_disk_info():
    vd_words = {
        "Disk's Default": 'Default',
        'Optl': 'Optimal',
        'Dgrd': 'Degraded',
    }

    header = ['VID', 'Type', 'Size', '#Dsk', 'StrpSz', 'CacheFlg', 'DskCache', 'Status', 'CacheCade', 'Path', 'Name', 'In progress']
    aligns = ['l', 'l', 'r', 'r', 'r', 'l', 'l', 'l', 'l', 'l', 'l', 'l']
    values = []
    footer = []

    vdata = virtual_disk_json()
    for controller in _get(vdata, 'Controllers', []):
        r = _get(controller, 'Response Data', {})
        for k, v in r.items():
            if re.match('^/c\d+/v\d+$', k):
                vid = k
                raid_type = strstrip(_get(v, '0.TYPE'))
                size = strstrip(_get(v, '0.Size'))
                cache_flags = strstrip(_get(v, '0.Cache'))
                cache_flags = re.sub('R', 'R/', re.sub('C', '/C', re.sub('D', '/D', cache_flags)))
                status = wordmap(strstrip(_get(v, '0.State')), vd_words)
                name = strstrip(_get(v, '0.Name'))
                cachecade = wordmap(strstrip(_get(v, '0.Cac')))
            elif re.match('^PDs for VD \d+$', k):
                disks = len(v)
            elif re.match('^VD\d+ Properties$', k):
                strip_size = strstrip(_get(v, 'Strip Size'))
                disk_cache = wordmap(strstrip(_get(v, 'Disk Cache Policy')), vd_words)
                path = wordmap(strstrip(_get(v, 'OS Drive Name')))
                #operations = wordmap(strstrip(_get(v, 'Active Operations')))
                operations = ', '.join(get_virtual_disk_operation_info(vid))
                # Sanitize
                # Colorize
                if status == 'Degraded': status = mark_text(status, 'warn')
                # Register
                values.append([vid, raid_type, size, disks, strip_size, cache_flags, disk_cache, status, cachecade, path, name, operations])

    values = sorted(values, key=lambda e: e[0])
    footer = ['R=Read Ahead Always,NR=No Read Ahead/WB=Write Back,AWB=Always Write Back,WT=Write Through/C=Cached IO,D=Direct IO']
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


def get_physical_disk_info(configured=None):
    pd_words = {
        'U': 'Up',
        'D': 'Down',
        'Onln': 'Online',
        'Offln': 'Offline',
        'Rbld': 'Rebuild',
        'Sntze': 'Sanitize',
        'GHS': 'Global Hot Spare',
        'DHS': 'Dedicated Hot Spare',
        'UGood': 'Unconfigured Good',
        'UBad': 'Unconfigured Bad',
    }

    header = ['VID', 'SID', 'Disk (serial)', 'Intf', 'Med', 'Size', 'Status', 'Spun', 'DiskSpd', 'LinkSpd', 'Tpr', 'DID', '#PFA', 'Topology', 'Fgn']
    aligns = ['l', 'l', 'l', 'l', 'l', 'r', 'l', 'l', 'r', 'r', 'r', 'r', 'r', 'l', 'l']
    values = []
    footer = []

    slot_to_virtual_disk_data = slot_to_virtual_disk_json()
    slot_to_topology_data = slot_to_topology_json()
    slot_to_foreign_config_data = slot_to_foreign_config_json()
    sdata = slot_json()
    for controller in _get(sdata, 'Controllers', []):
        r = _get(controller, 'Response Data', {})
        for k, v in r.items():
            if re.match('^Drive /c\d+/e\d+/s\d+$', k):
                sid = k[6:]
                vid = '' if sid not in slot_to_virtual_disk_data else slot_to_virtual_disk_data[sid]
                interface = strstrip(_get(v, '0.Intf'))
                media = strstrip(_get(v, '0.Med'))
                disk_model = re.sub('\s\s+', ' ', strstrip(_get(v, '0.Model')))
                size = strstrip(_get(v, '0.Size'))
                status = wordmap(strstrip(_get(v, '0.State')), pd_words)
                spun = wordmap(strstrip(_get(v, '0.Sp')), pd_words)
                did = _get(v, '0.DID')
            elif re.match('^Drive /c\d+/e\d+/s\d+ - Detailed Information$', k):
                disk_manufacturer = strstrip(_get(v, f'Drive {sid} Device attributes.Manufacturer Id'))
                disk_manufacturer = '' if disk_manufacturer == 'ATA' else f'{disk_manufacturer} '
                disk_serial_number = strstrip(_get(v, f'Drive {sid} Device attributes.SN'))
                #disk_firmware_version = strstrip(_get(v, f'Drive {sid} Device attributes.Firmware Revision'))
                speed = strstrip(_get(v, f'Drive {sid} Device attributes.Device Speed'))
                link_speed = strstrip(_get(v, f'Drive {sid} Device attributes.Link Speed'))
                temperature = strstrip(_get(v, f'Drive {sid} State.Drive Temperature')).split(' ')[0]
                predictive_failure = _get(v, f'Drive {sid} State.Predictive Failure Count')
                topology = '' if sid not in slot_to_topology_data else slot_to_topology_data[sid]
                foreign = '' if sid not in slot_to_foreign_config_data else 'Yes'
                # Colorize
                if status == 'Rebuild': status = mark_text(status, 'warn')
                elif status == 'Unconfigured Bad': status = mark_text(status, 'warn')
                if predictive_failure >= 1: predictive_failure = mark_text(predictive_failure, 'info')
                if foreign != '': foreign = mark_text(foreign, 'warn')
                # Filter
                if configured is True and vid == '': continue
                if configured is False and vid != '': continue
                # Register
                values.append([vid, sid, f'{disk_manufacturer}{disk_model} ({disk_serial_number})', interface, media, size, status, spun, speed, link_speed, temperature, did, predictive_failure, topology, foreign])

    if configured is False:
        delcols(['VID', 'Topology'], header, aligns, values)
    if configured is True:
        delcols(['Fgn'], header, aligns, values)
        values = sorted(values, key=lambda e: e[0])
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


###############################################################################
# Sanity check
###############################################################################


checklist_dict = {
    'W001': {
        'text': 'BBU is either absent or good on {cid}.',
        'action': [
            'sudo {storcli_path} {cid}/bbu show status', 
            'sudo {storcli_path} {cid} show batterywarning', 
            'Replace BBU on {cid} if needed.',
        ],
    },
    'W002': {
        'text': 'Alarm is either absent or on in {cid}.',
        'action': ['sudo {storcli_path} {cid} set alarm=on']
    },
    'W003': {
        'text': 'Auto rebuild option is on in {cid}.',
        'action': ['sudo {storcli_path} {cid} set autorebuild=on']
    },
    'W004': {
        'text': 'No two tasks are schueduled to run at the same time on {cid}.',
        'action': ['sudo {storcli_path} {cid} set [task] starttime="yyyy/mm/dd hh"']
    },
    'W005': {
        'text': 'Consistency check is recommended not to run too often (less than 30 days) on {cid}.',
        'action': ['sudo {storcli_path} {cid} set consistencycheck delay=720']
    },
    'W006': {
        'text': 'Patrol read is recommended not to run too often (less than a week) on {cid}.',
        'action': ['sudo {storcli_path} {cid} set patroread delay=168']
    },
    'I001': {
        'text': 'Multiple virtual disks are recommended to be named.',
        'action': ['sudo {storcli_path} /cx/vx set name="[name]"']
    },
    'I002': {
        'text': 'Write-back is recommended for write cache policy on {vid} if connected to a failure-free power source.',
        'action': [
            mark_text('WARNING', 'error') + ': Do NOT run the following command if NOT connected to a failure-free power source.',
            'sudo {storcli_path} {vid} set wrcache=wb|awb',
        ]
    },
}


def sanity_check():
    checklist = []

    cdata = controller_json()
    for controller in _get(cdata, 'Controllers', []):
        cid = getcid(controller)
        r = _get(controller, 'Response Data', {})
        bbu = strstrip(_get(r, 'HwCfg.BBU'))
        if bbu == 'Present': bbu = _get(r, 'Status.BBU Status')
        alarm = strstrip(_get(r, 'HwCfg.Alarm', 'On'))
        if alarm == 'Disable': alarm = 'Disabled'
        auto_rebuild = strstrip(_get(r, 'Policies.Auto Rebuild', 'On'))

        # W001
        passed = not (bbu != 'Absent' and bbu != 0 and bbu != '')
        checklist.append({ 'key': 'W001', 'pass': passed, 'params': { 'cid': cid } })

        # W002
        passed = not (alarm == 'Disabled')
        checklist.append({ 'key': 'W002', 'pass': passed, 'params': { 'cid': cid } })

        # W003
        passed = not (auto_rebuild != 'On')
        checklist.append({ 'key': 'W003', 'pass': passed, 'params': { 'cid': cid } })

    controller_schedule_data = controller_schedule_json()
    schedules = {}
    for controller in _get(controller_schedule_data, 'Controllers', []):
        cid = getcid(controller)
        r = _get(controller, 'Response Data.Controller Properties', {})
        (cc_mode, cc_delay, cc_next, pr_mode, pr_delay, pr_next) = (None,) * 6
        for e in r:
            k = _get(e, 'Ctrl_Prop', '')
            v = strstrip(_get(e, 'Value', ''))
            if k == '': continue
            elif k == 'CC Operation Mode': cc_mode = v
            elif k == 'CC Execution Delay': cc_delay = int(v.split(' ')[0])
            elif k == 'CC Next Starttime': cc_next = v
            elif k == 'PR Mode': pr_mode = 'Disabled' if v == 'Disable' else v
            elif k == 'PR Execution Delay': pr_delay = int(v.split(' ')[0])
            elif k == 'PR Next Start time': pr_next = v
        schedules[cid] = { 'cc_mode': cc_mode, 'cc_next': cc_next, 'pr_mode': pr_mode, 'pr_next': pr_next }

        # W004
        passed = not (cc_mode is not None and cc_mode != 'Disabled' and pr_mode is not None and pr_mode != 'Disabled' and cc_next != None and cc_next == pr_next)
        checklist.append({ 'key': 'W004', 'pass': passed, 'params': { 'cid': cid } })

        # W005
        passed = not (cc_mode is not None and cc_mode != 'Disabled' and cc_delay is not None and cc_delay < 720)
        checklist.append({ 'key': 'W005', 'pass': passed, 'params': { 'cid': cid } })

        # W006
        passed = not (pr_mode is not None and pr_mode != 'Disabled' and pr_delay is not None and pr_delay < 168)
        checklist.append({ 'key': 'W006', 'pass': passed, 'params': { 'cid': cid } })

    vdata = virtual_disk_json()
    virtual_disk_names = []
    for controller in _get(vdata, 'Controllers', []):
        cid = getcid(controller)
        r = _get(controller, 'Response Data', {})
        for k, v in r.items():
            if re.match('^/c\d+/v\d+$', k):
                vid = k
                name = strstrip(_get(v, '0.Name'))
                virtual_disk_names.append(name)
                cache_flags = strstrip(_get(v, '0.Cache'))
                cache_flags = re.sub('R', 'R/', re.sub('C', '/C', re.sub('D', '/D', cache_flags)))
                write_policy = cache_flags.split('/')[1]

                # I002
                passed = True if write_policy == 'AWB' or write_policy == 'WB' else None
                checklist.append({ 'key': 'I002', 'pass': passed, 'params': { 'vid': vid } })
    # I001
    passed = not (len(virtual_disk_names) >= 2 and len(list(filter(lambda e: e is None or e == '', virtual_disk_names))) >= 1)
    checklist.append({ 'key': 'I001', 'pass': passed })

    def compare(x, y):
        order = { 'F': 0, 'E': 1, 'W': 2, 'I': 3 }
        k1, s1 = x['key'][0], int(x['key'][1:])
        k2, s2 = y['key'][0], int(y['key'][1:])
        return s1 - s2 if k1 == k2 else order[k1] - order[k2]

    checklist = sorted(checklist, key=functools.cmp_to_key(compare))
    return checklist


###############################################################################
# Predictive failure
###############################################################################


# TODO: Find the equivalent command for this: megacli64 -AdpAllInfo -aALL | grep "Critical Disk"
# TODO: Find the equivalent command for this: megacli64 -AdpAllInfo -aALL | grep "Failed Disk"

def get_predictive_failure():
    predictive_failure_counts = {}

    sdata = slot_json()
    for controller in _get(sdata, 'Controllers', []):
        r = _get(controller, 'Response Data', {})
        for k, v in r.items():
            if re.match('^Drive /c\d+/e\d+/s\d+$', k):
                sid = k[6:]
            elif re.match('^Drive /c\d+/e\d+/s\d+ - Detailed Information$', k):
                predictive_failure = _get(v, f'Drive {sid} State.Predictive Failure Count')
                if predictive_failure == 0: continue
                predictive_failure_counts[sid] = predictive_failure

    return predictive_failure_counts


###############################################################################
# Event logs
###############################################################################


severity = {
    '-1': 'progress',  # Progress message. No user action is necessary.
    '0': 'info',       # Informational message. No user action is necessary.
    '1': 'warning',    # Some component might be close to a failure point.
    '2': 'critical',   # A component has failed, but the system has not lost data.
    '3': 'fatal',      # A component has failed, and data loss has occurred or will occur.
    '4': 'fault',      # The I/O Unit faulted due to a catastrophic error.
}


def get_event_logs(cid, event_filters, event_type):
    ignores = ['', '===========', 'None']
    event_terminator = 'CLI Version ='

    header = ['CID', 'SeqNum', 'Event time (system)', 'Severity', 'Description', 'Data', 'Code', 'Locl', 'Event time (controller)']
    aligns = ['l', 'l', 'r', 'l', 'l', 'l', 'l', 'l', 'r']
    values = []
    footer = [
        # @see https://techdocs.broadcom.com/content/dam/broadcom/techdocs/data-center-solutions/tools/generated-pdfs/12Gbs-MegaRAID-Tri-Mode-Software.pdf
        'CRITICAL=error without data loss,FATAL=error with possible data loss,FAULT=catastropic hardware failure',
    ]

    if cid.endswith('all'):
        controller_count = controller_count_json()
        controller_count = int(_get(controller_count, 'Controllers.0.Response Data.Controller Count', 0))    
        cids = [f'/c{c}' for c in range(controller_count)]
    else: cids = [cid]

    for cid in cids:
        event_data = event_text(cid, event_filters, event_type)
        events = []
        entry = None
        handling_event_data = False

        for line in event_data.splitlines():
            line = line.strip()
            if line in ignores: continue
            if line.startswith(event_terminator): break

            try:
                split = line.split(':')
                (key, v) = (split[0], ':'.join(split[1:]).strip())
            except: (key, v) = [line, '']

            if key == 'seqNum': # next event starts
                if entry is not None: events.append(entry)  # save previous entry
                entry = { 'seq_num': None, 'time': None, 'system_clock': None, 'code': None, 'level': None, 'locale': None, 'description': None, 'data': [] }
                handling_event_data = False
                entry['seq_num'] = v
            elif key == 'Time':
                entry['time'] = format_datetime(parse_datetime(v))
                entry['system_clock'] = format_datetime(parse_to_system_datetime(cid, v))
            elif key == 'Seconds since last reboot':
                entry['time'] = f'{v} secs (since reboot)'
                entry['system_clock'] = entry['time']
            elif key == 'Code': entry['code'] = v
            elif key == 'Class':
                s = _get(severity, v, f'unknown ({v})')
                # @see https://techdocs.broadcom.com/content/dam/broadcom/techdocs/data-center-solutions/tools/generated-pdfs/12Gbs-MegaRAID-Tri-Mode-Software.pdf
                if s == 'progress': s = mark_text(s, 'text')
                elif s == 'info': s = mark_text(s, 'info')
                elif s == 'warning': s = mark_text(s, 'warn')
                elif s == 'critical': s = mark_text(s, 'error')
                elif s == 'fatal': s = mark_text(s, 'fatal')
                elif s == 'fault': s = mark_text(s, 'fatal')
                else: s = mark_text(s, 'fatal')
                entry['severity'] = s.upper()
            elif key == 'Locale': entry['locale'] = v
            elif key == 'Event Description': entry['description'] = ellipsis(v, 80)
            elif key == 'Event Data': handling_event_data = True
            elif handling_event_data: entry['data'].append(line)
        if entry is not None: events.append(entry)  # save previous entry

        #print(json.dumps(events, indent=2))

        values.extend([[cid, e['seq_num'], e['system_clock'], e['severity'], e['description'], 'More' if len(e['data']) else '', e['code'], e['locale'], e['time']] for e in events])

    # Filter columns
    delcols(['Code', 'Locl'], header, aligns, values)
    return { 'header': header, 'aligns': aligns, 'values': values, 'footer': footer }


###############################################################################
# Data formatters
###############################################################################


def ellipsis(s, bound, suffix='...'): return s if len(str(s)) <= bound else str(s)[:bound - len(suffix)] + suffix

def format_table(title, header, aligns, values, footer, sep_index=None):
    def pad_values(v, char=' '):
        padded = []
        for i in range(len(header)):
            justified = justify_mark_text(v[i], widths[i], char, aligns[i])
            padded.append(justified)
        return padded

    widths = [len(s) for s in header]
    for v in values:
        lwidths = [mark_text_len(str(s)) for s in v]
        widths = [max(widths[i], lwidths[i]) for i in range(len(widths))]

    divider = '+-' + '-+-'.join(pad_values(['-'] * len(header), '-')) + '-+'

    # title
    if title: print(mark_to_color(mark_text(title.upper(), 'text')))
    print(divider)

    # header 
    colorized = [mark_to_color(c) for c in pad_values(header)]
    print('| ' + ' | '.join(colorized) + ' |')
    print(divider)

    # body
    for i, v in enumerate(values):
        if sep_index is not None and i != 0 and values[i - 1][sep_index] != values[i][sep_index]:
            print(divider)
        colorized = [mark_to_color(c) for c in pad_values(v)]
        print('| ' + ' | '.join(colorized) + ' |')
    if len(values) == 0:
        text = 'No data available'.ljust(len(divider) - 4)
        print('| ' + text  + ' |')
    print(divider)

    # footer
    bullet = '#'
    for line in footer: print(bullet + ' ' + line)


def format_checklist(checklist):
    for check in checklist:
        key = check['key']
        passed = check['pass']
        params = { **_get(check, 'params', {}), **{ 'storcli_path': storcli_path } }
        item = checklist_dict[key]
        text = item['text'].format(**params)
        action = [f.format(**params) for f in _get(item, 'action', [])]

        if passed is not True:
            text = mark_text(text, 'text')
            if key.startswith('I'): key = mark_text(key, 'info')
            elif key.startswith('W'): key = mark_text(key, 'warn')
            elif key.startswith('E'): key = mark_text(key, 'error')
            elif key.startswith('F'): key = mark_text(key, 'fatal')

        print(f'[{mark_to_color(key)}] {mark_to_color(text)}')
        if passed: continue
        for m in action: print(' ' * (mark_text_len(key) + 3) + f'# {mark_to_color(m)}')


def format_predictive_failure(prediction):
    if len(prediction) == 0: return
    # @see https://slowkow.com/notes/raid-fix/
    print(json.dumps(prediction, indent=2))
    print(f'#')
    print(f'# Checking disk status')
    print(f'#')
    print(f'# sudo {storcli_path} /cx show nolog                  # Show degraded virtual disks and rebuilding physical disks (**)')
    print(f'# sudo {storcli_path} /cx/ex/sx show rebuild nolog    # Show rebuild task progress if it is configured to do so')
    print(f'#')
    print(f'# Relacing failed disks in array')
    print(f'#')
    print(f'# sudo {storcli_path} /cx set alarm=silence           # Stop the beeping noises')
    print(f'# sudo {storcli_path} /cx/ex/sx start locate nolog    # Start blinking the failed disk LED')
    print(f'# sudo {storcli_path} /cx/ex/sx set offline           # Set the failed disk offline')
    print(f'# sudo {storcli_path} /cx/ex/sx set missing           # Set the failed disk missing')
    print(f'# sudo {storcli_path} /cx/ex/sx set spindown          # Spin down the failed disk')
    print(f'# Replace the failed disk with a new one with same model.')
    print(f'# sudo {storcli_path} /cx/ex/sx stop locate nolog     # Stop blinking the failed disk LED')
    print(f'#')
    print(f'# REBUILD TASK SHOULD START AUTOMATICALLY. IF NOT, DO "Rebuilding disk array" BELOW AND COME BACK TO THE NEXT LINE.')
    print(f'#')
    print(f'# sudo {storcli_path} /cx set alarm=on                # Start the beeping noises for failure')
    print(f'# sudo {storcli_path} /cx/ex/sx show rebuild nolog    # Monitor rebuild task progress')
    print(f'# sudo {storcli_path} /cx show nolog                  # Show virtual disks and physical disks')
    print(f'#')
    print(f'# Rebuilding disk array')
    print(f'# Do NOT do the following steps if rebuilding is in progress.')
    print(f'#')
    print(f'# sudo {storcli_path} /cx/ex/sx insert dg= array= row=  # Note. dg, array, row correspond to DG, Arr, Row in TOPOLOGY table in (**) above.')
    print(f'# sudo {storcli_path} /cx/ex/sx start rebuild nolog     # Show rebuild task progress')
    print(f'# sudo {storcli_path} /cx set autorebuild=on nolog      # Set autorebuild on for heaven\'s sake')


###############################################################################
# Driver
###############################################################################


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', help='Specify storcli executable path.', default=None)
    parser.add_argument('--no-color', help='Do not use color.', action='store_true', default=False)
    parser.add_argument('--predict', help='Check if failure is predicted.', action='store_true', default=False)
    parser.add_argument('--check', help='Check if configuration is sane.', action='store_true', default=False)
    parser.add_argument('--event', help='Show event logs.', action='store_true', default=False)
    parser.add_argument('--event-filters', help='Specify comma separated filters for event logs. Available filters are: info, warning, critical, fatal', default=None)
    parser.add_argument('--event-type', help='Specify a type of event logs. Available types are: includedeleted, sinceshutdown, sincereboot, latest=N, "ccincon vd=0,1,2..."', default='latest=100')
    args = parser.parse_args()
    global colorize
    colorize = not args.no_color
    return args


def find_storcli_executable(user_executable):
    def executable(f): return os.path.isfile(f) and os.access(f, os.X_OK)

    global storcli_path
    if user_executable:
        realpath = os.path.realpath(os.path.expanduser(user_executable))
        if not os.path.isfile(realpath): return 127
        if not os.access(realpath, os.X_OK): return 126
        storcli_path = realpath
        return storcli_path

    script_basename = ['storcli64', 'storcli', 'perccli64', 'perccli']
    well_known_paths = ['/opt/MegaRAID/storcli', '/opt/lsi/scorcli', '/opt/MegaRAID/perccli']
    for path in well_known_paths: os.environ['PATH'] += os.pathsep + path
    for basename in script_basename:
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            candidate = os.path.join(path, basename)
            if executable(candidate):
                storcli_path = candidate
                return storcli_path
    return None


#if __name__ == '__main__':
def main():
    args = parse_arguments()
    found = find_storcli_executable(args.path)

    if found is None:
        print('Cannot find storcli executable in your PATH. Please install it.', file=sys.stderr)
        sys.exit(127)
    elif args.path and found == 127:
        print(f'Cannot find {args.path}. Please make sure it exists.', file=sys.stderr)
        sys.exit(127)
    elif args.path and found == 126:
        print(f'Cannot execute {args.path}. Please make sure it is executable.', file=sys.stderr)
        sys.exit(126)
    if os.geteuid() != 0:
        print(f'{storcli_path} requires administrator privileges.', file=sys.stderr)
        sys.exit(5)

    # Good to go

    controller_count = controller_count_json()
    controller_count = int(_get(controller_count, 'Controllers.0.Response Data.Controller Count', 0))
    if controller_count == 0:
        print('Cannot find controllers.')
        quit()

    if args.check:
        format_checklist(sanity_check())
        quit()

    if args.predict:
        format_predictive_failure(get_predictive_failure())
        quit()

    if args.event:
        for c in range(controller_count):
            format_table(f'Event logs: controller {c}', **get_event_logs(f'/c{c}', args.event_filters, args.event_type))
        quit()

    format_table('Controllers', **get_controller_info())
    format_table('Controller schedules', **get_controller_schedule_info())
    format_table('Enclosures', **get_enclosure_info())
    format_table('Virtual disks', **get_virtual_disk_info())
    format_table('Physical disks in virtual disks', **get_physical_disk_info(True), sep_index=0)
    format_table('Physical disks out of virtual disks', **get_physical_disk_info(False))
    format_table('Event logs', **get_event_logs('/call', None, 'latest=5'), sep_index=0)
