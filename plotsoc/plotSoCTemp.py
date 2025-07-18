#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotSoCTemp.py
# Purpose:     plot SoC temperatur of the raspberry Pi
# Configuration options in config.py
#
# depends on:  WOSPi
#   plotsoctemp_*.input
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     08.02.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 18.07.2025: changes for python3

import wospi
import os, sys
import subprocess
import shutil
import re
import time
from datetime import date, timedelta, datetime

# from local module
from wxtools import print_dbg, runGnuPlot, uploadPNG

DEBUG=False
TRACE=False
KEEP_PNG=False
KEEP_TMP=False
DO_SCP=True


# merged source data
allsocdata   = wospi.TMPPATH + 'plotsocdata.tmp'

#-------------------------------------------------------------------------------
# handle csv files

def daterange( start_date, end_date ):
    """ iterate through date by days
        https://tudorbarbu.ninja/iterate-thru-dates-in-python/
    """
    if start_date <= end_date:
        for n in range( ( end_date - start_date ).days + 1 ):
            yield start_date + timedelta( n )
    else:
        for n in range( ( start_date - end_date ).days + 1 ):
            yield start_date - timedelta( n )


def prepareCSVDataYear(fromYear, tmpfile):
    """ merging csv files from YYY to current year
    """

    print_dbg(True, 'INFO : preparing temp CSV file')

    # remove existing temp file
    if (os.path.isfile(tmpfile)):
        os.unlink(tmpfile)

    fromMonth = int('%s' % time.strftime('%m'))
    start = date( year = fromYear, month = fromMonth, day = 1 )
    end   = date.today()

    print_dbg(DEBUG, "DEBUG: start: %s" % (start))
    print_dbg(DEBUG, "DEBUG: end  : %s" % (end))

    for dv in range(fromYear, end.year+1):
        curYY  = str(dv)
        SOCcur = str(os.path.dirname(wospi.SOCFILE)) + '/' + str(curYY) + '-' + str(os.path.basename(wospi.SOCFILE))
        if (os.path.isfile(SOCcur)):
            print_dbg(DEBUG, "DEBUG merging %s from %s" % (curYY, SOCcur))
            wx  = open(tmpfile, 'ab')
            wxc = open(SOCcur,'rb')
            shutil.copyfileobj(wxc, wx)
            wxc.close()
            wx.close()
        else:
            print_dbg(DEBUG, "DEBUG file missing %s" % SOCcur)

    return


def prepareSoCTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, outfile, rType):
    """ prepare csv data for gnuplot depending on plot type
    """
    MinMaxTemp = {}
    csv_out = []

    SOC = allsocdata

    # set startdate
    start_date = date( year = fromYear, month = fromMonth, day = fromDay )

    if rType == 'full':
        # we use the entire data for the plot
        print_dbg(DEBUG,"prepareSoCTemperature: prepare %s csv" % rType)
        #SOCTEMP = wospi.TMPPATH + 'plot' + outfile + '.tmp'
        #shutil.copyfile(SOC, SOCTEMP)
        #return
    elif rType == '24h':
        print_dbg(DEBUG,"prepareSoCTemperature: prepare %s csv" % rType)
    elif rType == 'week':
        print_dbg(DEBUG,"prepareSoCTemperature: prepare %s csv" % rType)
    elif rType == 'minmax':
        print_dbg(DEBUG,"prepareSoCTemperature: prepare %s csv" % rType)
        start_date = date( year = fromYear, month = fromMonth, day = 1 )
    else:
        print_dbg(DEBUG,"prepareSoCTemperature: unknown time range type: %s" % rType)


    # end date is today
    end_date = date.today()

    print_dbg(DEBUG,"out=start date : %s  == end date : %s" % (start_date,end_date))

    SOCTEMP = wospi.TMPPATH + 'plot' + outfile + '.tmp'
    print_dbg(DEBUG,"prepareSoCTemperature: write %s timerange into temp" % rType)
    if (os.path.isfile(SOC)):
        sf = open(SOC,'r')
        st = open(SOCTEMP, 'w')

        for dv in daterange(start_date, end_date ):
            print_dbg(DEBUG,"working on %s" % dv)
            csvDate = str(dv)[8:10].zfill(2) + '.' + str(dv)[5:7].zfill(2) + '.' + str(dv)[:4]

            print_dbg(DEBUG,"  csvDate: %s" % (csvDate))
            re_date = re.compile(r"^%s.*" % csvDate)
            for line in sf:
                m = re.search(re_date, line.strip())
                if m:
                    if rType == 'week':
                        parts = line.strip().split(',')
                        newrec  = parts[0][6:10] + '.'
                        newrec += parts[0][3:5] + '.'
                        newrec += parts[0][0:2] + ' '
                        newrec += parts[0][11:19] + ','
                        newrec += parts[1] + '\n'

                        st.write(newrec)

                    elif rType == 'minmax' or rType == 'full':
                        parts = line.strip().split(',')
                        newdate  = parts[0][6:10] + '.'
                        newdate += parts[0][3:5] + '.'
                        newdate += parts[0][0:2]

                        tVal = parts[1]

                        if newdate not in MinMaxTemp.keys():
                            print_dbg(TRACE,"  new val %s: %s" % (newdate,tVal))
                            MinMaxTemp[newdate] = [tVal, tVal]
                        else:
                            if tVal < MinMaxTemp[newdate][0]:
                                MinMaxTemp[newdate][0] = tVal
                            elif tVal > MinMaxTemp[newdate][1]:
                                MinMaxTemp[newdate][1] = tVal
                            else:
                                print_dbg(TRACE,"  newdate: %s" % (newdate))

                    elif rType == '24h':
                        st.write(line)

                    else:
                        #print_dbg(DEBUG,"no match: %s" % (line.strip()))
                        pass

            # reset filepointer
            sf.seek(0)

        if rType == 'minmax' or rType == 'full':
            # write min/max values to tmp file
            for line in sorted(MinMaxTemp.keys()):
                rec = line + ', ' + MinMaxTemp[line][0] + ', ' + MinMaxTemp[line][1] + '\n'
                st.write(rec)


        # close the csv and the tmp file
        sf.close()
        st.close()

    else:
        print_dbg(True, "WARN : file %s is missing" % SOC)


    return



def plotSoCTemp(plt,title):
    """ create plot file from template and start gnuplot
    """
    inFile  = wospi.HOMEPATH + 'plot' + plt + '.input'
    outFile = wospi.TMPPATH  + 'plot' + plt + '.plt'

    print_dbg(True,"plotSoCTemp: call prepareGPC with " + plt)
    wospi.prepareGPC(wospi.fromTime(), wospi.toTime(), title, inFile, outFile, wospi.COMMISSIONDATE)
    runGnuPlot(plt, KEEP_TMP, DEBUG, TRACE)
    return


# -------------------------------------------------------------------------------------------

def main():
    errStat = 0

    d2        = datetime.now()
    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year

    try:
        fromDate  = d2 + timedelta(days = -365)
        fromYear  = fromDate.year
        prepareCSVDataYear(fromYear, allsocdata)

        # part 1 : 24h plot
        soc = 'soctemp_24h'
        fromDate  = d2 + timedelta(days = -2)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        prepareSoCTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, soc, '24h')
        plotSoCTemp(soc,wospi.PLOTSOCTEMP24HTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + soc + '.png', DO_SCP, KEEP_PNG, wospi.SCP)


        # part 2 : weekly plot
        fromDate  = d2 + timedelta(days = -7)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        soc = 'soctemp_week'
        prepareSoCTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, soc, 'week')
        plotSoCTemp(soc,wospi.PLOTSOCTEMPTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + soc + '.png', DO_SCP, KEEP_PNG, wospi.SCP)


        # part 3 : minmax plot
        soc = 'soctemp_minmax'
        fromDate  = d2 + timedelta(days = -365)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        prepareSoCTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, soc, 'minmax')
        plotSoCTemp(soc,wospi.PLOTSOCTEMPMINMAXTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + soc + '.png', DO_SCP, KEEP_PNG, wospi.SCP)


        # part 4 : full plot, from* and to* parameters are ignored
        soc = 'soctemp_full'
        prepareSoCTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, soc, 'full')
        plotSoCTemp(soc,wospi.PLOTSOCTEMPALLTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + soc + '.png', DO_SCP, KEEP_PNG, wospi.SCP)


    except Exception as e:
        print('Done with exception(s): %s.' % e)
        errStat = 1

    if not KEEP_TMP:
        if (os.path.isfile(allsocdata)):
            os.unlink(allsocdata)

    if(errStat == 0):
        print('Done.')


if __name__ == '__main__':
    main()


