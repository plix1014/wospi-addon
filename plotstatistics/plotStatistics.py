#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotStatistics.py
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
# IV. same for rain statistics
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
#    v1.3:     changes for new pandas version (resample)
#    v1.4:     add rainstatistics
#    v1.5:     add dropna() to fix the MinTemperatur during the current month
#    v1.6:     exclude 'do_fill' in December
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 18.07.2025: changes for python3
#  PLI, 30.12.2025: remove border=1 from include html

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
statdata   = TMPPATH + 'plotstatistics.tmp'
statdata_r = TMPPATH + 'plotrainstatistics.tmp'
statout_d  = TMPPATH + 'statistics_daily.csv'
statout_dr = TMPPATH + 'statistics_daily_rain.csv'
statout_m  = TMPPATH + 'statistics_month.csv'
statout_mr = TMPPATH + 'statistics_month_rain.csv'

# outfile for SSI
statout_h  = TMPPATH + 'statistics.inc'
statout_hr = TMPPATH + 'statistics_rain.inc'

# labels for plot file
labelfile  = TMPPATH + 'labels.tmp'
labelfile_r = TMPPATH + 'labels_rain.tmp'

# rain suffix
RAINSUFFIX='rain'

# German labels
# see https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?nn=103346&lv2=101334&lv3=101452
# key is used for sortorder
LabelTextDE = {
 '_001xtitle'  : 'TEMPERATUR Statistik für',
 '_002ylabel'  : 'Anzahl der Tage',
 '_01temp_min' : 'MinTemperatur',
 '_02temp_max' : 'MaxTemperatur',
 '_03temp_mean': 'AvgTemperatur',
 '_04t_ice'    : 'Eistage',
 '_05t_frost'  : 'Frosttage',
 '_06t_summer' : 'Sommertage',
 '_07t_hot'    : 'Hitzetage',
 '_08t_desert' : 'Wuestentage',
 '_09t_trope'  : 'Tropennaechte'
}

LabelTextDE_Rain = {
 '_001xtitle'  : 'TEMPERATUR Statistik für',
 '_002ylabel'  : 'Anzahl der Tage',
 '_01rain_days'        :'Regentage',
 '_02daily_rain_max'   :'Tagesmaximum',
 '_03daily_rain_avg'   :'Tagesdurchschnitt pro Monat',
 '_04monthly_rain_max' :'Monatsniederschlag',
 '_05yearly_rain_max'  :'mm seit Jahresbeginn',
 '_06yearly_rain_mean' :'Monatsdurchschnitt'
}

# English labels
LabelTextEN = {
 '_001xtitle'  : 'TEMPERATURE statistics for',
 '_002ylabel'  : 'Number of Days',
 '_01temp_min' : 'MinTemperature',
 '_02temp_max' : 'MaxTemperature',
 '_03temp_mean': 'AvgTemperature',
 '_04t_ice'    : 'Ice days',
 '_05t_frost'  : 'Frost days',
 '_06t_summer' : 'Summer days',
 '_07t_hot'    : 'Hot days',
 '_08t_desert' : 'Desert days',
 '_09t_trope'  : 'Trop nights'
}

LabelTextEN_Rain = {
 '_001xtitle'  : 'TEMPERATURE statistics for',
 '_002ylabel'  : 'Number of Days',
 '_01rain_days'        :'Raindays',
 '_02daily_rain_max'   :'Daily Max',
 '_03daily_rain_avg'   :'Daily average per Month',
 '_04monthly_rain_max' :'Monathly Rain',
 '_05yearly_rain_max'  :'mm since BOY',
 '_06yearly_rain_mean' :'Monthy average'
}

# set to desired language
LabelText  = LabelTextEN
LabelTextR = LabelTextEN_Rain


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

#-------------------------------------------------------------------------------


def prepareCSVData(fromMonth,fromYear, tmpfile):
    """ merging csv files from YYYMM to current month
    """

    print_dbg(True, 'INFO : preparing temp CSV file')

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

    if (YYMM != fromYYMM):
        print_dbg(DEBUG, "DEBUG: YYMM (%s) != fromYYMM (%s)" % (YYMM,fromYYMM))
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


def prepareCSVDataRain(fromMonth,fromYear, tmpfile):
    """ merging rain csv files from YYYMM to current month
        DAY         DD   MM   YY
        04.05.2019, 0.2, 3.2, 80.4
    """

    print_dbg(True, 'INFO : preparing rain CSV file')

    # get date to read the current csv
    YYMM = '%s' % time.strftime('%Y-%m')
    RX   = CSVPATH + YYMM + "." + RAINSUFFIX

    # get name for previous csv
    fromYYMM = str(fromYear) + '-' + str(fromMonth).zfill(2)

    # remove existing temp file
    if (os.path.isfile(tmpfile)):
        os.unlink(tmpfile)

    start = date( year = fromYear, month = fromMonth, day = 1 )
    end   = date.today()

    print_dbg(DEBUG, "DEBUG: start: %s" % (start))
    print_dbg(DEBUG, "DEBUG: end  : %s" % (end))

    if (YYMM != fromYYMM):
        print_dbg(DEBUG, "DEBUG: YYMM (%s) != fromYYMM (%s)" % (YYMM,fromYYMM))
        # to add dummy data for missing months, now open target file inside the loop

        for dv in jump_by_month( start, end ):
            curYYMM = str(dv)[:7]
            RXcur = CSVPATH + curYYMM + "." + RAINSUFFIX
            if (os.path.isfile(RXcur)):
                print_dbg(DEBUG, "DEBUG merging %s" % curYYMM)
                rx  = open(tmpfile, 'ab')
                rxc = open(RXcur,'rb')
                shutil.copyfileobj(rxc, rx)
                rxc.close()
                rx.close()
            else:
                # if year does not start in january (because you started with this project later)
                # it also plots january for the next year, which doesn't look pretty.
                # the reason seems to be the calculation of the trope nights because I shift the night
                # data to the next day.
                # the year is correctly plotted, if I add this monthly dummy line for the year, where you
                # started with wospi.
                # until I have a better solution (clipping the data for the next year after trope night calc,
                # I'll keep this workaround here. It works for my environment, hope, it works for yours aswell.
                # you can test be behaviour if you comment the "rx.write(...)" line below
                print_dbg(True, "WARN : missing data for %s" % curYYMM)
                curYY = str(dv)[:4]
                curMM = str(dv)[6:7].zfill(2)
                print_dbg(True, "WARN : adding dummy line for %s.%s" % (curMM,curYY))
                rx = open(tmpfile,'ab')
                #         04.05.2019, 0.2, 3.2, 80.4
                rx.write('01.%s.%s,0.0,0.0,0.0\n' % (curMM,curYY))
                rx.close()


    else:
        print_dbg(DEBUG, "DEBUG: YYMM (%s) == fromYYMM (%s)" % (YYMM,fromYYMM))
        print_dbg(True, "INFO : creating tmpcsv from %s" % YYMM)
        shutil.copyfile(RX,tmpfile)

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
    if do_fill and int(datetime.now().month) < 12:
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


def read_rx_csv(rxin,fromDay,fromMonth,fromYear,fromHour,toDay,toMonth,toYear, do_fill):
    """ read rxdata into pandas dataformat
    """

    print_dbg(True, 'INFO : building DataFrame')

    # sample data
    # 04.05.2019, 0.2, 3.2, 80.4

    # read all csv fields
    data = pd.read_csv(rxin, header=None, converters = {4 : stripNL})

    # fill future month records with empty data
    # to have a even plotted chart (needs commandline option 'f')
    if do_fill and int(datetime.now().month) < 12:
        fillMonth = datetime.now().month + 1
        print_dbg(True, "INFO : fill future months with empty data (%s - 12)" % fillMonth)
        for n in range(fillMonth,13):
            future_date  = '01.' + str(n).zfill(2) + '.' + str(toYear)
            data.loc[-1] = [future_date,0.0,0.0,0.0]  # adding a row
            data.index   = data.index + 1  # shifting index
            print_dbg(DEBUG, "DEBUG: added fill data for date %s" % future_date)


    # rename columns
    data.rename(columns={ 0: 'timestamp',
                          1: 'rain_dd',
                          2: 'rain_mm',
                          3: 'rain_yy'}, inplace=True)

    # convert date string field to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], format = '%d.%m.%Y')

    start_date = "%s-%s-%s" % (fromYear,str(fromMonth).zfill(2),str(fromDay).zfill(2))
    end_date   = "%s-%s-%s" % (toYear,  str(toMonth).zfill(2),  str(toDay).zfill(2))

    # select only the data within the timerange
    print_dbg(DEBUG, "DEBUG: mask = (data['timestamp'] >= %s) & (data['timestamp'] <= %s)" % (start_date,end_date))
    mask = (data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)
    plotdata = data.loc[mask]

    # use first col. as index
    plotdata.set_index('timestamp', inplace=True)

    if not KEEP_TMP:
        if (os.path.isfile(rxin)):
            os.unlink(rxin)

    return plotdata


def rebuild_name(fin,key):
    """ add year prefix to filename
    """
    bn = os.path.basename(fin)
    dn = os.path.dirname(fin)
    #fn = os.path.splitext(bn)[0]

    fout = dn + '/' + key + '.' + bn

    return fout


def rain_stats(pdin,key,fromMonth,toMonth,do_fill):
    """ calculate rain statistics per day and per month
        # 05.01.2019, 7.4, 9.4, 9.4
        # 06.01.2019, 0.0, 9.4, 9.4
        # 07.01.2019, 0.0, 9.4, 9.4
        # 08.01.2019, 3.0, 12.4, 12.4
    """
    print_dbg(True, 'INFO : calculating rain stats')

    # get rain columns

    # month and year
    pd_rain  = pdin.iloc[:,[1,2]]

    # rain_dd
    pd_rain_d  = pdin.iloc[:,[0]]

    M_FREQ = 'ME'
    Q_FREQ = 'QE'

    # resample to day and calc some basic stats
    pd_ver = int(re.sub("\.","",pd.__version__))
    if (pd_ver <= 141):
        M_FREQ = 'M'
        # old syntax
        # numpy: 1.6.2
        # pandas: 0.14.1
        r_mean = pd_rain.resample(M_FREQ, how='mean')
        r_max   = pd_rain.resample(M_FREQ, how='max')
        r_max_d = pd_rain_d.resample(M_FREQ, how='max')
        r_sum_d = pd_rain_d.resample(M_FREQ, how='sum')

    else:
        # PLI new syntax
        # numpy: 1.12.1
        # pandas: 0.19.2
        r_mean = pd_rain.resample(M_FREQ).mean()
        r_max   = pd_rain.resample(M_FREQ).max()
        # max mm per day/month
        r_max_d = pd_rain_d.resample(M_FREQ).max()
        # r_sum_d = r_max = monthly rain
        r_sum_d = pd_rain_d.resample(M_FREQ).sum()
        r_sum_q = pd_rain_d.resample(Q_FREQ).sum()
        r_avg_m = pd_rain_d.resample(M_FREQ).mean()
        #r_avg_m = r_sum_d.resample(M_FREQ).mean()


    # number of rain days, avg mm/day (if raining)
    r_nr_d  = pd_rain_d.mask(pd_rain_d.rain_dd.le(0.2)).groupby(pd.Grouper(freq=M_FREQ)).count()
    r_avg_d = pd_rain_d.mask(pd_rain_d.rain_dd.le(0.2)).groupby(pd.Grouper(freq=M_FREQ)).mean()

    r_avg_m = r_sum_d.rolling(window=2).mean()
    #r_avg_m.at[key + '-01-31', 'rain_dd'] = r_sum_d.loc[key + '-01-31', 'rain_dd']

    date_key = pd.to_datetime(key + '-01-31')
    if date_key in r_sum_d.index:
        r_avg_m.at[date_key, 'rain_dd'] = r_sum_d.loc[date_key, 'rain_dd']
    else:
        print(f"Date {date_key} not found — skipping or filling with default.")
        r_avg_m.at[date_key, 'rain_dd'] = 0.0  # or np.nan



    for i in range(2,5):
           r_avg_m['MA{}'.format(i)] = r_sum_d.rolling(window=i).mean()


    rx_nr_d   = r_nr_d.rename  (columns={'rain_dd': '_01rain_days'})
    rx_d_max  = r_max_d.rename (columns={'rain_dd': '_02daily_rain_max'})
    rx_d_avg  = r_avg_d.rename (columns={'rain_dd': '_03daily_rain_avg'})

    rx_max  = r_max.rename  (columns={'rain_mm': '_04monthly_rain_max' , 'rain_yy': '_05yearly_rain_max' })
    rx_mean = r_mean.rename (columns={'rain_mm': '_07monthly_rain_mean', 'rain_yy': '_06yearly_rain_mean'})

    # we don't need _07month...
    rx_mean_y  = rx_mean.iloc[:,[1]]


    print_dbg(DEBUG, "DEBUG: pandas rain r_sum_d  : \n%s" % (r_sum_d))
    print_dbg(DEBUG, "DEBUG: pandas rain r_sum_q  : \n%s" % (r_sum_q))
    print_dbg(DEBUG, "DEBUG: pandas rain r_avg_d  : \n%s" % (r_avg_d))
    print_dbg(DEBUG, "DEBUG: pandas rain r_avg_m  : \n%s" % (r_avg_m))

    # create new dataframe
    rain_df = pd.concat([rx_nr_d, rx_d_max, rx_d_avg, rx_max, rx_mean_y], axis=1)
    print_dbg(DEBUG, "DEBUG: pandas rain rain_df: \n%s" % (rain_df))

    # replace NaN by '0';
    # needed if you provide the 'f' commandline parameter
    # because future values are generated with NaN
    rain_df.fillna(0, inplace=True)

    # create monthly stats
    if (pd_ver <= 141):
        # old syntax
        # numpy: 1.6.2
        # pandas: 0.14.1
        m_df  = rain_df.resample('MS', how={'_01rain_days'        :'sum',
                                            '_02daily_rain_max'   :'max',
                                            '_03daily_rain_avg'   :'mean',
                                            '_04monthly_rain_max' :'max',
                                            '_05yearly_rain_max'  :'max',
                                            '_06yearly_rain_mean' :'mean'
                                        })

    else:
        # PLI new syntax
        # numpy: 1.12.1
        # pandas: 0.19.2
        m_df  = rain_df.resample('MS').agg({'_01rain_days'        :'sum',
                                            '_02daily_rain_max'   :'max',
                                            '_03daily_rain_avg'   :'mean',
                                            '_04monthly_rain_max' :'max',
                                            '_05yearly_rain_max'  :'max',
                                            '_06yearly_rain_mean' :'mean'
                                        })

    m_df['_06yearly_rain_mean'] = m_df._06yearly_rain_mean.apply(lambda x: '-')
    print_dbg(DEBUG, "DEBUG: pandas rain m_df: \n%s" % (m_df))

    dd_sum    = "%.2f" % m_df._01rain_days.sum()
    dd_max    = "%.2f" % m_df._02daily_rain_max.max()
    dd_mean   = "%.2f" % m_df._03daily_rain_avg.mean()

    dm_max    = "%.2f" % m_df._04monthly_rain_max.max()

    dy_mean   = "%.2f" % m_df._04monthly_rain_max.mean()
    dy_max    = "%.2f" % m_df._05yearly_rain_max.max()

    if TRACE:
        print_dbg(True, "INFO : Raindays   : %s" % dd_sum)
        print_dbg(True, "INFO : max Day    : %s" % dd_max)
        print_dbg(True, "INFO : max Month  : %s" % dm_max)
        print_dbg(True, "INFO : mm/Year    : %s" % dy_max)

    # sort indices
    m_df.sort_index(axis=1, inplace=True)

    # rename sort header to usable names
    m_df.rename(columns=LabelTextR, inplace=True)

    # write daily and monthly stats to file
    out_m = rebuild_name(statout_mr,key)

    # save csv for plotting
    rain_df.to_csv(statout_dr)
    m_df.to_csv(out_m)

    if do_fill:
        fillMonth = datetime.now().month
        # now dropping the additional records which we have added before
        for n in range(toMonth,fillMonth,-1):
            print_dbg(DEBUG, 'DEBUG: removing empty month: n %s' % (n))
            m_df = m_df[:-1]


    df_col = ['timestamp']
    iterlabel = iter(sorted(LabelTextR))
    next(iterlabel)
    next(iterlabel)
    for n in iterlabel:
        df_col.append(LabelTextR[n])


    sum_val = [key + '-12-31',dd_sum,dd_max,dd_mean,dm_max,dy_max,dy_mean]

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

#------------------------------------------------------------------------------------------------------------

def temp_stats(pdin,key,fromMonth,toMonth,do_fill):
    """ calculate temperature statistics per day and per month
    """
    print_dbg(True, 'INFO : calculating temperature stats')

    # get temperature column
    pd_temp  = pdin.iloc[:,[0]]
    FREQ = 'D'
    print_dbg(DEBUG, "DEBUG: pandas temperature dataframe end: \n%s" % (pd_temp.tail(3)))

    # for calc. of the trope-night shift records between 18:00 - 06:00 to 00:00 - 12:00
    # need this for resampling
    # to have the required timerange within the same day
    # last night was a trope-night if between 06:00pm and 06:00am Tmin >= 20degC
    pdt = pd_temp.shift(6, freq='h')
    print_dbg(DEBUG, "DEBUG: pandas temperature df tshift 6h: \n%s" % (pdt.tail(3)))

    # the temperature we need to check is now between 00:00 and 12:00 noon
    # ignore everything outside, Tmin needs to be >= 20
    pdx = pdt.loc[(pdt.index.hour <= 12)]


    # resample to day and calc some basic stats
    pd_ver = int(re.sub("\.","",pd.__version__))
    if (pd_ver <= 141):
        # old syntax
        # numpy: 1.6.2
        # pandas: 0.14.1
        t_mean = pd_temp.resample(FREQ, how='mean')
        t_max  = pd_temp.resample(FREQ, how='max')
        t_min  = pd_temp.resample(FREQ, how='min')
        t_min_n= pdx.resample(FREQ, how='min')

    else:
        # PLI new syntax
        # numpy: 1.12.1
        # pandas: 0.19.2
        t_mean = pd_temp.resample(FREQ).mean()
        t_max  = pd_temp.resample(FREQ).max()
        t_min  = pd_temp.resample(FREQ).min()
        t_min_n= pdx.resample(FREQ).min()

    # drop last record for trope-night; due to timeshift before
    if len(t_min) < len(t_min_n):
        t_min_n=t_min_n.iloc[:-1]

    # rename columns
    tx_min  = t_min.rename  (columns={'outside_air_temp': '_01temp_min'})
    tx_max  = t_max.rename  (columns={'outside_air_temp': '_02temp_max'})
    tx_mean = t_mean.rename (columns={'outside_air_temp': '_03temp_mean'})
    tx_trop = t_min_n.rename(columns={'outside_air_temp': '_09temp_trope'})

    print_dbg(DEBUG, "DEBUG: pandas temperature tx_mean: \n%s" % (tx_mean.tail(3)))
    print_dbg(DEBUG, "DEBUG: pandas temperature tx_trop: \n%s" % (tx_trop.tail(3)))

    # create new dataframe
    temp_df = pd.concat([tx_min, tx_max, tx_mean, tx_trop], axis=1)

    # help function
    isTrue = lambda x:int(x==True)
    isNeg  = lambda x:int(x < 0)

    # replace NaN by '0';
    # needed if you provide the 'f' commandline parameter
    # because future values are generated with NaN
    temp_df.dropna(inplace=True)
    temp_df.fillna(0, inplace=True)

    # add additional stats rows
    temp_df['_04t_ice'   ] = np.sign(temp_df._02temp_max)
    temp_df['_05t_frost' ] = np.sign(temp_df._01temp_min)

    temp_df['_06t_summer'] = temp_df.apply(lambda e: e._02temp_max   >= DEG_C['_06t_summer'], axis=1)
    temp_df['_07t_hot'   ] = temp_df.apply(lambda e: e._02temp_max   >= DEG_C['_07t_hot'   ], axis=1)
    temp_df['_08t_desert'] = temp_df.apply(lambda e: e._02temp_max   >= DEG_C['_08t_desert'], axis=1)
    temp_df['_09t_trope' ] = temp_df.apply(lambda e: e._09temp_trope >= DEG_C['_09t_trope' ], axis=1)

    # recalc values
    temp_df['_04t_ice'   ] = temp_df.apply(lambda temp_df: isNeg (temp_df['_04t_ice'   ]),axis=1)
    temp_df['_05t_frost' ] = temp_df.apply(lambda temp_df: isNeg (temp_df['_05t_frost' ]),axis=1)
    temp_df['_06t_summer'] = temp_df.apply(lambda temp_df: isTrue(temp_df['_06t_summer']),axis=1)
    temp_df['_07t_hot'   ] = temp_df.apply(lambda temp_df: isTrue(temp_df['_07t_hot'   ]),axis=1)
    temp_df['_08t_desert'] = temp_df.apply(lambda temp_df: isTrue(temp_df['_08t_desert']),axis=1)
    temp_df['_09t_trope' ] = temp_df.apply(lambda temp_df: isTrue(temp_df['_09t_trope' ]) ,axis=1)

    # just for statistics
    d_ice    = temp_df['_04t_ice'].sum()
    d_frost  = temp_df['_05t_frost'].sum()
    d_summer = temp_df['_06t_summer'].sum()
    d_hot    = temp_df['_07t_hot'].sum()
    d_desert = temp_df['_08t_desert'].sum()
    d_trope  = temp_df['_09t_trope'].sum()

    #---------------------------------------------------------------------
    # show some stats
    if TRACE:
        # overal statistics
        #d_desert = t_max[t_max["outside_air_temp"] >= 35 ].count()['outside_air_temp']
        #d_trope  = temp_df[temp_df["_09t_trope"] > 0 ].count()['_09t_trope']

        # frost day
        print_dbg(True, "INFO : Icedays    : %s" % d_ice)
        print_dbg(True, "INFO : Frostdays  : %s" % d_frost)
        # hot day
        print_dbg(True, "INFO : Summerdays : %s" % d_summer)
        print_dbg(True, "INFO : Hotdays    : %s" % d_hot)
        print_dbg(True, "INFO : Desertdays : %s" % d_desert)
        print_dbg(True, "INFO : Tropenights: %s" % d_trope)


    #---------------------------------------------------------------------

    # create monthly stats
    if (pd_ver <= 141):
        # old syntax
        # numpy: 1.6.2
        # pandas: 0.14.1
        m_df  = temp_df.resample('MS', how={'_01temp_min' :'min',
                                            '_02temp_max' :'max',
                                            '_03temp_mean':'mean',
                                            '_04t_ice'    :'sum',
                                            '_05t_frost'  :'sum',
                                            '_06t_summer' :'sum',
                                            '_07t_hot'    :'sum',
                                            '_08t_desert' :'sum',
                                            '_09t_trope'  :'sum'
                                        })

    else:
        # PLI new syntax
        # numpy: 1.12.1
        # pandas: 0.19.2
        m_df  = temp_df.resample('MS').agg({'_01temp_min' :'min',
                                            '_02temp_max' :'max',
                                            '_03temp_mean':'mean',
                                            '_04t_ice'    :'sum',
                                            '_05t_frost'  :'sum',
                                            '_06t_summer' :'sum',
                                            '_07t_hot'    :'sum',
                                            '_08t_desert' :'sum',
                                            '_09t_trope'  :'sum'
                                        })

    d_min    = "%.2f" % m_df._01temp_min.min()
    d_max    = "%.2f" % m_df._02temp_max.max()
    d_mean   = "%.2f" % m_df._03temp_mean.mean()

    # sort indices
    m_df.sort_index(axis=1, inplace=True)

    # rename sort header to usable names
    m_df.rename(columns=LabelText, inplace=True)

    # write daily and monthly stats to file
    out_m = rebuild_name(statout_m,key)

    # save csv for plotting
    temp_df.to_csv(statout_d)
    m_df.to_csv(out_m)

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


    sum_val = [key + '-12-31',d_min,d_max,d_mean,d_ice,d_frost,d_summer,d_hot,d_desert,d_trope]

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


def save_html(df,key,tm):
    """ save table as html include (SSI)
    """
    if tm == 't':
        sout = statout_h
    else:
        sout = statout_hr

    out = rebuild_name(sout,key)

    html = df.to_html(header=True,classes='df',float_format=lambda x: '%10.2f' % x)

    # Remove obsolete border attribute
    html = html.replace('border="1"', '')

    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
        f.close()

    uploadAny(out, DO_SCP, KEEP_TMP, SCP)
    return


def save_labels(year,tm):
    """ save labels to file to support
        languages without changing the gnuplot file
    """
    if tm == 't':
        lf = labelfile
        lt = LabelText
    else:
        lf = labelfile_r
        lt = LabelTextR

    st = open(lf, 'w')
    st.write(year+'\n')

    for n in sorted(lt.keys()):
        rec = lt[n]

        if (n in DEG_C.keys()):
            rec += ';'+ str(DEG_C[n])

        st.write(rec+'\n')

    st.close()
    return


def plotStatistics(plt,tm):
    """ create plot file from template and start gnuplot
    """
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
        if tm == 't':
            lf = labelfile
        else:
            lf = labelfile_r

        if (os.path.isfile(lf)):
            os.unlink(lf)

    return


def usage():
    """ show all options
    """
    msg  = "\nusage: " + __file__ + " -c|-l n -f -i y|m\n\n"
    msg += "\t\t-c --current :\t current interval\n"
    msg += "\t\t-l --last    :\t last interval, n ... number of years back\n"
    msg += "\t\t-i --interval:\t y ... yearly, m ... monthly\n"
    msg += "\t\t-f --fill    :\t fill upcomming months of current year with empty data\n"
    msg += "\n"
    msg += "\te.g.: plot a yearly chart for the current year. Fill upcomming months.\n"
    msg += "\t      python plotStatistics.py -c -f -i y\n"
    msg += "\n"

    print(msg)
    sys.exit(10)
    return


#-------------------------------------------------------------------------------

def main():
    errStat  = 0
    has_cmdc = False
    has_cmdl = False
    has_cmdi = False
    has_cmdf = False
    INTERVAL = 'y'
    YYYY_DIF = 1

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hcl:fi:", ["help", "current", "last", "fill", "interval="])
    except getopt.GetoptError as err:
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
        else:
            assert False, "unhandled option"


    if has_cmdi:
        if (INTERVAL != "y") and (INTERVAL != "m"):
            print_dbg(True, "ERROR: only 'y' or 'm' are allowed")
            usage()

    if (not has_cmdi) and (not has_cmdc) and (not has_cmdl):
        usage()

    if (has_cmdl):
        if (not YYYY_DIF.isdigit()):
            print_dbg(True, "ERROR: only digits are allowed with 'l'")
            usage()

    if has_cmdf:
        if (has_cmdl):
            print_dbg(True, "ERROR: option 'fill' only allowed with 'c'")
            usage()


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

    # fill month records with empty data
    if has_cmdf:
        toMonth   = 12
        toDay     = 31
        key       = str(fromYear)

    print_dbg(True, "INFO : plotinterval: %s.%s.%s - %s.%s.%s" \
            % (str(fromDay).zfill(2),str(fromMonth).zfill(2),fromYear,str(toDay).zfill(2),str(toMonth).zfill(2),toYear))

    # save year and other labels for gnuplot file
    save_labels(key,'t')
    save_labels(key,'r')


    try:
        prepareCSVData(fromMonth,fromYear, statdata)
        wr = read_wx_csv(statdata,fromDay,fromMonth,fromYear,'00',toDay,toMonth,toYear,has_cmdf)

        df = temp_stats(wr,key,fromMonth,toMonth,has_cmdf)
        save_html(df, key,'t')

        pkey = 'temp_year'
        plotStatistics(pkey,'t')
        uploadPNG(TMPPATH  + 'plottemp_' + key + '.png', DO_SCP, KEEP_PNG, SCP)

        prepareCSVDataRain(fromMonth,fromYear, statdata_r)
        wr_r = read_rx_csv(statdata_r,fromDay,fromMonth,fromYear,'00',toDay,toMonth,toYear,has_cmdf)

        df_r = rain_stats(wr_r,key,fromMonth,toMonth,has_cmdf)
        save_html(df_r, key,'r')

        pkey = 'monthlyrain'
        plotStatistics(pkey,'t')
        uploadPNG(TMPPATH  + 'monthlyrain_' + key + '.png', DO_SCP, KEEP_PNG, SCP)
        if not KEEP_TMP:
            if (os.path.isfile(statout_d)):
                os.unlink(statout_d)
            if (os.path.isfile(statout_dr)):
                os.unlink(statout_dr)
            out_m  = rebuild_name(statout_m,key)
            out_mr = rebuild_name(statout_mr,key)
            print_dbg(DEBUG,"DEBUG: remove " + out_m)
            if (os.path.isfile(out_m)):
                os.unlink(out_m)
            if (os.path.isfile(out_mr)):
                os.unlink(out_mr)


    except Exception as e:
        print_dbg(True, 'ERROR: run with exception(s): %s.' % e)
        errStat = 1

    if(errStat == 0):
        print_dbg(True, 'INFO : Done.')



if __name__ == '__main__':
    main()
