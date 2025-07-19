#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        saveUptime.py
# Purpose:     save uptime of the raspberry Pi to csv
#
# Configuration options in config.py
#
# depends on and used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     20.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 15.11.2023: read HOMEPATH from environment
#  PLI, 18.07.2025: changes for python3
#

import sys, os, subprocess

CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME)

from datetime import timedelta, datetime, date
from time import time
from config import CSVPATH

UPTIMEFILE  = CSVPATH + 'uptime.csv'

def save2CSV(csv,atTime,upTime):

    try:
        fout = open(csv, 'a')

        new_rec = "%s,%s\n" % (atTime,upTime)

        fout.write(new_rec)
        fout.close()

    except Exception as e:
        print('Exception occured in function save2CSV. Check your code: %s' % e)

    return


def read_uptime():
    """ get uptime in seconds
          linux  : from /proc
          solaris: kstat
          windows: net stat
    """
    fup = 0.0
    try:
        if (sys.platform == "win32" ):
            import wuptime
            fup = wuptime.uptime()

        elif (sys.platform == "sunos5" ):
            cmd = "kstat -p unix:0:system_misc:boot_time"
            p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (child_stdin, child_stdout) = (p.stdin, p.stdout)
            lines = child_stdout.readlines()

            uptime_val = lines[0].split('\t')[1].strip()

            epoch_time = int(time())
            fup = epoch_time - int(uptime_val)

        elif (sys.platform == "linux2" or sys.platform == "linux"):
            procfile = '/proc/uptime'
            with open(procfile, 'r') as f:
                fup = float(f.readline().split()[0])

            f.close()

        else:
            pass

    except Exception as e:
        print('Exception occured in function read_uptime. Check your code: %s' % e)

    return fup



#-------------------------------------------------------------------------------

def main():

    # current time
    stringdate = datetime.strftime(datetime.now(), '%d.%m.%Y %H:%M:%S')

    # uptime
    uptime_seconds = read_uptime()
    if uptime_seconds > 0.0:
        uptime_string = str(timedelta(seconds = uptime_seconds))
        uptime_hh = "%.2f" % float(uptime_seconds/3600.0)

        print(("save current uptime: at %s this server is %sh up.") % (stringdate,uptime_hh))

        save2CSV(UPTIMEFILE,stringdate,uptime_hh)
    else:
        print("WARN: invalid uptime or unsupported OS.")


if __name__ == '__main__':
    main()
