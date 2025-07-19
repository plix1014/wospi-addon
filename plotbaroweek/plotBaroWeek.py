#!/usr/bin/python

# Create gnuplot of annual wind direction readings for the last 12 months, SCP to web server.
# To be called by cron --- refer to the WOSPi documentation for details.
# Configuration options in config.py 
#
# 20131230/TMJ

import wospi
import datetime
import os

errStat = 0

d2 = datetime.datetime.now()
d1 = d2 + datetime.timedelta(days = -7)  # by default grabbing data for the last week

toDay = d2.day
toMonth = d2.month
toYear  = d2.year
fromDay = d1.day
fromMonth = d1.month
fromYear  = d1.year


try:
    wospi.prepareBaroData(fromDay, fromMonth, fromYear, toDay, toMonth, toYear)
    wospi.plotBaroWeek()
    os.system(wospi.SCPCOMMAND_PLOTBAROWEEK)
    if (os.path.isfile(wospi.PLOTBAROWEEK)):
        os.unlink(wospi.PLOTBAROWEEK)
except Exception as e:
    print('Done with exception(s): %s.' % e)
    errStat = 1

if(errStat == 0):
    print('Done.')


