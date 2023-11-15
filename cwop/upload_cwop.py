#!/usr/bin/env python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        cwop
# Purpose:     upload weather data to CWOP
#
# TNC packet
#  see http://aprs.org/aprs12.html
#      http://wxqa.com/faq.html
#      APRS101.pdf, chapter 12
#
# TNC part 1
# EW8288>APRS,TCPIP*:@131040z4833.82N/01605.50E_
# xWdddd               ... CWOP user
# >APRS,TCPIP*:        ... fix preamble
# @DDHHMMz             ... date hour minute in (UTC)
# DDMM.hhN/DDDMM.hhE_  ... latitude and longitude (LORAN)
#
# TNC part 2
# 240/004g012t047r000p000P000h73b10173L169.WOSPiv20151108-RPi
# ccc    ... wind direction (deg)
# /sss   ... wind speed (mph)
# gggg   ... wind gust (mph)
# tttt   ... temperature (F)
# rrrr   ... rain last hour (1/100inch)
# pppp   ... rain within 24h (1/100inch)
# PPPP   ... rainfall since midnight (1/100inch)
# hhh    ... humidity (%)
# bbbbbb ... air preasure (mb*10)
# LLLL   ... solar radiation, 'l' for > 999 (W/m^2)
# xxxx   ... software and version
#
# if you put "CWOP_ID" in the config file, you don't need
# to provide your id at the commandline
# e.g.: CWOP_ID = 'EW8288'
#
# depends on:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     08.12.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 15.11.2023: read HOMEPATH from environment
#

from __future__ import print_function

import sys,os

CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME + '/')

import socket
import sys
import time
import datetime
import pytz
import re
import csv
import config


# cwop passcode
CWOP_PASS    = '-1'

# software type, version only as fallback
#CWOP_SW_NAME = 'Dvs'
CWOP_SW_NAME = 'WOSPi'
CWOP_SW_VERS = '1.0'

# upload server
CWOP_SRV     = 'cwop.aprs.net'
CWOP_PRT     = '14580'

# TNC preamble
CWOP_FIX = ">APRS,TCPIP*:"


#-------------------------------------------------------------------------------

# for testing, if 'True' no upload happens
# set to 'False' for normal operation
TESTING=False

# just print more information
DEBUG=False

# print upload response messages
TRACE=False

#-------------------------------------------------------------------------------

def split_lonlat(gps_coded):
    """ remove non numeric chars, split gps coordinates in single numeric parts
        http://stackoverflow.com/questions/10852955/python-batch-convert-gps-positions-to-lat-lon-decimals
    """
    # definition is wrong in the above link
    direction = {'N':1, 'S':-1, 'E':1, 'W':-1}
    # tokenize string
    gps_clean = gps_coded.replace(u'°',' ').replace('*', ' ').replace('\'',' ').replace('"',' ')
    gps_clean = gps_clean.split()
    # get wind direction
    gps_clean_dir = gps_clean.pop()
    # fill with zero values for easier calc of decimals
    gps_clean.extend([0,0,0])
    # add numeric factor for winddir
    gps_clean.append(direction[gps_clean_dir])
    gps_clean.append(gps_clean_dir)

    return gps_clean


def DMS2DM_m(DMS):
    """ build GPS string for CWOP record
        http://wxqa.com/faq.html
    """
    # repare string
    dms_l = split_lonlat(DMS)
    wdir_s = dms_l.pop()

    # calculate min from MM'SS"
    min_m = "%05.2f" % (float(dms_l[1]) + (float(dms_l[2])/60.0))

    # pad missing 0s
    # target format "ddmm.hhN/dddmm.hhW"
    if ((wdir_s == 'W') or (wdir_s == 'E')):
        deg = dms_l[0].zfill(3)
    else:
        deg = dms_l[0].zfill(2)

    # build result string
    dms = deg + min_m + wdir_s

    return dms


def get_GPS2DMm(gps):
    """ build GPS string for CWOP record
        combine LAT & LON
    """

    # split into tokens
    LONLAT_s =  gps.split()

    # create latitude and longitude string
    LAT = LONLAT_s[1] + LONLAT_s[0]
    LON = LONLAT_s[3] + LONLAT_s[2]

    # convert to DM.m (for CWOP)
    DM_LAT = DMS2DM_m(LAT)
    DM_LON = DMS2DM_m(LON)

    if DEBUG:
        print("MYPOSITION: %s" % gps)
        print("splitted  : %s" % LONLAT_s)

    # finally build string
    CWOP_STR = DM_LAT + '/' + DM_LON

    return CWOP_STR


def get_constants(prefix):
    """Create a dictionary mapping socket module constants to their names.
       https://pymotw.com/2/socket/tcp.html
    """
    return dict( (getattr(socket, n), n)
                 for n in dir(socket)
                 if n.startswith(prefix)
                 )


def read_last_csv_line(infile):
    """ read last line from csv YYYY-MM-wxdata.csv
    """
    try:
        with open(infile, 'r') as f:
            last_line = f.readlines()[-1].split(",")

        f.close()
    except Exception as e:
        print('Done with exception(s): %s.' % e)
        errStat = 1
        sys.exit(errStat)

    return last_line


def read_txtfile(infile):
    """ read any text file
    """
    try:
        with open(infile, 'r') as f:
            txt = f.readlines()

        f.close()
    except Exception as e:
        print('Done with exception(s): %s.' % e)
        errStat = 1
        sys.exit(errStat)

    return txt


def get_wospi_version(infile):
    """ gets the WOSPi version from the wospi module
        or the minmax file, depending whether the module
        is in the same directory as this script or not
    """

    wospivers = ''

    try:
        from wospi import PROGRAMVERSION
        re_version = re.compile('(\w+)-(\w+)')
        m = re.match(re_version, PROGRAMVERSION)
        if m:
            wospivers = m.group(1)

    except ImportError:
        # loading of wospi not possible, read minmax file instead
        minmax_data = read_txtfile(infile)


        # match following string in the minmax file
        #   Software Version .... : 20151108-RPi
        re_version = re.compile('.*(Software\s+Version)\s+\.\..*:\s+(\w+)')
        for line in minmax_data:
            m = re.match(re_version, line)
            if m:
                wospivers = m.group(2)

        # fall back, if version could not be read
        if (wospivers == '' ):
            wospivers = CWOP_SW_VERS

    return wospivers


def fill_template(cwop_user):
    tzname = ''
    tzfile = '/etc/timezone'

    # get date to read the current csv
    YYMM = '%s' % time.strftime('%Y-%m')

    # csv to read the solar radiation
    WX   = config.CSVPATH + YYMM + "-" + config.CSVFILESUFFIX

    # solar radiation
    # http://www.aprs.org/aprs12/weather-new.txt
    last_rec_solar_rad = read_last_csv_line(WX)[8].strip()
    if ( int(last_rec_solar_rad) > 999 ):
        solar_rad = 'l' + last_rec_solar_rad[1:]
    else:
        solar_rad = 'L' + last_rec_solar_rad.zfill(3)

    # convert the position information from the config
    LONLAT = get_GPS2DMm(config.MYPOSITION)

    # read uiview file with APRS data
    uiview = read_txtfile(config.UIFILE)

    # get the data string and add solar radiation
    UIDATA = uiview[1].strip() + solar_rad

    # we need the time in DHM format (APRS101.pdf, p32)
    ui_time  = uiview[0].strip()

    # time in zulu format (APRS101.pdf, p32)
    if 'TZ' in os.environ:
        tzname = os.environ['TZ']
    if ( tzname == '' ):
        if os.path.exists(tzfile):
            tzname = read_txtfile(tzfile)[0].strip()
        else:
            # fall back, should not happen
            tzname = 'Europe/Vienna'

    local    = pytz.timezone (tzname)
    naive    = datetime.datetime.strptime (ui_time, "%b %d %Y %H:%M")
    local_dt = local.localize(naive, is_dst=None)
    utc_dt   = local_dt.astimezone (pytz.utc)

    # convert the time into utc and add 'z' for the result encoding
    utc = utc_dt.strftime("%d%H%M") + 'z'

    DEVICE = '-DvVP2'

    # fetch current wospi version
    CWOP_VERS = CWOP_SW_NAME + '-' + get_wospi_version(config.MINMAXFILE) + DEVICE

    # just some debug prints if you need it
    if DEBUG:
        print("LONLAT    : %s" % LONLAT)
        print("uidate    : %s" % uiview[0].strip())
        print("zulu time : %s" % utc)
        print("uidata    : %s" % UIDATA)

    # APRS101.pdf, p32ff
    #
    # create TNC string
    tnc = cwop_user + CWOP_FIX + '@' + utc + LONLAT + '_' + UIDATA + 'e' + CWOP_VERS

    return tnc


def print_dbg(level,msg):
    if level:
        print(msg)
    return


#-------------------------------------------------------------------------------
def main():
    # regex rule, login with wrong credentials
    re_resp_repeat  = re.compile('.*logresp.*unverified.*')

    # init socket variables
    families  = get_constants('AF_')
    types     = get_constants('SOCK_')
    protocols = get_constants('IPPROTO_')
    buflen    = 1024


    try:
        CWOP_USER = config.CWOP_ID
    except:
        # parameter not found in config.py
        # check commandline for user id
        if (len(sys.argv) < 2):
            print("\nusage: %s <cwop ID>\n" % sys.argv[0])
            sys.exit(1)
        else:
            CWOP_USER = sys.argv[1]


    # get data and fill template
    CWOP_DATA = fill_template(CWOP_USER)

    # build login string
    CWOP_SW_VERS = get_wospi_version(config.MINMAXFILE)
    LOGIN="user %s pass %s vers %s %s" % (CWOP_USER,CWOP_PASS,CWOP_SW_NAME,CWOP_SW_VERS)

    print("------------------------------------------------------------------------------------------------------------------")
    print("Login: %s" % LOGIN)
    print("DATA : %s" % CWOP_DATA)
    print("------------------------------------------------------------------------------------------------------------------")

    if TESTING:
        print_dbg(TRACE,'TESTING activated. Set TESTING=False, if you want to upload data. Exiting... ')
        sys.exit()

    # Create a TCP/IP socket
    print_dbg(TRACE,'1a-connecting : "%s"' % (CWOP_SRV))
    sock = socket.create_connection((CWOP_SRV, CWOP_PRT))

    try:
        data         = sock.recv(buflen)
        resp_connect = data.strip()

        re_resp_connect = re.compile('.*' + resp_connect + '.*')

        if re.match(re_resp_connect, resp_connect):
            pass
        else:
            print("CWOP response failed")

        print_dbg(TRACE,"1b-received   : %s" % (resp_connect))

        # Send login data
        print_dbg(TRACE,'\n2a-sending    : "%s"' % LOGIN)
        sock.sendall(LOGIN + '\r\n')
        data       = sock.recv(buflen)
        resp_login = data.strip()

        print_dbg(TRACE,"2b-received   : %s" % (resp_login))

        # for some reason, the first login fails, so I resend the login
        if re.match(re_resp_connect, resp_login):
            pass
        else:
            time.sleep(1)
            print_dbg(TRACE,'2a-resending  : "%s"' % LOGIN)
            sock.sendall(LOGIN + '\r\n')
            data       = sock.recv(buflen)
            resp_login = data.strip()

            print_dbg(TRACE,"2c-received   : %s" % (resp_login))

        if re.match(re_resp_repeat, resp_login):
            pass
        else:
            # if the response after the login is different to the response
            # to the connect, compile new regex
            # only use leading part of response without time
            re_resp_connect = re.compile('.*' + resp_login[:20] + '.*')

        # now, we really send the data
        print_dbg(TRACE,'\n3a-sending    : "%s"' % CWOP_DATA)
        sock.sendall(CWOP_DATA + '\r\n')

        data     = sock.recv(buflen)
        resp_msg = data.strip()
        print_dbg(TRACE,"3b-received   : %s" % (resp_msg))

        if re.match(re_resp_connect, resp_msg):
            pass
        else:
            time.sleep(1)
            print_dbg(TRACE,'3a-resending  : "%s"' % CWOP_DATA)
            sock.sendall(CWOP_DATA + '\r\n')
            data     = sock.recv(buflen)
            resp_msg = data.strip()

            print_dbg(TRACE,"3c-received   : %s" % (resp_msg))

    finally:
        print_dbg(TRACE,'4a-closing socket')
        sock.close()
        print("CWOP upload done.\n")


#-------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

