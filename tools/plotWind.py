#!/usr/bin/env python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotWind.py
# Purpose:     windrose plot of wind data
#
# Configuration options in config.py
#
# windrose module from:
#   http://youarealegend.blogspot.co.at/2008/09/windrose.html
#
# depends on:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
#   modules:  windrose, numpy, matplotlib, pandas, PIL, sqlite3
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     10.12.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 24.10.2023: remove debug code
#  PLI, 15.11.2023: read HOMEPATH from environment
#

import sys,os, shutil

CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME)

# datetime and panda for data structure
from datetime import datetime, timedelta, date
import pandas as pd

# wospi config and prepare functions
import wospi
from config import TMPPATH, HOMEPATH, CSVPATH, CSVFILESUFFIX, SCPTARGET, SCP

# for resizing the image
import PIL
from PIL import Image

# disable X11
import matplotlib as mpl
mpl.use('Agg')

# modules for the windrose plot
from windrose.windrose import WindroseAxes
from matplotlib import pyplot as plt
import matplotlib.cm as cm
from numpy import arange
import numpy as np
import sqlite3 as db
import time


# number of days for plotting
NBDAYS = 2

# temp files for processing
tmpwrdata  = TMPPATH + 'plotwrdata.tmp'

# sqlite database
dbfile = HOMEPATH + '../db/wospi.db'

# use sqlite3 db or csv file for plotting
# True  ... csv files
# False ... sqlite3
USE_CSV = True

# wind speed and direction variables, used by windrose
wd=[]
ws=[]

# set debug level
DEBUG=True
# show table contents
TRACE=False

# cleanup tmp
KEEP_PNG=False
KEEP_TMP=False

# initiate scp transfer
DO_SCP=True

#-------------------------------------------------------------------------------
# handle csv files

def daterange( start_date, end_date ):
    """ iterate through date
    """
    if start_date <= end_date:
        for n in range( ( end_date - start_date ).days + 1 ):
            yield start_date + timedelta( n )
    else:
        for n in range( ( start_date - end_date ).days + 1 ):
            yield start_date - timedelta( n )


def jump_by_month(start_date, end_date, month_step=1):
    """ iterate through date by month increments
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

def prepareCSVData(fromMonth,fromYear):
    """ merging csv files from YYYMM to current month
    """

    # get date to read the current csv
    YYMM = '%s' % time.strftime('%Y-%m')
    WX   = CSVPATH + YYMM + "-" + CSVFILESUFFIX

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
        # open target file
        wx  = open(tmpwrdata, 'wb')

        for dv in jump_by_month( start, end ):
            curYYMM = str(dv)[:7]
            WXcur = CSVPATH + curYYMM + "-" + CSVFILESUFFIX
            if (os.path.isfile(WXcur)):
                print("merging %s" % curYYMM)
                wxc = open(WXcur,'rb')
                shutil.copyfileobj(wxc, wx)
                wxc.close()
            else:
                print("missing %s" % curYYMM)

        wx.close()

    else:
        print_dbg(DEBUG, "DEBUG: YYMM (%s) == fromYYMM (%s)" % (YYMM,fromYYMM))
        print_dbg(True, "INFO: creating tmpcsv from %s" % YYMM)
        shutil.copyfile(WX,tmpwrdata)

    return



def stripNL(text):
    """ remove the newline from the end of the string
    """
    try:
        return float(text.strip())
    except AttributeError:
        return float(text)


def read_wx_csv(wxin,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear,isgust=False):
    """ read wxdata into pandas dataformat
    """
    # sample data
    # 20.12.2015 19:04:35,4.0,98,3.9,1027.8,242,2.6,0.0,0,0.0,0.4,0.0,5.8,1.7,2.0,4.3,180

    # rows to read
    rows = [0, 5, 6, 15, 16]

    # read csv
    data = pd.read_csv(wxin, header=None, usecols=rows, converters = {16 : stripNL})

    # rename columns
    data.rename(columns={ 0: 'timestamp',
                          5: 'present_wind_direction',
                          6: 'present_wind_speed',
                         15: 'ten_min_wind_gust_speed',
                         16: 'ten_min_wind_gust_direction'}, inplace=True)

    # convert date string field to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], format = '%d.%m.%Y %H:%M:%S')

    print_dbg(TRACE, data.head(2))

    # set time range
    #start_date = "%s.%s.%s %s:00:00" % (str(fromDay).zfill(2),str(fromMonth).zfill(2),fromYear,str(fromHour).zfill(2))
    #end_date   = "%s.%s.%s %s:00:00" % (str(toDay).zfill(2),  str(toMonth).zfill(2),  toYear,  str(fromHour).zfill(2))

    start_date = "%s-%s-%s %s:00:00" % (fromYear,str(fromMonth).zfill(2),str(fromDay).zfill(2),str(fromHour).zfill(2))
    end_date   = "%s-%s-%s %s:00:00" % (toYear,  str(toMonth).zfill(2),  str(toDay).zfill(2),  str(fromHour).zfill(2))

    print_dbg(DEBUG, "DEBUG: start: %s" % (start_date))
    print_dbg(DEBUG, "DEBUG: end  : %s" % (end_date))

    # select only the data within the timerange
    mask = (data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)

    print_dbg(TRACE, mask)
    plotdata = data.loc[mask]

    print_dbg(TRACE, "=== start of csv records ===")
    print_dbg(TRACE, plotdata.head(2))
    print_dbg(TRACE, "=== end of csv records ===")
    print_dbg(TRACE, plotdata.tail(2))

    return plotdata


#-------------------------------------------------------------------------------
# handle sqlite3 files

def read_wx_db(dbfile,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear,isgust=False):
    """ sql read wxdata into pandas dataformat
    """
    # sample data
    # 20.12.2015 19:04:35,4.0,98,3.9,1027.8,242,2.6,0.0,0,0.0,0.4,0.0,5.8,1.7,2.0,4.3,180
    try:
        con = db.connect(dbfile)

        # set time range
        start_date = "%s.%s.%s %s:00:00" % (str(fromDay).zfill(2),str(fromMonth).zfill(2),fromYear,str(fromHour).zfill(2))
        end_date   = "%s.%s.%s %s:00:00" % (str(toDay).zfill(2),  str(toMonth).zfill(2),  toYear,  str(fromHour).zfill(2))

        print_dbg(DEBUG, "DEBUG: start: %s" % (start_date))
        print_dbg(DEBUG, "DEBUG: end  : %s" % (end_date))

        if isgust:
            sql  = "SELECT timestamp, ten_min_wind_gust_direction, ten_min_wind_gust_speed "
            sql += "from vantage_wxdata "
            sql += "where timestamp BETWEEN '%s' and '%s' "  % (start_date, end_date)
            sql += "order by timestamp asc"

        else:
            sql  = "SELECT timestamp, present_wind_direction, present_wind_speed "
            sql += "from vantage_wxdata "
            sql += "where timestamp BETWEEN '%s' and '%s' "  % (start_date, end_date)
            sql += "order by timestamp asc"
            #sql += " limit 6"

        #table = pd.read_sql_query(sql, con)
        table = pd.read_sql(sql, con, index_col=None)

        print_dbg(TRACE, "=== start of db records ===")
        print_dbg(TRACE, table.head(2))
        print_dbg(TRACE, "=== end of db records ===")
        print_dbg(TRACE, table.tail(2))

        return table

    except db.Error, e:
        print_dbg(True, "Error %s:" % e.args[0])
        sys.exit(1)

    finally:
        if con:
            con.close()

    return

#-------------------------------------------------------------------------------
# plot functions

def new_axes():
    """ A quick way to create new windrose axes...
    """
    fig = plt.figure(figsize=(8, 8), dpi=80, facecolor='w', edgecolor='w')
    rect = [0.1, 0.1, 0.8, 0.8]
    ax = WindroseAxes(fig, rect, facecolor='w')
    fig.add_axes(ax)
    return ax


def set_legend(ax):
    """ ... and adjust the legend box
    """
    l = ax.legend(borderaxespad=-5.0)
    plt.setp(l.get_texts(), fontsize=8)


def mk_windrose(prefix,plotBar=False):
    """ create the windrose plots
    """
    HOURS = NBDAYS * 24

    if (prefix == "current"):
        typ = 'Present wind'
    else:
        typ = 'Wind gust'

    # A stacked histogram with normed (displayed in percent) results :
    print_dbg(True, "plotting Wind distribution " + prefix + " stacked WR")
    ax = new_axes()
    ax.bar(wd, ws, normed=True, opening=0.8, edgecolor='white')
    set_legend(ax)
    img_name = TMPPATH + 'wr_' + prefix + '_1_stacked.png'

    plt.text(0.5, 1.1, typ + " distribution (%)\n\n", weight="bold", fontsize=12,
            transform=plt.gca().transAxes, ha='center')
    plt.text(0.5, 1.1, "Data from the last %s hours" % HOURS, weight="light", fontsize=10,
            transform=plt.gca().transAxes, ha='center')

    fig = plt.gcf()
    fig.set_size_inches(5.5, 5.5, forward=True)

    if plotBar:
        sm = plt.cm.ScalarMappable(cmap=cm.jet, norm=plt.Normalize(vmin=0, vmax=max(ws)))
        sm._A = []
        cb = fig.colorbar(sm)
        cb.ax.tick_params(labelsize=9)

    fig.savefig(img_name, dpi=80, bbox_inches="tight", pad_inches=0.1, frameon=True)
    plt.clf()
    uploadPNG(img_name)


    # Same as above, but with contours over each filled region...
    print_dbg(True,"plotting Wind distribution " + prefix + " filled colormap WR")
    ax = new_axes()
    ax.contourf(wd, ws, bins=arange(0,8,1), cmap=cm.bwr)
    ax.contour(wd, ws, bins=arange(0,8,1), colors='black')
    set_legend(ax)
    img_name = TMPPATH + 'wr_' + prefix + '_4_colormap_filled.png'

    plt.text(0.5, 1.1, typ + " distribution map\n\n", weight="bold", fontsize=12,
            transform=plt.gca().transAxes, ha='center')
    plt.text(0.5, 1.1, "Data from the last %s hours" % HOURS, weight="light", fontsize=10,
            transform=plt.gca().transAxes, ha='center')

    fig = plt.gcf()
    fig.set_size_inches(5.5, 5.5, forward=True)

    if plotBar:
        sm = plt.cm.ScalarMappable(cmap=cm.bwr, norm=plt.Normalize(vmin=0, vmax=max(ws)))
        sm._A = []
        cb = fig.colorbar(sm)
        cb.ax.tick_params(labelsize=9)

    fig.savefig(img_name, dpi=80, bbox_inches="tight", pad_inches=0.1, frameon=True)
    plt.clf()
    uploadPNG(img_name)

    return


def uploadPNG(png):
    """ copies the png file to the website
    """

    SCPCOMMAND_PLOTWIND = '%s -o ConnectTimeout=12 %s %s' % (SCP, png, SCPTARGET)

    if DO_SCP:
        try:
            print_dbg(True, 'INFO : upload png %s.' % (png))
            os.system(SCPCOMMAND_PLOTWIND)
        except Exception as e:
            print_dbg(True, 'ERROR: upload png %s: %s.' % (png,e))

    if not KEEP_PNG:
        if (os.path.isfile(png)):
            os.unlink(png)

    return

#-------------------------------------------------------------------------------

def main():
    errStat = 0
    global wd
    global ws

    d2 = datetime.now()
    d1 = d2 + timedelta(days = -1 * NBDAYS)

    toDay     = d2.day
    toMonth   = d2.month
    toYear    = d2.year
    toHour    = d2.hour

    fromDay   = d1.day
    fromMonth = d1.month
    fromYear  = d1.year
    fromHour  = d1.hour

    try:
        if USE_CSV:
            prepareCSVData(fromMonth,fromYear)
            wr = read_wx_csv(tmpwrdata,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear)
        else:
            wr = read_wx_db(dbfile,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear)

        # fill wind arrays
        wd = wr["present_wind_direction"].tolist()
        ws = wr["present_wind_speed"].tolist()
        print_dbg(DEBUG, "DEBUG: Nb of Data points: %s/%s" % (len(wd),len(ws)))
        mk_windrose("current")

        if USE_CSV:
            wr = read_wx_csv(tmpwrdata,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear,True)
        else:
            wr = read_wx_db(dbfile,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear,True)

        # fill gust arrays
        wd = wr["ten_min_wind_gust_direction"].tolist()
        ws = wr["ten_min_wind_gust_speed"].tolist()

        print_dbg(DEBUG, "DEBUG: Nb of Data points: %s/%s" % (len(wd),len(ws)))
        mk_windrose("gust")

        # remove existing temp file
        if (os.path.isfile(tmpwrdata)):
            os.unlink(tmpwrdata)

    except Exception as e:
        print_dbg(True, 'ERROR: run with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO: Done.')


if __name__ == '__main__':
    main()

