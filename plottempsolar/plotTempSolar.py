#!/usr/bin/python

# Create gnuplot of daily max temperature/solar radiation readings for the last 12 months, SCP to web server.
# To be called by cron --- refer to the WOSPi documentation for details.
# Configuration options in config.py 
# 20150323/TMJ

import wospi
import datetime
import os

errStat = 0

d2 = datetime.datetime.now()
d1 = d2 + datetime.timedelta(days = -365)  # by default grabbing data for the last year

toMonth = d2.month
toYear  = d2.year
fromMonth = d1.month
fromYear  = d1.year


try:
    wospi.prepareTemperatureAndSolarData(fromMonth, fromYear, toMonth, toYear)
    wospi.plotTempSolar()
    os.system(wospi.SCPCOMMAND_PLOTTEMPSOLAR)
    if (os.path.isfile(wospi.PLOTTEMPSOLAR)):
        os.unlink(wospi.PLOTTEMPSOLAR)
except Exception as e:
    print('Done with exception(s): %s.' % e)
    errStat = 1

if(errStat == 0):
    print('Done.')


