#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotInternalTemp.py
# Purpose:     plot Internal temperatur of the raspberry Pi
#
# Configuration options in config.py
#
# depends on:
#   plotinternal_*.input
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
# Changes:
#  PLI, 18.07.2025: changes for python3

import wospi
import os, sys
import subprocess
import shutil
import re
import time
from datetime import date, timedelta, datetime
import numpy

DEBUG=False
TRACE=True
KEEP_PNG=False
KEEP_TMP=False
DO_SCP=True

DEF_INTFILE = wospi.INTFILE

# plot chart daterange
NB_DAYS = 40

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


def print_dbg(level,msg):
    now = time.strftime('%a %b %d %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now,msg))
    return

def prepareInternalTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, outfile, rType):
    """ prepare csv data for gnuplot depending on plot type
    """
    InternalTemp = {}

    # datetime             SoC    IAT   IRH   DHT_T    DHT_RH   T11  RH11
    # 01.02.2016 06:03:02, 42.2, 21.6,   48,   21.0,   58.9,   20.0, 37.0

    # set startdate
    start_date = date( year = fromYear, month = fromMonth, day = fromDay )

    if rType == 'full':
        # we use the entire data for the plot
        print_dbg(DEBUG,"prepareInternalTemperature: prepare %s csv" % rType)
    elif rType == '24h':
        print_dbg(DEBUG,"prepareInternalTemperature: prepare %s csv" % rType)
    elif rType == 'week':
        print_dbg(DEBUG,"prepareInternalTemperature: prepare %s csv" % rType)
    else:
        print_dbg(DEBUG,"prepareInternalTemperature: unknown time range type: %s" % rType)


    # end date is today
    end_date = date.today()

    print_dbg(DEBUG,"out=start date : %s  == end date : %s" % (start_date,end_date))

    INTTEMP = wospi.TMPPATH + 'plot' + outfile + '.tmp'
    print_dbg(DEBUG,"prepareInternalTemperature: write %s timerange into temp" % rType)
    if (os.path.isfile(CURRENT_INTFILE)):
        sf = open(CURRENT_INTFILE,'r')
        wxlines = sf.readlines()
        sf.close()

        st = open(INTTEMP, 'w')
        st.write('# date-time,         SoC,  Tv,   RHv, T22, RH22, T11,  RH11, Ts22, RHs22, Ts11, RHs11\n')

        if rType == 'full':
            re_hdr = re.compile(r'^#')
            for line in wxlines:
                if not re.search(re_hdr, line.strip()):
                    print_dbg(DEBUG,"DEBUG: %s" % line.strip())
                    line_stat = standard_deviation(line)

                    st.write(line_stat)

        else:
            for dv in daterange(start_date, end_date ):
                print_dbg(TRACE,"working on %s" % dv)
                csvDate = str(dv)[8:10].zfill(2) + '.' + str(dv)[5:7].zfill(2) + '.' + str(dv)[:4]

                re_date = re.compile(r"^%s.*" % csvDate)
                for line in wxlines:
                    m = re.search(re_date, line.strip())
                    if m:
                        if rType == '24h' or rType == 'week':
                            line_stat = standard_deviation(line)

                            st.write(line_stat)
                            print_dbg(DEBUG,"DEBUG: %s" % line_stat.strip())



        for dv in daterange(start_date, end_date ):
            print_dbg(TRACE,"working on %s" % dv)
            csvDate = str(dv)[8:10].zfill(2) + '.' + str(dv)[5:7].zfill(2) + '.' + str(dv)[:4]

            try:
                if rType == 'minmax' or rType == 'full1':
                    rec  = csvDate + ', '
                    rec += InternalTemp[csvDate][0] + ', '
                    rec += InternalTemp[csvDate][1]
                    rec += '\n'
                    st.write(rec)

            except:
                # ignore data outside daterange
                pass



        # close the tmp file
        st.close()

    else:
        print_dbg(True, "WARN : file %s is missing" % CURRENT_INTFILE)


    return

#=================================================================================================================


def runGnuPlot(plt):
    """ run gnuplot
    """
    # full error message
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
                line = line.decode('latin1').strip()
                m = re.search(re_stderr, line)
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

        if not re.search("_24h",plt):
            tmpFile = wospi.TMPPATH + 'plot' + plt + '.tmp'
            if (os.path.isfile(tmpFile)):
                os.unlink(tmpFile)
            else:
                print_dbg(DEBUG,"tmp file not found: %s" % tmpFile)

    return el


def plotInternalTemp(plt,fromDate, title, ext='input'):
    """ create plot file from template and start gnuplot
    """
    inFile  = wospi.HOMEPATH + 'plot' + plt + '.' + ext
    outFile = wospi.TMPPATH  + 'plot' + plt + '.plt'
    fromTime = fromDate.strftime('%d.%m.%Y %H:%M:%S')

    toTime   = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    print_dbg(True,"plotInternalTemp: call prepareGPC with " + plt)
    wospi.prepareGPC(fromTime, toTime, title, inFile, outFile, wospi.COMMISSIONDATE)
    runGnuPlot(plt)
    return


def uploadPNG(png):
    """ copies the png file to the website
    """

    SCPCOMMAND_PLOTINT = '%s -o ConnectTimeout=12 %s %s' % (wospi.SCP, png, wospi.SCPTARGET)

    if DO_SCP:
        try:
            os.system(SCPCOMMAND_PLOTINT)

        except Exception as e:
            print_dbg(True, 'ERROR: upload png %s: %s.' % (png,e))

    if not KEEP_PNG:
        if (os.path.isfile(png)):
            os.unlink(png)

    return

def standard_deviation(line):
    """ calc standard deviation for temperatur and humidity
    """

    # 01.02.2016 06:03:02, 42.2, 21.6, 48, 21.0, 58.9, 20.0, 37.0
    parts = line.strip().split(',')

    #Tv22  = [ parts[2], parts[4]]
    #RHv22 = [ parts[3], parts[5]]
    #Tv11  = [ parts[2], parts[6]]
    #RHv11 = [ parts[3], parts[7]]

    #Tv22  = list(map(float, Tv22))
    #RHv22 = list(map(float, RHv22))
    #Tv11  = list(map(float, Tv11))
    #RHv11 = list(map(float, RHv11))

    Tv22  = [float(parts[2]), float(parts[4])]
    RHv22 = [float(parts[3]), float(parts[5])]
    Tv11  = [float(parts[2]), float(parts[6])]
    RHv11 = [float(parts[3]), float(parts[7])]

    #
    T22dev  = numpy.std(numpy.array([Tv22]), ddof=0)
    RH22dev = numpy.std(numpy.array([RHv22]), ddof=0)
    T11dev  = numpy.std(numpy.array([Tv11]), ddof=0)
    RH11dev = numpy.std(numpy.array([RHv11]), ddof=0)

    return line.strip() + ", " + str(T22dev) + ", " + str(T11dev) + ", " + str(RH22dev) + ", " + str(RH11dev) +"\n"

# -------------------------------------------------------------------------------------------

def main():
    errStat = 0
    global CURRENT_INTFILE

    d2        = datetime.now()
    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year

    CURRENT_INTFILE = str(os.path.dirname(DEF_INTFILE)) + '/' + str(toYear) + '-' + str(os.path.basename(DEF_INTFILE))

    print("INTFILE: " + DEF_INTFILE)
    print("CUR_INT: " + CURRENT_INTFILE)

    try:
        # part 1 : 24h plot
        ctyp = 'internal_24h'
        fromDate  = d2 + timedelta(days = -2)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        prepareInternalTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, ctyp, '24h')
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTTEMP24HTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')

        ctyp = 'internal_rh_24h'
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTRH24SHTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')

        ctyp = 'internal_tv_24h'
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTTEMP24SHTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')

        ctyp = 'internal_diff_24h'
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTTEMPDIF24HTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')


        # cleanup temp files
        if not KEEP_TMP:
            tmpFile = wospi.TMPPATH + 'plotinternal_24h.tmp'
            if (os.path.isfile(tmpFile)):
                os.unlink(tmpFile)
            else:
                print_dbg(DEBUG,"tmp file not found: %s" % tmpFile)


        # part 2 : weekly plot
        fromDate  = d2 + timedelta(days = -6)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        ctyp = 'internal_week'
        prepareInternalTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, ctyp, 'week')
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTTEMPTITLE)

        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')


        # part 4 : full plot, from* and to* parameters are ignored
        ctyp = 'internal_full'
        prepareInternalTemperature(fromDay, fromMonth, fromYear, toDay, toMonth, toYear, ctyp, 'full')
        plotInternalTemp(ctyp,fromDate, wospi.PLOTINTALLHTITLE)
        uploadPNG(wospi.TMPPATH  + 'plot' + ctyp + '.png')

    except Exception as e:
        print_dbg(True, 'ERROR: Done with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')


if __name__ == '__main__':
    main()


