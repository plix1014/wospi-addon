#!/usr/bin/python

# Create gnuplot of daily max UV/solar radiation readings for the last 12 months, SCP to web server.
# To be called by cron --- refer to the WOSPi documentation for details.
# Configuration options in config.py 
# 20141228/TMJ

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
    wospi.prepareSolarData(fromMonth, fromYear, toMonth, toYear)
    wospi.plotSolar()
    os.system(wospi.SCPCOMMAND_PLOTSOLAR)
    if (os.path.isfile(wospi.PLOTSOLAR)):
        os.unlink(wospi.PLOTSOLAR)
except Exception as e:
    print('Done with exception(s): %s.' % e)
    errStat = 1

if(errStat == 0):
    print('Done.')


