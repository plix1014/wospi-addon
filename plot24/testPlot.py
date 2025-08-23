#!/usr/bin/python

# Test script: create gnuplot of weather data, SCP to web server
# 20160115/TMJ

import wospi
import os

print('NOTE: this program will NOT update the sunrise/sunset times.')

errStat = 0
try:
    wospi.plotData()
    os.system(wospi.SCPCOMMAND_PLOT24FILE)
    os.system(wospi.SCPCOMMAND_PLOT24WIND)
except:
    print('Done with exception(s).')
    errStat = 1

if(errStat == 0):
    print('Done.')


