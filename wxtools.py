#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        wxtools.py
# Purpose:     tools for plotting
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
# Created:     05.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

import config
import os, sys
import subprocess
import shutil
import re
import time
from datetime import date, timedelta, datetime


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


def runGnuPlot(plt, KEEP_TMP=False, LEVEL1=False, LEVEL2=False):
    """ run gnuplot
        TODO: parse output
    """
    # full error message
    re_stderr = re.compile(r'^.*,\s+(line\s+\d+):\s+(.*)')
    el = 0

    inFile = config.TMPPATH + 'plot' + plt + '.plt'

    gnuplot = '/usr/bin/gnuplot'

    if os.path.exists(gnuplot):
        print_dbg(LEVEL1,"runGnuPlot: plot png " + plt)
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

            if LEVEL2:
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

        tmpFile = config.TMPPATH + 'plot' + plt + '.tmp'
        if (os.path.isfile(tmpFile)):
            os.unlink(tmpFile)
        else:
            print_dbg(LEVEL1,"tmp file not found: %s" % tmpFile)

    return el


def uploadAny(inFile, DO_SCP=True, KEEP_IN=False, trans_mode='scp'):
    """ copies the any file to the website
    """

    SCPCOMMAND_PLOTINT = '%s -o ConnectTimeout=12 %s %s' % (trans_mode, inFile, config.SCPTARGET)

    if DO_SCP:
        try:
            print_dbg(True, 'INFO : uploading %s.' % (inFile))
            os.system(SCPCOMMAND_PLOTINT)

        except Exception as e:
            print_dbg(True, 'ERROR: upload %s: %s.' % (inFile,e))

    if not KEEP_IN:
        if (os.path.isfile(inFile)):
            os.unlink(inFile)
        else:
            print_dbg(True, 'ERROR: cannot delete %s.' % (inFile))

    return


def uploadPNG(png, DO_SCP=True, KEEP_PNG=False,trans_mode='scp'):
    """ copies the png file to the website
    """

    SCPCOMMAND_PLOTINT = '%s -o ConnectTimeout=12 %s %s' % (trans_mode, png, config.SCPTARGET)

    if DO_SCP:
        try:
            print_dbg(True, 'INFO : uploading %s.' % (png))
            os.system(SCPCOMMAND_PLOTINT)

        except Exception as e:
            print_dbg(True, 'ERROR: upload png %s: %s.' % (png,e))

    if not KEEP_PNG:
        if (os.path.isfile(png)):
            os.unlink(png)
        else:
            print_dbg(True, 'ERROR: cannot delete %s.' % (png))

    return


def saveTemp2CSV(outFile,toTime,SOCTEMP):

    try:
        fout = open(outFile, 'a')

        new_rec = "%s,%s\n" % (toTime,SOCTEMP)

        fout.write(new_rec)
        fout.close()

    except Exception as e:
        print 'Exception occured in function saveTemp2CSV. Check your code: %s' % e

    return


def stripNL(text):
    """ remove the newline from the end of the string
    """
    try:
        return float(text.strip())
    except AttributeError:
        return float(text)

# -------------------------------------------------------------------------------------------

def main():
    return

if __name__ == '__main__':
    main()


