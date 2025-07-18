#!/usr/bin/python

# Create gnuplot of annual wind direction readings for the last 12 months, SCP to web server.
# To be called by cron --- refer to the WOSPi documentation for details.
# Configuration options in config.py 
#
# 20131227/TMJ

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
    wospi.prepareAnnualWindData(fromMonth, fromYear, toMonth, toYear)
    wospi.plotAnnualWind()
    os.system(wospi.SCPCOMMAND_PLOTANNUALWIND)
    if (os.path.isfile(wospi.PLOTANNUALWIND)):
        os.unlink(wospi.PLOTANNUALWIND)
except Exception as e:
    print('Done with exception(s): %s.' % e)
    errStat = 1

if(errStat == 0):
    print('Done.')


