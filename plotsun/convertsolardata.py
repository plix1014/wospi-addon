#!/usr/bin/env python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        convertsolardata.py
# Purpose:     download values from and reformat
#
# if you request data in your browser. You can store file
# in 'URLFILE' (see below). conversion will be done with this file
# instead of direct url request
#
# https://www.nrel.gov/midc/solpos/spa.html
# https://www.nrel.gov/midc/srrl_bms/
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     26.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

import re, os
from datetime import date, timedelta, datetime
from config import CSVPATH
import urllib2

# URL to retrieve data
URL_BASE = 'https://www.nrel.gov/midc/apps/spa.pl?'


#-------------------------------------------------------------------------------
# this parameter below needs to be adjusted
#
# set your GPS location
latitude    = 48.3382
longitude   = 016.0550

# set your timezone difference
# -1 == %2B1: '-' needs to be url-encoded
# -2 == %2B2
timezone    = "%2B1"

# set your elevation
elev        = 250

# set avg yearly air pressure and OAT
# cat ../csv_data/2015-*csv \
#	| awk -F"," '{oat+=$2; rh+=$5} END {print "AVG OAT: "oat/NR"   AVG RH: "rh/NR}'
press       = 1035
temp        = 11

# set deltaT, deltaUT
dut1        = 0.0
deltat      = 67.9547

#
azmrot      = 180
slope       = 0
refract     = 0.3704

# output fields (no need to change)
fielda      = 4
fieldb      = 6
zip         = 0


SOLFILE = CSVPATH + 'suntimes.csv'
# use it, if present
URLFILE = CSVPATH + 'suntimes_url.csv'
# created by script. 
SOLOUT  = CSVPATH + 'suntimes_conv.csv'

#-------------------------------------------------------------------------------

def save2CSV(csv,rec):
    try:
        fout = open(csv, 'w')

        header = "Date       Sunrise  Sunset\n"
        fout.write(header)

        for line in rec:
            fout.write(line)

        fout.close()

    except Exception as e:
        print 'Exception occured in function save2CSV. Check your code: %s' % e

    return


def h2hms(h):
    h_int   = int(h)

    if h_int > 0:
        min     = (h % h_int) * 60
        min_int = int(min)
    else:
        min     = h * 60
        min_int = int(min)

    if min_int > 0:
        sec     = (min % min_int) * 60
        sec_int = int(sec)
    else:
        sec     = min * 60
        sec_int = int(sec)

    hms     = str(h_int).zfill(2) + ':'
    hms    += str(min_int).zfill(2) + ':'
    hms    += str(sec_int).zfill(2)

    return hms


def convert_data(sol):
    re_sol = re.compile(r'^.*,6:00:00,.*')
    csv_out = []

    print "converting data for use with plotSun.py"

    for line in sol:
        # we only want the times at 06:00 in the morning
        m = re.search(re_sol, line.strip())
        if m:
            parts = line.strip().split(',')

            year  = parts[0].split('/')
            srise = h2hms(float(parts[2]))
            sset  = h2hms(float(parts[3]))

            rec  = year[1].zfill(2) + '.'
            rec += year[0].zfill(2) + '.'
            rec += year[2] + ' '
            rec += srise + ' '
            rec += sset + '\n'

            csv_out.append(rec)


    return csv_out


def get_solar_times(infile):

    edate       = datetime.now()
    sdate       = edate + timedelta(days = -365)

    # start date = one year earlier
    syear       = sdate.year
    smonth      = sdate.month
    sday        = sdate.day

    # end date = today
    eyear       = edate.year
    emonth      = edate.month
    eday        = edate.day

    # biggest step possible; every 10 minutes
    # though we only need one per day
    step        = 60
    stepunit    = 1

    # build URL
    URL  = URL_BASE
    URL += "syear=%s&"      % syear
    URL += "smonth=%s&"     % smonth
    URL += "sday=%s&"       % sday
    URL += "eyear=%s&"      % eyear
    URL += "emonth=%s&"     % emonth
    URL += "eday=%s&"       % eday
    URL += "step=%s&"       % step
    URL += "stepunit=%s&"   % stepunit
    URL += "latitude=%s2&"  % latitude
    URL += "longitude=%s&"  % longitude
    URL += "timezone=%s&"   % timezone
    URL += "elev=%s&"       % elev
    URL += "press=%s&"      % press
    URL += "temp=%s&"       % temp
    URL += "dut1=%s&"       % dut1
    URL += "deltat=%s&"     % deltat
    URL += "azmrot=%s&"     % azmrot
    URL += "slope=%s&"      % slope
    URL += "refract=%s&"    % refract
    URL += "field=%s&"      % fielda
    URL += "field=%s&"      % fieldb
    URL += "zip=%s"         % zip

    headers_agent  = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'}
    request = urllib2.Request(URL,None,headers_agent)
    csv = []

    if (os.path.isfile(infile)):
        print "using %s for conversion" % infile
        f = open(infile, "r")
        csv = f.readlines()
        f.close()
    else:
        print "feching data from URL %s" % URL

        try:
            #
            csv = urllib2.urlopen(request, timeout=10).readlines()

        except urllib2.URLError,e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason

            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code


    return csv



def main():
    solar_data = get_solar_times(URLFILE)
    save2CSV(SOLOUT,convert_data(solar_data))
    print "Done, copy %s to %s and than run plotSun.py" % (SOLOUT, SOLFILE)


if __name__ == '__main__':
    main()

