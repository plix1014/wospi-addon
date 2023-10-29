#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotPrevRainDays.py
# Purpose:     create plot of rain days of previous year, SCP to web server
#
# Configuration options in config.py
#
# depends on:  WOSPi
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     16.01.2017
# Copyright:   (c) Peter Lidauer 2018
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
# Update:
#    v1.1: add gnuplot and transfer code
#    v1.2: send year to gnuplot input file
#-------------------------------------------------------------------------------

import wospi
import os, sys, shutil
from datetime import datetime, timedelta, date

# from local module
from wxtools import jump_by_month, print_dbg, uploadPNG

# some filenames for creating the plot
tmpfile = wospi.TMPPATH  + 'prevraindata.tmp'
inpfile = wospi.HOMEPATH + 'plotPrevRainDaysPerMonthY.input'
gpcfile = wospi.TMPPATH  + 'plotPrevRainDaysPerMonthY.gpc'
pngname = 'monthlyraindays'
pngfile = wospi.TMPPATH  + pngname + '_prev.png'

# labels for plot file
labelfile  = wospi.TMPPATH + 'year.tmp'

#-------------------------------------------------------------------------------


# set debug level
DEBUG    = True

# keep png files after upload
KEEP_PNG = True
# keep temporary files
KEEP_TMP = False
# upload png and inc
DO_SCP   = False

# -----------------------------------------------------------------------------------------------------------
def findPrevRainPerMonth(minYear, maxYear):
    """Support function to extract a series of rain data from 01.01.[PRESENT_YEAR-2] until NOW,"""
    #maxYear = datetime.now().year
    #maxMonth = datetime.now().month
    maxMonth = 12
    #minYear = maxYear - 2
    minMonth = 1
    monthRange = []
    monthlyRain = {}

    start = date( year = minYear, month = minMonth, day = 1 )
    end   = date.today() + timedelta(days = -30)

    for dv in jump_by_month( start, end ):
        curYYMM = str(dv)[:7]
        monthRange.append(curYYMM)


    for rainFilePrefix in monthRange:
        rainDays = 0
        monthRain = 0
        rainFileName = wospi.CSVPATH + rainFilePrefix + '.rain'
        try:
            print_dbg(DEBUG,"DEBUG: rainFilePrefix = %s" % rainFilePrefix)
            rainFile = open(rainFileName, 'r')
            rainLines = rainFile.readlines()
            rainFile.close()


            for rainLine in rainLines:
                dayRain = float(rainLine.split(',')[1])

                if dayRain > wospi.RAINTHRESHOLD_MM:
                    rainDays += 1

            rainLines = rainLines[len(rainLines) - 1]
            monthRain = rainLines.split(',')[2]
            if float(monthRain) > wospi.RAINTHRESHOLD_MM:
                monthlyRain[rainFilePrefix] = [float(monthRain), rainDays]
            else:
                monthlyRain[rainFilePrefix] = [0, rainDays]
        except Exception as e:
            #monthlyRain[rainFilePrefix] = [-1, -1]
            pass


    rainData = []
    for month in monthlyRain:
        rainData.append('%s, %0.2f, %d\n' % (month, monthlyRain[month][0], monthlyRain[month][1]))

    rainData.sort()
    f = open(tmpfile, 'w')
    f.writelines(rainData)
    f.close()


def preparePrevRainData(prevYear, thisYear):
    thisDay=1
    thisMonth=1

    if (os.path.isfile(tmpfile)):
        os.unlink(tmpfile)

    for n in range(prevYear,thisYear):
        s  = 'cat ' + wospi.CSVPATH + str(n) + '-*' + '.rain >> ' + tmpfile
        print_dbg(DEBUG,"DEBUG: %s" %s)
        os.system(s)


def save_labels(year):
    """ save labels to file to support
        languages without changing the gnuplot file
    """

    print_dbg(DEBUG,"DEBUG: year: %s" % year)

    try:
        st = open(labelfile, 'w')
        st.write(str(year)+'\n')
        st.close()

    except Exception as e:
        print_dbg(True,"ERROR: writing to file '%s': %s" % (labelfile,e))

    return

# -----------------------------------------------------------------------------------------------------------

def main():
    d2        = datetime.now()
    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year

    fromYear  = toYear - 1


    errStat = 0
    try:
        print_dbg(DEBUG,"DEBUG: start: %s" % fromYear)
        print_dbg(DEBUG,"DEBUG: end  : %s" % toYear)

        #preparePrevRainData(fromYear, toYear)

        findPrevRainPerMonth(fromYear, toYear)
        wospi.prepareGPC('', wospi.toTime(), wospi.PLOTRAINDAYSPERMONTHTITLE, inpfile, gpcfile, wospi.COMMISSIONDATE)

        # save year for gnuplot file
        save_labels(fromYear)

        if (sys.platform == "win32" ):
            gnuplot = 'c:\\MyApps\\gnuplot\\bin\\gnuplot.exe'
            os.system(gnuplot + ' ' + gpcfile)
        else:
            gnuplot = '/usr/bin/gnuplot'
            os.system(gnuplot + ' ' + gpcfile + ' 2> /dev/null')



        png_year = wospi.TMPPATH  + pngname + '_' + str(fromYear) + '.png'
        print_dbg(True, "INFO : Result file: %s" % png_year)

        uploadPNG(png_year, DO_SCP, KEEP_PNG)

        if not KEEP_TMP:
            if (os.path.isfile(tmpfile)):
                print_dbg(DEBUG,"DEBUG: unlink %s" % tmpfile)
                os.unlink(tmpfile)

            if (os.path.isfile(gpcfile)):
                print_dbg(DEBUG,"DEBUG: unlink %s" % gpcfile)
                os.unlink(gpcfile)

            if (os.path.isfile(labelfile)):
                print_dbg(DEBUG,"DEBUG: unlink %s" % labelfile)
                os.unlink(labelfile)


    except Exception as e:
        print 'Done with exception(s): %s.' % e
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')


if __name__ == '__main__':
    main()
