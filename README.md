# megaraidstat

## Installation

```bash
pip3 install git@gitlab.com:daverona/python/megaraidcli  # installation
# pip3 remove megaraidstat  # uninstallation
```

## Use

```bash
sudo megaraidstat --help

# usage: megaraidstat [-h] [--version] [--path PATH] [--no-color] [--predict] [--check] [--event] [--event-filters EVENT_FILTERS] [--event-type EVENT_TYPE]
# 
# options:
#   -h, --help            show this help message and exit
#   --version             Show version
#   --path PATH           Specify storcli executable path.
#   --no-color            Do not use color.
#   --predict             Check if failure is predicted.
#   --check               Check if configuration is sane.
#   --event               Show event logs.
#   --event-filters EVENT_FILTERS
#                         Specify comma separated filters for event logs. Available filters are: info, warning, critical, fatal
#   --event-type EVENT_TYPE
#                         Specify a type of event logs. Available types are: includedeleted, sinceshutdown, sincereboot, latest=N, "ccincon vd=0,1,2..."
```

```bash
sudo megaraidstat
# sudo megaraidstat --no-color  # monochrome version

# CONTROLLERS
# +-----+-----------------------------------------------------+-------+------+--------+-------+-------------------------+
# | CID | Controller (serial, firmware)                       |   RAM |  Tpr | BBU    | Alarm | Clock (controller)      |
# +-----+-----------------------------------------------------+-------+------+--------+-------+-------------------------+
# | /c0 | LSI MegaRAID SAS 9267-8i (XXXXXXXXXX, XXXXXXXXXXXX) | 512MB | 255C | Absent | On    | Mon 2023-10-30 04:07:07 |
# +-----+-----------------------------------------------------+-------+------+--------+-------+-------------------------+
# CONTROLLER SCHEDULES
# +-----+-------------------+-----------+------------+-----------+-------------------------+-------------------------+---------+
# | CID | Task              | Excl VIDs | Mode       |     Delay | Next start (system)     | Next start (controller) | Status  |
# +-----+-------------------+-----------+------------+-----------+-------------------------+-------------------------+---------+
# | /c0 | Consistency Check |           | Concurrent | 720 hours | Tue 2023-11-21 01:00:03 | Mon 2023-11-20 16:00:00 | Stopped |
# | /c0 | Patrol Read       |           | Auto       | 168 hours | Sat 2023-11-04 01:00:03 | Fri 2023-11-03 16:00:00 | Stopped |
# +-----+-------------------+-----------+------------+-----------+-------------------------+-------------------------+---------+
# ENCLOSURES
# +----------+--------------------------+-----------+--------+------+------+
# | EID      | Enclosure (serial, rev.) | Type      | Status | #Slt | #Dsk |
# +----------+--------------------------+-----------+--------+------+------+
# | /c0/e252 | LSI SGPIO (N/A, N/A)     | Backplane | OK     |    8 |    8 |
# +----------+--------------------------+-----------+--------+------+------+
# VIRTUAL DISKS
# +--------+-------+-----------+------+--------+----------+----------+---------+-----------+----------+--------+-------------+
# | VID    | Type  |      Size | #Dsk | StrpSz | CacheFlg | DskCache | Status  | CacheCade | Path     | Name   | In progress |
# +--------+-------+-----------+------+--------+----------+----------+---------+-----------+----------+--------+-------------+
# | /c0/v0 | RAID6 | 43.661 TB |    8 |  64 KB | R/AWB/D  | Default  | Optimal |           | /dev/sda | backup |             |
# +--------+-------+-----------+------+--------+----------+----------+---------+-----------+----------+--------+-------------+
# # R=Read Ahead Always,NR=No Read Ahead/WB=Write Back,AWB=Always Write Back,WT=Write Through/C=Cached IO,D=Direct IO
# PHYSICAL DISKS IN VIRTUAL DISKS
# +--------+-------------+------------------------------------+------+-----+----------+--------+------+---------+---------+-----+-----+------+--------------------+
# | VID    | SID         | Disk (serial)                      | Intf | Med |     Size | Status | Spun | DiskSpd | LinkSpd | Tpr | DID | #PFA | Topology           |
# +--------+-------------+------------------------------------+------+-----+----------+--------+------+---------+---------+-----+-----+------+--------------------+
# | /c0/v0 | /c0/e252/s0 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 33C |  18 |    0 | dg=0 array=0 row=0 |
# | /c0/v0 | /c0/e252/s1 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 34C |  17 |    0 | dg=0 array=0 row=1 |
# | /c0/v0 | /c0/e252/s2 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 34C |  15 |    0 | dg=0 array=0 row=2 |
# | /c0/v0 | /c0/e252/s3 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 35C |  16 |    0 | dg=0 array=0 row=3 |
# | /c0/v0 | /c0/e252/s4 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 33C |  14 |    0 | dg=0 array=0 row=4 |
# | /c0/v0 | /c0/e252/s5 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 33C |  13 |    0 | dg=0 array=0 row=5 |
# | /c0/v0 | /c0/e252/s6 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 34C |  12 |    0 | dg=0 array=0 row=6 |
# | /c0/v0 | /c0/e252/s7 | WDC WD80EAZZ-00BKLB0 (WD-XXXXXXXX) | SATA | HDD | 7.276 TB | Online | Up   | 6.0Gb/s | 6.0Gb/s | 34C |  11 |    0 | dg=0 array=0 row=7 |
# +--------+-------------+------------------------------------+------+-----+----------+--------+------+---------+---------+-----+-----+------+--------------------+
# PHYSICAL DISKS OUT OF VIRTUAL DISKS
# +-----+---------------+------+-----+------+--------+------+---------+---------+-----+-----+------+-----+
# | SID | Disk (serial) | Intf | Med | Size | Status | Spun | DiskSpd | LinkSpd | Tpr | DID | #PFA | Fgn |
# +-----+---------------+------+-----+------+--------+------+---------+---------+-----+-----+------+-----+
# | No data available                                                                                    |
# +-----+---------------+------+-----+------+--------+------+---------+---------+-----+-----+------+-----+
# EVENT LOGS
# +-----+------------+-------------------------+----------+--------------------------------------+------+-------------------------+
# | CID | SeqNum     |     Event time (system) | Severity | Description                          | Data | Event time (controller) |
# +-----+------------+-------------------------+----------+--------------------------------------+------+-------------------------+
# | /c0 | 0x0000675d | Sat 2023-10-28 15:40:43 | INFO     | Patrol Read complete                 |      | Sat 2023-10-28 06:40:40 |
# | /c0 | 0x0000675c | Sat 2023-10-28 01:00:03 | INFO     | Patrol Read started                  |      | Fri 2023-10-27 16:00:00 |
# | /c0 | 0x0000675b | Fri 2023-10-27 20:02:12 | INFO     | Consistency Check aborted on VD 00/0 | More | Fri 2023-10-27 11:02:09 |
# | /c0 | 0x0000675a | Fri 2023-10-27 20:02:12 | INFO     | Consistency Check aborted on VD 00/0 | More | Fri 2023-10-27 11:02:09 |
# | /c0 | 0x00006759 | Fri 2023-10-27 19:58:26 | INFO     | Consistency Check resumed on VD 00/0 | More | Fri 2023-10-27 10:58:23 |
# +-----+------------+-------------------------+----------+--------------------------------------+------+-------------------------+
# # CRITICAL=error without data loss,FATAL=error with possible data loss,FAULT=catastropic hardware failure
```

```bash
sudo megaraidstat --event
# sudo megaraidstat --event --event-type="latest=10"  # the most recent ten log entries
```

```bash
sudo megaraidstat --check
```

## References

* https://docs.broadcom.com/doc/12352476
* https://raw.githubusercontent.com/eLvErDe/hwraid/master/wrapper-scripts/megaclisas-status
* https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797#colors--graphics-mode
* https://stackoverflow.com/a/44307814
* https://techdocs.broadcom.com/content/dam/broadcom/techdocs/data-center-solutions/tools/generated-pdfs/StorCLI-12Gbs-MegaRAID-Tri-Mode.pdf
* https://techdocs.broadcom.com/content/dam/broadcom/techdocs/data-center-solutions/tools/generated-pdfs/12Gbs-MegaRAID-Tri-Mode-Software.pdf
* https://www.dell.com/support/kbdoc/en-us/000127841/dell-perc-controller-disk-patrol-read
* https://slowkow.com/notes/raid-fix/
