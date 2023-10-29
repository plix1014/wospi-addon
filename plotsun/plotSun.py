#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        Sun.py
# Purpose:     plot sunrise, sunset and sunshine
#
# Configuration options in config.py
#
# depends on:  WOSPi
#   ephem
#   plotsun_*.input
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     05.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

import wospi
import os, sys
import subprocess
import shutil
import re
import time
from datetime import date, timedelta, datetime
import ephem

# display more infos
DEBUG=False
# display gnuplot output, if any
TRACE=False
# remove png after upload
KEEP_PNG=False
# remove *.tmp file after gnuplot
KEEP_TMP=False
# upload png to your homepage
DO_SCP=True

#
NB_DAYS = 370

# merged version of all used csv files
tmpwrdata  = wospi.TMPPATH + 'plotwxdata.tmp'

# save equinox and solstice dates in tmp. file for gnuplot.
EQUINOX_OUT = wospi.TMPPATH + 'equinox.tmp'

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


def jump_by_month(start_date, end_date, month_step=1):
    """ iterate through date by month increments
        https://stackoverflow.com/questions/153584/how-to-iterate-over-a-timespan-after-days-hours-weeks-and-months-in-python
    """
    current_date = start_date
    while current_date < end_date:
        yield current_date
        carry, new_month = divmod(current_date.month - 1 + month_step, 12)
        new_month += 1
        current_date = current_date.replace(year=current_date.year + carry, month=new_month)


def toMinute(tstring):
    parts = tstring.split(":")
    minutes = int(parts[0])*60 + int(parts[1])
    return str(minutes)

def toHour(tstring):
    parts = tstring.split(":")
    hour = "%.2f" % ((int(parts[0])*60 + int(parts[1]))/60.0)
    return hour


def saveEquinoxDates(startDate):
    """ calculates the startdate of the equinoxs and solistices
    """
    spring = datetime.strptime(str(ephem.previous_spring_equinox(startDate)),'%Y/%m/%d %H:%M:%S').strftime('%d.%m.%Y')
    summer = datetime.strptime(str(ephem.previous_summer_solstice(startDate)),'%Y/%m/%d %H:%M:%S').strftime('%d.%m.%Y')
    autumn = datetime.strptime(str(ephem.previous_autumnal_equinox(startDate)),'%Y/%m/%d %H:%M:%S').strftime('%d.%m.%Y')
    winter = datetime.strptime(str(ephem.previous_winter_solstice(startDate)),'%Y/%m/%d %H:%M:%S').strftime('%d.%m.%Y')

    print_dbg(DEBUG, "current date    : %s" % startDate.strftime('%d.%m.%Y'))
    print_dbg(DEBUG, "spring_equinox  : %s" % spring)
    print_dbg(DEBUG, "summer_solstice : %s" % summer)
    print_dbg(DEBUG, "autumnal_equinox: %s" % autumn)
    print_dbg(DEBUG, "winter_solstice : %s" % winter)

    try:
        st = open(EQUINOX_OUT, 'w')
        s  = spring + ' ' + summer + ' ' + autumn + ' ' + winter + '\n'
        st.write(s)
        st.close()

    except Exception as e:
        print_dbg(True,"saveEquinoxDates: Done with exception(s): %s." % e)

    return


def prepareCSVData(fromMonth,fromYear):
    """ merging csv files from YYYMM to current month into one file
    """

    # get date to read the current csv
    YYMM = '%s' % time.strftime('%Y-%m')
    WX   = wospi.CSVPATH + YYMM + "-" + wospi.CSVFILESUFFIX

    # get name for previous csv
    fromYYMM = str(fromYear) + '-' + str(fromMonth).zfill(2)

    # remove existing temp file
    if (os.path.isfile(tmpwrdata)):
        os.unlink(tmpwrdata)

    start = date( year = fromYear, month = fromMonth, day = 1 )
    end   = date.today()

    print_dbg(DEBUG, "DEBUG: start: %s" % (start))
    print_dbg(DEBUG, "DEBUG: end  : %s" % (end))

    if (YYMM <> fromYYMM):
        print_dbg(DEBUG, "DEBUG: YYMM (%s) <> fromYYMM (%s)" % (YYMM,fromYYMM))
        print_dbg(True, "INFO : merging wxdata.csv into one file")
        # open target file
        wx  = open(tmpwrdata, 'wb')

        for dv in jump_by_month( start, end ):
            curYYMM = str(dv)[:7]
            WXcur = wospi.CSVPATH + curYYMM + "-" + wospi.CSVFILESUFFIX
            if (os.path.isfile(WXcur)):
                print_dbg(DEBUG, "DEBUG: merging %s" % curYYMM)
                wxc = open(WXcur,'rb')
                shutil.copyfileobj(wxc, wx)
                wxc.close()
            else:
                print_dbg(DEBUG,"DEBUG: missing %s" % curYYMM)

        wx.close()

    else:
        print_dbg(DEBUG, "DEBUG: YYMM (%s) == fromYYMM (%s)" % (YYMM,fromYYMM))
        print_dbg(True, "INFO : creating tmpcsv from %s" % YYMM)
        shutil.copyfile(WX,tmpwrdata)

    return


def prepareSunData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, outfile):
    """ prepare csv data; used by the gnuplot script
    """
    SunTimes = {}
    SunLight = {}
    SunShine = {}

    # set startdate
    start_date = date( year = fromYear, month = fromMonth, day = fromDay )

    # end date is today
    end_date = date.today()

    print_dbg(True,"INFO : processing from %s to %s" % (start_date,end_date))

    # create single csv for further processing
    prepareCSVData(fromMonth,fromYear)

    # open file for gnuplot
    OUTTEMP = wospi.TMPPATH + 'plot' + outfile + '.tmp'
    st = open(OUTTEMP, 'w')


    if (os.path.isfile(wospi.SUNTIMEFILE)):
        print_dbg(DEBUG,"prepareSunData: prepare sunrise, sunset data and calculate sun duration")
        sf = open(wospi.SUNTIMEFILE,'r')
        # skip header line
        wxlines = sf.readlines()[1:]
        sf.close()

        for line in wxlines:
            parts = line.strip().split(' ')

            sunrise = toHour(parts[1])
            sunset  = toHour(parts[2])

            newrec  = parts[0] + ', '
            newrec += sunrise + ', '
            newrec += sunset  + ', '
            newrec += str(float(sunset)-float(sunrise)) # + '\n'

            if parts[0] not in SunTimes.keys():
                SunTimes[parts[0]] = newrec
            else:
                print_dbg(DEBUG,"DEBUG: found 2nd value %s: %s" % (parts[0],newrec.strip()))
                #SunTimes[parts[0]] = newrec


    if (os.path.isfile(tmpwrdata)):
        print_dbg(DEBUG,"prepareSunData: calculate sunshine duration")
        sf = open(tmpwrdata,'r')
        wxlines = sf.readlines()
        sf.close()

        for line in wxlines:
            parts = line.strip().split(',')

            # we only need date and solar radiation
            keyDate = parts[0].split()[0]
            tVal = parts[8]

            # count number of events with solar radiation > 0
            if keyDate not in SunLight.keys():
                SunLight[keyDate] = int(wospi.CSVINTERVAL)

            else:
                if int(tVal) > 0:
                    SunLight[keyDate] += int(wospi.CSVINTERVAL)


            # count number of events with solar radiation > 120
            # Die tatsächliche Sonnenscheindauer ist als die Zeitspanne definiert,
            # während der die direkte Sonnenstrahlung senkrecht zur Sonnenrichtung mindestens 120 W/m2 beträgt
            # https://de.wikipedia.org/wiki/Sonnenschein
            # https://en.wikipedia.org/wiki/Sunlight
            if keyDate not in SunShine.keys():
                SunShine[keyDate] = int(wospi.CSVINTERVAL)

            else:
                if int(tVal) > 120:
                    SunShine[keyDate] += int(wospi.CSVINTERVAL)



        # write data sorted to file
        # convert minutes to hours and write sunshine values to tmp file
        # we have a reading every 'wospi.CSVINTERVAL' minutes. As we add wospi.CSVINTERVAL for each solar radiation > 0, we need
        # devide by 60 to get the hour-value
        for dv in daterange(start_date, end_date ):
            csvDate = str(dv)[8:10].zfill(2) + '.' + str(dv)[5:7].zfill(2) + '.' + str(dv)[:4]

            try:
                rec  = SunTimes[csvDate] + ', '
                rec += "%.2f" % (SunLight[csvDate]/60.0) + ', '
                rec += "%.2f" % (SunShine[csvDate]/60.0)
                rec += '\n'
                st.write(rec)

            except:
                # key error, add dummy value
                if SunTimes.has_key(csvDate):
                    rec  = SunTimes[csvDate] + ', '
                    rec += "0.00" + ', '
                    rec += "0.00"
                    rec += '\n'
                    st.write(rec)
                    print_dbg(True,"WARN :   ign val %s: %s" % (csvDate, rec.strip()))
                else:
                    pass


        # close the tmp file
        st.close()

        saveEquinoxDates(end_date)
        removeTMP(tmpwrdata)

    else:
        print_db(True, "WARN : file %s is missing" % config.SUNTIMEFILE)

    return



def print_dbg(level,msg):
    now = time.strftime('%a %b %d %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now,msg))
    return


def runGnuPlot(plt):
    """ run gnuplot
        TODO: parse output
    """
    re_stderr = re.compile(r'^.*,\s+(line\s+\d+):\s+(.*)')
    el = 0

    inFile = wospi.TMPPATH + 'plot' + plt + '.plt'

    gnuplot = '/usr/bin/gnuplot'

    if os.path.exists(gnuplot):
        print_dbg(DEBUG,"runGnuPlot: plot png " + plt)
        try:
            proc_out = subprocess.Popen([gnuplot, inFile], stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            output = proc_out.stdout.readlines()
            outerr = proc_out.stderr.readlines()

            for line in outerr:
                m = re.search(re_stderr, line.strip())
                if m:
                    print_dbg(True, "STDERR: %s" % line.strip())
                    if re.search("warning:",line):
                        # we ignore warning errors
                        pass
                    else:
                        raise ValueError('syntax or plot error in gnuplot file')
                    el = 1

            if TRACE:
                for n in output:
                    print_dbg(True, "STDOUT: %s" % n.strip())
                for n in outerr:
                    print_dbg(True, "STDERR: %s" % n.strip())

        except Exception as e:
            print_dbg(True, 'WARN : GnuPlot done with exception(s): %s.' % e)
            el = 1

    else:
        print_dbg(True,"ERROR: gnuplot command '%s' not found." % gnuplot)
        el = 1

    # cleanup temp files
    if not KEEP_TMP:
        if (os.path.isfile(inFile)):
            os.unlink(inFile)

    return el


def plotSun(plt,title, ext='input'):
    """ create plot file from template and start gnuplot
    """
    inFile  = wospi.HOMEPATH + 'plot' + plt + '.' + ext
    outFile = wospi.TMPPATH  + 'plot' + plt + '.plt'

    print_dbg(True,"INFO : plotSun: call prepareGPC for " + plt + " and run gnuplot")
    wospi.prepareGPC(wospi.fromTime(), wospi.toTime(), title, inFile, outFile, wospi.COMMISSIONDATE)
    runGnuPlot(plt)

    return


def uploadPNG(png):
    """ copies the png file to the website
    """

    SCPCOMMAND_PLOTSUNTIME = 'scp -o ConnectTimeout=12 %s %s' % (png, wospi.SCPTARGET)

    if DO_SCP:
        try:
            print_dbg(True, 'INFO : upload png %s.' % (png))
            os.system(SCPCOMMAND_PLOTSUNTIME)
        except Exception as e:
            print_dbg(True, 'ERROR: upload png %s: %s.' % (png,e))

    if not KEEP_PNG:
        if (os.path.isfile(png)):
            os.unlink(png)

    return


def removeTMP(inFile):
    # cleanup temp files
    if not KEEP_TMP:
        if (os.path.isfile(inFile)):
            os.unlink(inFile)



# -------------------------------------------------------------------------------------------

def main():
    errStat = 0

    d2        = datetime.now()
    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year

    try:
        # plot data
        key = 'sun_full'
        fromDate  = d2 + timedelta(days = -NB_DAYS)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year

        prepareSunData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, key)

        plotSun(key,wospi.PLOTSUNTIMEALLTITLE)
        plotSun('sun_shine',wospi.PLOTSUNSHINETITLE)

        uploadPNG(wospi.TMPPATH  + 'plot' + key + '.png')
        uploadPNG(wospi.TMPPATH  + 'plot' + 'sun_shine.png')

        removeTMP(wospi.TMPPATH + 'plot' + key + '.tmp')



    except Exception as e:
        print_dbg(True, 'ERROR: Done with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')


if __name__ == '__main__':
    main()


