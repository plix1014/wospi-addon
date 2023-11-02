#!/usr/bin/python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotUV.py
# Purpose:     plot historical weather stats
#
# Note:
# - script only uses celsius degrees. If you want the limits shown as fahrenheit
#   you need to convert TICE,TFRE,TSUM,THEA,TDES,TTRO in the *.input file
# - definition of cold- ,hot-days, trop nights differ between countries
#   current thresholds are valid for austria/germany/swiss as shown on
#   https://de.wikipedia.org/wiki/Klimatologie or DWD (Deutscher Wetterdienst)
#   if you need to change this limits(DEG_C), you need to convert your °F to °C
#   e.g. Hot day:
#           AT: Tmax >= 30°C
#           US: Tmax >= 91°F = 32.8°C
#
# - set LabelText to desired language. This does not change the calculation
#
# short overview of the program logic
# I. prepare pandas array
#	1. merge csv' from requested year to on file
#	2. load data into pandas array (all columns, although currently only outside temp is used)
#	3. rename columns
#	4. tell pandas, that first column is a datetime
#	5. set first column as index
#
# II. calc temperature statistics
#	1. get outside_air_temp column
#	2. get a 6h time shifted outside_air_temp column (for trop night calc.)
#	3. resample by day
#	4. get a min, max, mean and trop record
#	5. rename columns
#	6. build new dataframe
#	7. calc the additional key figures
#		- set flag if threshold reached
#		- change boolean to numeric
#
#	8. resample by month, sum up
#	9. sort dataframe for a consistent output
#	10. rename columns to a usable label
#
# III. output dataframe
#	1. save to csv for gnuplot
#	2. build new dataframe for output
#		- add sum row
#		- create new header
#		- rename timestamp column to monthname
#	3. save monthy dataframe to html table
#	4. run gnuplot
#	5. transfer include and png files
#
#
# Configuration options in config.py
#
# depends on:  WOSPi, numpy, pandas
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     13.02.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
# Update:
#    v1.1:     add 'fill' option
#    v1.2:     fix getopts typo, change plotting of ice days, add dummy data for missing months
#-------------------------------------------------------------------------------

import os, sys, shutil, re
import time, string
import getopt
from datetime import date, timedelta, datetime
from config import TMPPATH, HOMEPATH, CSVPATH, CSVFILESUFFIX, SCPTARGET, SCP

# numpy and panda for data structure
import pandas as pd
import numpy as np

# from local module
from wxtools import jump_by_month, print_dbg, stripNL, runGnuPlot, uploadPNG, uploadAny

#-------------------------------------------------------------------------------


# temp files for processing
statdata   = TMPPATH + 'plotuv.tmp'
statout_d  = TMPPATH + 'stat_uv_daily.csv'
statouuv_m  = TMPPATH + 'stat_uv_month.csv'
# outfile for SSI
statout_h  = TMPPATH + 'stat_uv.inc'
# labels for plot file
labelfile  = TMPPATH + 'labels.tmp'


# German labels
# see https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?nn=103346&lv2=101334&lv3=101452
# key is used for sortorder
LabelTextDE = {
 '_001xtitle'  : 'UV INDEX Statistik für',
 '_002ylabel'  : 'Anzahl der Tage',
 '_01uv_min'   : 'MinUVIndex',
 '_02uv_max'   : 'MaxUVIndex',
 '_03uv_mean'  : 'AvgUVIndex',
}

# English labels
LabelTextEN = {
 '_001xtitle'  : 'UV INDEX statistics for',
 '_002ylabel'  : 'Number of Days',
 '_01uv_min'   : 'MinUVIndex',
 '_02uv_max'   : 'MaxUVIndex',
 '_03uv_mean'  : 'AvgUVIndex',
}

# set to desired language
LabelText = LabelTextDE


# Celsius temperature limits
DEG_C = {
 '_04t_ice'    : 0,
 '_05t_frost'  : 0,
 '_06t_summer' : 25,
 '_07t_hot'    : 30,
 '_08t_desert' : 35,
 '_09t_trope'  : 20
}


# number to month mapping
months = {  1: 'Jan',
            2: 'Feb',
            3: 'Mar',
            4: 'Apr',
            5: 'May',
            6: 'Jun',
            7: 'Jul',
            8: 'Aug',
            9: 'Sep',
           10: 'Oct',
           11: 'Nov',
           12: 'Dec'
            }


# set debug level
DEBUG= False

# show some statistics in stdout
TRACE= True

# keep png files after upload
KEEP_PNG = False
# keep temporary files
KEEP_TMP = False
# upload png and inc
DO_SCP   = True

#
NB_DAYS = 370

#-------------------------------------------------------------------------------

def prepareCSVData(fromMonth,fromYear, tmpfile):
    """ merging csv files from YYYMM to current month
    """

    print_dbg(True, 'INFO : preparing CSV file')

    # get date to read the current csv
    YYMM = '%s' % time.strftime('%Y-%m')
    WX   = CSVPATH + YYMM + "-" + CSVFILESUFFIX

    # get name for previous csv
    fromYYMM = str(fromYear) + '-' + str(fromMonth).zfill(2)

    # remove existing temp file
    if (os.path.isfile(tmpfile)):
        os.unlink(tmpfile)

    start = date( year = fromYear, month = fromMonth, day = 1 )
    end   = date.today()

    print_dbg(DEBUG, "DEBUG: start: %s" % (start))
    print_dbg(DEBUG, "DEBUG: end  : %s" % (end))

    if (YYMM <> fromYYMM):
        print_dbg(DEBUG, "DEBUG: YYMM (%s) <> fromYYMM (%s)" % (YYMM,fromYYMM))
        # to add dummy data for missing months, now open target file inside the loop

        for dv in jump_by_month( start, end ):
            curYYMM = str(dv)[:7]
            WXcur = CSVPATH + curYYMM + "-" + CSVFILESUFFIX
            if (os.path.isfile(WXcur)):
                print_dbg(DEBUG, "DEBUG merging %s" % curYYMM)
                wx  = open(tmpfile, 'ab')
                wxc = open(WXcur,'rb')
                shutil.copyfileobj(wxc, wx)
                wxc.close()
                wx.close()
            else:
                # if year does not start in january (because you started with this project later)
                # it also plots january for the next year, which doesn't look pretty.
                # the reason seems to be the calculation of the trope nights because I shift the night
                # data to the next day.
                # the year is correctly plotted, if I add this monthly dummy line for the year, where you
                # started with wospi.
                # until I have a better solution (clipping the data for the next year after trope night calc,
                # I'll keep this workaround here. It works for my environment, hope, it works for yours aswell.
                # you can test be behaviour if you comment the "wx.write(...)" line below
                print_dbg(True, "WARN : missing data for %s" % curYYMM)
                curYY = str(dv)[:4]
                curMM = str(dv)[6:7].zfill(2)
                print_dbg(True, "WARN : adding dummy line for %s.%s" % (curMM,curYY))
                wx = open(tmpfile,'ab')
                wx.write('01.%s.%s 00:06:30,0,0,0,1000.0,0,0.0,0.0,0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0\n' % (curMM,curYY))
                wx.close()


    else:
        print_dbg(DEBUG, "DEBUG: YYMM (%s) == fromYYMM (%s)" % (YYMM,fromYYMM))
        print_dbg(True, "INFO : creating tmpcsv from %s" % YYMM)
        shutil.copyfile(WX,tmpfile)

    return


def read_wx_csv(wxin,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear, do_fill):
    """ read wxdata into pandas dataformat
    """

    print_dbg(True, 'INFO : building DataFrame')

    # sample data
    # 01.02.2016 00:05:19,3.9,90,2.2,1012.5,237,1.7,0.0,0,0.0,0.0,0.0,0.0,1.5,1.7,6.1,135

    # read all csv fields
    data = pd.read_csv(wxin, header=None, converters = {16 : stripNL})

    # fill future month records with empty data
    # to have a even plotted chart (needs commandline option 'f')
    if do_fill:
        fillMonth = datetime.now().month + 1
        print_dbg(True, "INFO : fill future months with empty data (%s - 12)" % fillMonth)
        for n in range(fillMonth,13):
            future_date  = '01.' + str(n).zfill(2) + '.' + str(toYear)
            data.loc[-1] = [future_date +" 00:00:00",0.0,90,0.0,1000.0,100,0.0,0.0,0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0]  # adding a row
            data.index   = data.index + 1  # shifting index
            print_dbg(DEBUG, "DEBUG: added fill data for date %s" % future_date)


    # rename columns
    data.rename(columns={ 0: 'timestamp',
                          1: 'outside_air_temp',
                          2: 'outside_rel_hum',
                          3: 'outside_dew_point_temp',
                          4: 'barometic_pressure',
                          5: 'present_wind_direction',
                          6: 'present_wind_speed',
                          7: 'UV_index',
                          8: 'solar_radiation',
                          9: 'rain_rate',
                         10: 'daily_rain',
                         11: 'daily_ET',
                         12: 'monthly_ET',
                         13: 'ten_min_avg_wind_speed',
                         14: 'two_min_avg_wind_speed',
                         15: 'ten_min_wind_gust_speed',
                         16: 'ten_min_wind_gust_direction'}, inplace=True)

    # convert date string field to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], format = '%d.%m.%Y %H:%M:%S')

    toHour = 23
    start_date = "%s-%s-%s %s:00:00" % (fromYear,str(fromMonth).zfill(2),str(fromDay).zfill(2),str(fromHour).zfill(2))
    end_date   = "%s-%s-%s %s:59:59" % (toYear,  str(toMonth).zfill(2),  str(toDay).zfill(2),  str(toHour).zfill(2))

    # select only the data within the timerange
    print_dbg(DEBUG, "DEBUG: mask = (data['timestamp'] >= %s) & (data['timestamp'] <= %s)" % (start_date,end_date))
    mask = (data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)
    plotdata = data.loc[mask]

    # use first col. as index
    plotdata.set_index('timestamp', inplace=True)

    if not KEEP_TMP:
        if (os.path.isfile(wxin)):
            os.unlink(wxin)

    return plotdata


def rebuild_name(fin,key):
    """ add year prefix to filename
    """
    bn = os.path.basename(fin)
    dn = os.path.dirname(fin)
    #fn = os.path.splitext(bn)[0]

    fout = dn + '/' + key + '.' + bn

    return fout


def uv_stats(pdin,key,fromMonth,toMonth,do_fill):
    """ calculate UV statistics per day and per month
    """
    print_dbg(True, 'INFO : calculating UV stats')

    # get UV column
    pd_uv  = pdin.iloc[:,[6]]
    FREQ = 'D'
    print_dbg(DEBUG, "DEBUG: pandas UV dataframe end: \n%s" % (pd_uv.tail(3)))

    # resample to day and calc some basic stats
    # old syntax
    # numpy: 1.6.2
    # pandas: 0.14.1
    #uv_mean = pd_uv.resample(FREQ, how='mean')
    #uv_max  = pd_uv.resample(FREQ, how='max')
    #uv_min  = pd_uv.resample(FREQ, how='min')
    # PLI new syntax
    # numpy: 1.12.1
    # pandas: 0.19.2
    uv_mean = pd_uv.resample(FREQ).mean()
    uv_max  = pd_uv.resample(FREQ).max()
    uv_min  = pd_uv.resample(FREQ).min()

    # drop last record for trope-night; due to timeshift before
    #if len(uv_min) < len(uv_min_n):
    #    uv_min_n=uv_min_n.iloc[:-1]

    # rename columns
    uvx_min  = uv_min.rename  (columns={'UV_index': '_01uv_min'})
    uvx_max  = uv_max.rename  (columns={'UV_index': '_02uv_max'})
    uvx_mean = uv_mean.rename (columns={'UV_index': '_03uv_mean'})

    print_dbg(DEBUG, "DEBUG: pandas UV uvx_mean: \n%s" % (uvx_mean.tail(3)))

    # create new dataframe
    uv_df = pd.concat([uvx_min, uvx_max, uvx_mean], axis=1)

    # help function
    isTrue = lambda x:int(x==True)
    isNeg  = lambda x:int(x < 0)


    #---------------------------------------------------------------------
    # show some stats
    #if TRACE:
        # overal statistics
        #d_desert = uv_max[uv_max["outside_air_temp"] >= 35 ].count()['outside_air_temp']
        #d_trope  = uv_df[uv_df["_09t_trope"] > 0 ].count()['_09t_trope']



    #---------------------------------------------------------------------

    # create monthly stats
    # PLI old syntax
    #m_df  = uv_df.resample('MS', how={'_01uv_min' :'min',
    #                                    '_02uv_max' :'max',
    #                                    '_03uv_mean':'mean',
    #                                })
    # PLI new syntax
    # numpy: 1.12.1
    # pandas: 0.19.2

    #agg_dict = { col:(uv_df.min() if col[1] == '_01uv_min'
    #    elif col[1] == '_02uv_max'
    #      uv_df.max()
    #      elif col[1] == '_03uv_mean'
    #      uv_df.mean()) for col in uv_df.columns
    #        }

    #m_df  = uv_df.resample('MS').apply(lambda x: agg_dict[x.name](x))

    m_df  = uv_df.resample('MS').agg({'_01uv_min' :'min',
                                        '_02uv_max' :'max',
                                        '_03uv_mean':'mean',
                                    })

    d_min    = "%.2f" % m_df._01uv_min.min()
    d_max    = "%.2f" % m_df._02uv_max.max()
    d_mean   = "%.2f" % m_df._03uv_mean.mean()

    # sort indices
    m_df.sort_index(axis=1, inplace=True)

    # rename sort header to usable names
    m_df.rename(columns=LabelText, inplace=True)

    # write daily and monthly stats to file
    ouuv_m = rebuild_name(statouuv_m,key)

    # save csv for plotting
    uv_df.to_csv(statout_d)
    m_df.to_csv(ouuv_m)

    if do_fill:
        fillMonth = datetime.now().month
        # now dropping the additional records which we have added before
        for n in range(toMonth,fillMonth,-1):
            print_dbg(DEBUG, 'DEBUG: removing empty month: n %s' % (n))
            m_df = m_df[:-1]


    # add sum to each column
    #df_col = ["timestamp","MinTemperatur","MaxTemperatur","AvgTemperatur",
    #          "Eistage","Frosttage","Sommertage","Hitzetage","Wuestentage","Tropennaechte"]

    df_col = ['timestamp']
    iterlabel = iter(sorted(LabelText))
    next(iterlabel)
    next(iterlabel)
    for n in iterlabel:
        df_col.append(LabelText[n])


    sum_val = [key + '-12-31',d_min,d_max,d_mean]

    # build new index names
    new_idx_names = []
    old_idx_names = m_df.index
    for n in range(len(m_df.index)):
        mon = old_idx_names[n].month
        new_idx_names.append(months[mon])


    new_idx_names.append(key)

    try:
        sum_df = pd.DataFrame([sum_val],columns=df_col)
        sum_df.set_index('timestamp', inplace=True)

        mx_df = pd.concat([m_df, sum_df])
        mx_df.index = new_idx_names
    except Exception as e:
        print_dbg(True, 'ERROR: exception(s) when creating sum: %s.' % e)


    return mx_df


def save_html(df,key):
    """ save table as html include (SSI)
    """
    out = rebuild_name(statout_h,key)

    with open(out, 'w') as f:
        f.write(df.to_html(header=True,classes='df',float_format=lambda x: '%10.2f' % x))
        f.close()

    uploadAny(out, DO_SCP, KEEP_TMP, SCP)


def save_labels(year):
    """ save labels to file to support
        languages without changing the gnuplot file
    """
    st = open(labelfile, 'w')
    st.write(year+'\n')

    for n in sorted(LabelText.keys()):
        rec = LabelText[n]

        if (n in DEG_C.keys()):
            rec += ';'+ str(DEG_C[n])

        st.write(rec+'\n')

    st.close()
    return


def plotUVstats(plt):
    """ create plot file from template and start gnuplot
    """
    if (sys.platform == "win32" ):
        inFile  = HOMEPATH + 'plot' + plt + '.win'
    else:
        inFile  = HOMEPATH + 'plot' + plt + '.input'
    outFile = TMPPATH  + 'plot' + plt + '.plt'

    print_dbg(True,"INFO : plot statistics with " + plt)
    shutil.copyfile(inFile, outFile)

    stdout_ = sys.stdout
    sys.stdout = runGnuPlot(plt,KEEP_TMP)
    sys.stdout = stdout_
    # ----
    # PLI
    #
    if not KEEP_TMP:
        if (os.path.isfile(labelfile)):
            os.unlink(labelfile)

    return


def usage():
    """ show all options
    """
    msg  = "\nusage: " + __file__ + " -c|-d|-l n -f -i y|m\n\n"
    msg += "\t\t-c --current :\t current interval\n"
    msg += "\t\t-l --last    :\t last interval, n ... number of years back\n"
    msg += "\t\t-i --interval:\t y ... yearly, m ... monthly\n"
    msg += "\t\t-f --fill    :\t fill upcomming months of current year with empty data\n"
    msg += "\t\t-d --day     :\t plot range from today and start NB_DAYS (" + str(NB_DAYS) + ")\n"
    msg += "\n"
    msg += "\te.g.: plot a yearly chart for the current year. Fill upcomming months.\n"
    msg += "\t      python plotUV.py -c\n"
    msg += "\t      python plotUV.py -l 1\n"
    msg += "\t      python plotUV.py -d\n"
    msg += "\n"

    print msg
    sys.exit(10)
    return


#-------------------------------------------------------------------------------

def main():
    errStat  = 0
    has_cmdc = False
    has_cmdl = False
    has_cmdi = False
    has_cmdf = False
    has_cmdd = False
    INTERVAL = 'y'
    YYYY_DIF = 1

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hcl:fi:d", ["help", "current", "last", "fill", "interval="])
    except getopt.GetoptError, err:
        # print help information and exit:
        log(E, str(err))
        usage()
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-c", "--current"):
            has_cmdc = True
        elif o in ("-l", "--last"):
            YYYY_DIF = a
            has_cmdl = True
        elif o in ("-i", "--interval"):
            INTERVAL = a
            has_cmdi = True
        elif o in ("-f", "--fill"):
            has_cmdf = True
        elif o in ("-d", "--days"):
            has_cmdd = True
        else:
            assert False, "unhandled option"


    if has_cmdi:
        if (INTERVAL <> "y") and (INTERVAL <> "m"):
            print_dbg(True, "ERROR: only 'y' or 'm' are allowed")
            usage()

    if (not has_cmdi) and (not has_cmdc) and (not has_cmdl) and (not has_cmdd):
        usage()

    if (has_cmdl):
        if (not YYYY_DIF.isdigit()):
            print_dbg(True, "ERROR: only digits are allowed with 'l'")
            usage()

    if has_cmdf:
        if (has_cmdl):
            print_dbg(True, "ERROR: option 'fill' only allowed with 'c'")
            usage()


    # test
    # d2 = date( year = 2017, month = 12, day = 31 )

    d2      = datetime.now()
    toDay   = d2.day
    toMonth = d2.month
    toYear  = d2.year
    fromDay = 1

    if has_cmdc:
        fromYear = toYear
        if INTERVAL  == 'y':
            fromMonth = 1
            key       = str(fromYear)
        else:
            fromMonth = toMonth
            key       = str(fromYear) + '-' + str(fromMonth).zfill(2)

    elif has_cmdl:
        if INTERVAL == 'y':
            toYear  -= int(YYYY_DIF)
            fromYear = toYear

            fromMonth = 1
            toMonth   = 12
            toDay     = 31
            key       = str(fromYear)
        else:
            firstDay  = d2.replace(day=1)
            lastMonth = firstDay - timedelta(days=1)

            toMonth   = lastMonth.month
            toDay     = lastMonth.day
            fromMonth = toMonth
            fromYear  = lastMonth.year
            toYear    = fromYear

            key       = str(fromYear) + '-' + str(fromMonth).zfill(2)

    elif has_cmdd:
        # PLI test always plt NB_DAYS
        fromDate  = d2 + timedelta(days = -NB_DAYS)
        fromDay   = fromDate.day
        fromMonth = fromDate.month
        fromYear  = fromDate.year
        key       = str(fromYear) + '-' + str(fromMonth).zfill(2)


    # fill month records with empty data
    if has_cmdf:
        toMonth   = 12
        key       = str(fromYear)

    # PLI test data
    #fromMonth = toMonth
    #key       = str(fromYear) + '-' + str(fromMonth).zfill(2)
    # PLI test data

    print_dbg(True, "INFO : plotinterval: %s.%s.%s - %s.%s.%s" \
            % (str(fromDay).zfill(2),str(fromMonth).zfill(2),fromYear,str(toDay).zfill(2),str(toMonth).zfill(2),toYear))

    # save year and other labels for gnuplot file
    save_labels(key)


    try:
        prepareCSVData(fromMonth,fromYear, statdata)
        wr = read_wx_csv(statdata,fromDay,fromMonth,fromYear,'00',toDay,toMonth,toYear,has_cmdf)

        df = uv_stats(wr,key,fromMonth,toMonth,has_cmdf)
        save_html(df, key)

        pkey = '_uv'
        plotUVstats(pkey)
        uploadPNG(TMPPATH  + 'plotuvindex_' + key + '.png', DO_SCP, KEEP_PNG, SCP)

        if not KEEP_TMP:
            if (os.path.isfile(statout_d)):
                os.unlink(statout_d)
            ouuv_m = rebuild_name(statouuv_m,key)
            print_dbg(DEBUG,"DEBUG: remove " + ouuv_m)
            if (os.path.isfile(ouuv_m)):
                os.unlink(ouuv_m)


    except Exception as e:
        print_dbg(True, 'ERROR: run with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')



if __name__ == '__main__':
    main()
