#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        Uptime.py
# Purpose:     plot uptime of the raspberry Pi
# Configuration options in config.py
#
# depends on:  WOSPi
#   plotuptime_*.input
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

DEBUG=False
TRACE=False
KEEP_PNG=False
KEEP_TMP=False
DO_SCP=True

# plot chart daterange
NB_DAYS = 180


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



def prepareUptimeData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, outfile, rType):
    """ prepare csv data for gnuplot depending on plot type
    """
    Uptimes    = {}

    # set startdate
    start_date = date( year = fromYear, month = fromMonth, day = fromDay )

    if rType == 'full':
        print_dbg(DEBUG,"DEBUG: prepareUptimeData: prepare %s csv" % rType)

    elif rType == 'minmax':
        print_dbg(DEBUG,"DEBUG: prepareUptimeData: prepare %s csv" % rType)
        start_date = date( year = fromYear, month = fromMonth, day = 1 )
    else:
        print_dbg(DEBUG,"DEBUG: prepareUptimeData: unknown time range type: %s" % rType)


    # end date is today
    end_date = date.today()

    print_dbg(DEBUG,"DEBUG: out=start date : %s  == end date : %s" % (start_date,end_date))

    UPTEMP = wospi.TMPPATH + 'plot' + outfile + '.tmp'
    print_dbg(DEBUG,"DEBUG: prepareUptimeData: write %s timerange into temp" % rType)
    if (os.path.isfile(wospi.UPTIMEFILE)):
        sf = open(wospi.UPTIMEFILE,'r')
        wxlines = sf.readlines()
        sf.close()

        st = open(UPTEMP, 'w')

        for line in wxlines:
            parts = line.strip().split(',')

            udate = parts[0].split()[0]
            hVal = parts[1]
            dVal = "%.2f" % (float(parts[1])/24.0)

            if rType == 'full':
                if udate not in Uptimes.keys():
                    Uptimes[udate] = [hVal, dVal]
                else:
                    Uptimes[udate][1] = dVal


            if rType == 'minmax':
                if udate not in Uptimes.keys():
                    Uptimes[udate] = [hVal, hVal]
                else:
                    if float(hVal) < float(Uptimes[udate][0]):
                        Uptimes[udate][0] = hVal
                    elif float(hVal) > float(Uptimes[udate][1]):
                        Uptimes[udate][1] = hVal



        for dv in daterange(start_date, end_date ):
            csvDate = str(dv)[8:10].zfill(2) + '.' + str(dv)[5:7].zfill(2) + '.' + str(dv)[:4]

            try:
                rec  = csvDate + ', '
                rec += Uptimes[csvDate][0] + ', '
                rec += Uptimes[csvDate][1]
                rec += '\n'
                st.write(rec)

                print_dbg(DEBUG,"DEBUG: %s" % rec.strip())
            except:
                # ignore data outside daterange
                pass

        # close the tmp file
        st.close()

    else:
        print_dbg(True, "ERROR: file %s is missing" % wospi.UPTIMEFILE)


    return


def print_dbg(level,msg):
    #now = time.strftime('%a %b %d %T %Y LT:')
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

    if (sys.platform == "win32" ):
        gnuplot = 'c:\\MyApps\\gnuplot\\bin\\gnuplot.exe'
    else:
        gnuplot = '/usr/bin/gnuplot'

    if os.path.exists(gnuplot):
        print_dbg(DEBUG,"DEBUG: runGnuPlot: plot png " + plt)
        try:
            proc_out = subprocess.Popen([gnuplot, inFile], stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            output = proc_out.stdout.readlines()
            outerr = proc_out.stderr.readlines()

            for line in outerr:
                m = re.search(re_stderr, line.strip())
                if m:
                    print_dbg(True, "STDER: %s" % line.strip())
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

        tmpFile = wospi.TMPPATH + 'plot' + plt + '.tmp'
        if (os.path.isfile(tmpFile)):
            os.unlink(tmpFile)
        else:
            print_dbg(DEBUG,"ERROR: tmp file not found: %s" % tmpFile)

    return el


def Uptime(plt,title):
    """ create plot file from template and start gnuplot
    """
    inFile  = wospi.HOMEPATH + 'plot' + plt + '.input'
    outFile = wospi.TMPPATH  + 'plot' + plt + '.plt'

    print_dbg(True,"INFO : Uptime: call prepareGPC with " + plt)
    wospi.prepareGPC(wospi.fromTime(), wospi.toTime(), title, inFile, outFile, wospi.COMMISSIONDATE)
    runGnuPlot(plt)
    return


def uploadPNG(png):
    """ copies the png file to the website
    """

    SCPCOMMAND_PLOTUPTIME = 'fscp -o ConnectTimeout=12 %s %s' % (png, wospi.FSCPTARGET)

    if DO_SCP:
        try:
            os.system(SCPCOMMAND_PLOTUPTIME)
        except Exception as e:
            print_dbg(True, 'ERROR: upload png %s: %s.' % (png,e))

    if not KEEP_PNG:
        if (os.path.isfile(png)):
            os.unlink(png)

    return

# -------------------------------------------------------------------------------------------

def main():
    errStat = 0

    d2        = datetime.now()
    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year

    fromDate  = d2 + timedelta(days = -NB_DAYS)
    fromDay   = fromDate.day
    fromMonth = fromDate.month
    fromYear  = fromDate.year

    try:
        # part 1 : plot uptime chart
        upt = 'uptime_full'
        prepareUptimeData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, upt, 'full')
        Uptime(upt,wospi.PLOTUPTIMEALLTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + upt + '.png')


        # part 2 : plot uptime with min/max values
        upt = 'uptime_minmax'

        prepareUptimeData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, upt, 'minmax')
        Uptime(upt,wospi.PLOTUPTIMEMINMAXTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + upt + '.png')


    except Exception as e:
        print_dbg(True, 'ERROR: Done with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')


if __name__ == '__main__':
    main()


