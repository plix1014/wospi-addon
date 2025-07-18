#!/usr/bin/python

# Create gnuplot of min/max temperatures for the last 12 months, SCP to web server.
# To be called by cron --- refer to the WOSPi documentation for details.
# Configuration options in config.py 
# 20131226/TMJ

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
    wospi.prepareTemperatureData(fromMonth, fromYear, toMonth, toYear)
    wospi.plotMinMaxTemp()
    os.system(wospi.SCPCOMMAND_PLOTMINMAXTEMP)
    if (os.path.isfile(wospi.PLOTMINMAXTEMP)):
        os.unlink(wospi.PLOTMINMAXTEMP)
except Exception as e:
    print('Done with exception(s): %s.' % e)
    errStat = 1

if(errStat == 0):
    print('Done.')


