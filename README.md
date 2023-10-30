# megaraidstat

Inspect disks on MegaRAID controllers.

## Installation

```bash
pip3 install git@gitlab.com:daverona/python/megaraidcli  # installation
# pip3 remove megaraidstat  # uninstallation
```

## How to use

```bash
sudo megaraidstat
# sudo megaraidstat --no-color  # monochrome version

# The output should look like this:
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
# | ...... | ........... | .................................. | .... | ... | ........ | ...... | .... | ....... | ....... | ... | ... | .... | .................. |
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
# | ... | .......... | ....................... | ........ | .................................... | .... | ....................... |
# +-----+------------+-------------------------+----------+--------------------------------------+------+-------------------------+
# # CRITICAL=error without data loss,FATAL=error with possible data loss,FAULT=catastropic hardware failure
```

```bash
sudo megaraidstat --event
# sudo megaraidstat --event --event-type="latest=10"  # the most recent ten log entries

# The output should look like this:
# EVENT LOGS: CONTROLLER 0
# +-----+------------+-------------------------+----------+----------------------------------------------------------------------------------+------+-------------------------+
# | CID | SeqNum     |     Event time (system) | Severity | Description                                                                      | Data | Event time (controller) |
# +-----+------------+-------------------------+----------+----------------------------------------------------------------------------------+------+-------------------------+
# | /c0 | 0x0000675d | Sat 2023-10-28 15:40:43 | INFO     | Patrol Read complete                                                             |      | Sat 2023-10-28 06:40:40 |
# | ... | .......... | ....................... | ........ | ................................................................................ | .... | ....................... |
# +-----+------------+-------------------------+----------+----------------------------------------------------------------------------------+------+-------------------------+
# # CRITICAL=error without data loss,FATAL=error with possible data loss,FAULT=catastropic hardware failure
```

```bash
sudo megaraidstat --check

# The output should look like this:
# [W001] BBU is either absent or good on /c0.
# [W002] Alarm is either absent or on in /c0.
# [W003] Auto rebuild option is on in /c0.
# [W004] No two tasks are schueduled to run at the same time on /c0.
# [W005] Consistency check is recommended not to run too often (less than 30 days) on /c0.
# [W006] Patrol read is recommended not to run too often (less than a week) on /c0.
# [I001] Multiple virtual disks are recommended to be named.
# [I002] Write-back is recommended for write cache policy on /c0/v0 if connected to a failure-free power source.
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
