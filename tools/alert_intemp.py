#!/usr/bin/python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        alert_intemp.py
# Purpose:     send alert if outside temperature is higher than indoor temp.
#
# Configuration options in config.py
#
# depends on and used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
#   needs telegram bot to post message
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     10.08.2020
# Copyright:   (c) Peter Lidauer 2020
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#
# 2022-08-14 - select notification method
#-------------------------------------------------------------------------------

# system modules
import sys,os
import time
from datetime import timedelta, datetime, date
import xml.etree.ElementTree as ET
#
# wospi config
from config import XMLFILE
# telegram
import telegram_send
#
# private subs
sys.path.append('/home/peter/bin')
from send_mail import send_msg_mail
from pytoolslib3 import print_dbg


# temp dir
TMP = '/tmp'
FILE_PREFIX = 'temperatur'
tstfile     = TMP + "/."+FILE_PREFIX+"_send"

DEBUG=False

#-------------------------------------------------------------------------------
def touch(fname):
    try:
        os.utime(fname, None)
    except:
        open(fname, 'a').close()


def notify_by_mail(msg,n_email=True, n_tg=True):

    is_new = False
    if os.path.exists(tstfile):
        statfile = os.stat(tstfile).st_mtime
        now = time.time()
        half_day = now - 60*60*12 # Number of seconds in a half day

        print_dbg(DEBUG,"   #              statfile   - half_day   = diff")
        print_dbg(DEBUG,"   # flag exists, %s - %s = %s." % (statfile,half_day, statfile-half_day))

        if statfile < half_day:
            print_dbg(DEBUG,"   # statfile %s < half_day %s. (removing flag)" % (statfile,half_day))
            is_new = True
            os.unlink(tstfile)
        else:
            is_new = False
            print_dbg(DEBUG,"   # statfile %s > half_day %s." % (statfile,half_day))
    else:
        print_dbg(DEBUG,"   # tstfile does not exist")
        is_new = True


    if is_new:
        if os.path.exists(tstfile):
            print_dbg(DEBUG," %s exists. do not send mail again." % tstfile)
        else:
            if n_email:
                print_dbg(DEBUG,"   # is_new %s => sending email." % (is_new))
                print_dbg(DEBUG," file %s does not exist. sending mail..." % tstfile)
                send_msg_mail(msg, "Close youre windows!",True)

            if n_tg:
                print("Post alert to Telegram")
                telegram_send.send(messages=[msg])

            # add flag
            print_dbg(DEBUG,"   # tstfile does not exist, touching file")
            touch(tstfile)


    return


def read_wxdata(xml,curtime):
    xmlTree = ET.parse(xml)

    #Get the root element in the xml file.
    rootElement = xmlTree.getroot()

    intemp  = 0.0
    outtemp = 0.0
    solar   = 0
    uvval   = 0.0

    # <intemp_c>22.1</intemp_c>
    # <outtemp_c>20.1</outtemp_c>
    # <solar_w>396</solar_w>
    # <uvindex>1.4</uvindex>

    for element in rootElement:
        if element.tag == 'intemp_c':
            intemp = float(element.text)
        elif element.tag == 'outtemp_c':
            outtemp = float(element.text)
        elif element.tag == 'solar_w':
            solar   = int(element.text)
        elif element.tag == 'uvindex':
            uvval = float(element.text)
        else:
            elem_txt = element.text
            #print_dbg(DEBUG,"elem: %s: %s" % (element.tag,elem_txt))


    msg  = ""
    msg += "Indoor : %s°C\n" % intemp
    msg += "Outdoor: %s°C\n" % outtemp
    msg += "Solar  : %sW\n" % solar
    msg += "UV Idx : %s\n" % uvval

    if outtemp >= intemp:
        msg  = "%s\nOutdoor temp. is higher then indoor.\n\nClose your windows!\n\n" % curtime + msg
        #notify_by_mail(msg)
        notify_by_mail(msg, False, True)
    else:
        msg  = "%s\nOutdoor temp. is below %s°C.\n\nYou can keep the windows open.\n" % (curtime,intemp) + msg


    # show values
    print(msg)

    return


#-------------------------------------------------------------------------------

def main():
    # current time
    stringdate = datetime.strftime(datetime.now(), '%d.%m.%Y %H:%M:%S')
    read_wxdata(XMLFILE,stringdate)


if __name__ == '__main__':
    main()
