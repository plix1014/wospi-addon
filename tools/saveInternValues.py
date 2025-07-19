#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        saveInternValues.py
# Purpose:     save internal temperatur, RH, SoC temperatur, DHT22 temp/RH
#
# Configuration options in config.py
#
# depends on:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     25.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 15.11.2023: read HOMEPATH from environment
#  PLI, 18.07.2025: changes for python3
#

import sys, os, subprocess
from dotenv import load_dotenv

ENVFILE = '/tmp/.env'

load_dotenv(ENVFILE)
CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME)

HOMEPATH = CONFIG_HOME

from datetime import datetime, date
import re, time
#from config import CSVPATH, HOMEPATH, INTFILE, MINMAXFILE, TEMPERATUREFILE, read_txtfile
from config import CSVPATH, INTFILE, MINMAXFILE, TEMPERATUREFILE, read_txtfile
#import Adafruit_DHT

#CSVOUT = CSVPATH + 'internal.csv'

YEAR   = str(datetime.now().year)
CSVOUT = str(os.path.dirname(INTFILE)) + '/' + str(YEAR) + '-' + str(os.path.basename(INTFILE))

GPIO27 = 27
GPIO7  = 7
duration = 2

DHT22 = HOMEPATH + 'dht22.py'

# use real DHT
USE_DHT=False

#print "CSVOUT1: " + CSVOUT
#print "CSVOUT2: " + CSVOUT2
#sys.exit()

#-------------------------------------------------------------------------------

def save2CSV(csv,atTime,IntVal):

    try:
        fout = open(csv, 'a')
        max = len(IntVal) - 1

        print("header : datetime, SoC, IAT, Irh, DHTtemp, DHTrh")
        print("list   : %s" % IntVal)

        # first record is the date

        new_rec  = atTime + ', '
        # adding all fields
        for n in range(max):
            new_rec += IntVal[n] + ', '

        # add last record
        new_rec += IntVal[max] + '\n'

        print("new_rec: %s" % new_rec)

        fout.write(new_rec)
        fout.close()

    except Exception as e:
        print('Exception occured in function save2CSV. Check your code: %s' % e)

    return

def get_tempvals(infile):
    txt = read_txtfile(infile)
    T_RH = []

    # Console Temperature . : 20.7&deg;C / 69.3 &deg;F   RH: 44 %
    re_temphum = re.compile(r'\s+Console Temperature.*:\s+(\d+.\d+)&deg.*RH:\s+(\d+)\s+%')

    for line in txt:
        m = re.match(re_temphum, line)
        if m:
            T_RH = [m.group(1), m.group(2) ]

    return T_RH


def get_socval(infile):
    tt = read_txtfile(infile)
    return tt[0].strip()


def get_dht22(gpio):
    dht = ['0.0', '0']

    p = subprocess.Popen(DHT22, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (child_stdin, child_stdout) = (p.stdin, p.stdout)
    lines = child_stdout.readlines()

    dht_line = lines[-1].split()

    print(dht_line)

    # only use valid values
    if len(dht_line) == 8:
        dht = [dht_line[6], dht_line[2]]


    return dht


def get_dht22ADA(gpio):
    dht = ['0.0', '0']

    sensor22    = Adafruit_DHT.DHT22
    RH22, IAT22 = Adafruit_DHT.read_retry(sensor22, gpio)

    if RH22 is not None and IAT22 is not None:
        dht = ["%.1f" % IAT22, "%.1f" % RH22]
    else:
        print('Failed to get reading. Try again!')

    time.sleep(duration)

    return dht


def get_dht11ADA(gpio):
    dht = ['0.0', '0']

    sensor11    = Adafruit_DHT.DHT11
    RH11, IAT11 = Adafruit_DHT.read_retry(sensor11, gpio)

    if RH11 is not None and IAT11 is not None:
        dht = ["%.1f" % IAT11, "%.1f" % RH11]
    else:
        print('Failed to get reading. Try again!')

    time.sleep(duration)

    return dht



#-------------------------------------------------------------------------------

def main():

    rec = []

    # current time
    stringdate = datetime.strftime(datetime.now(), '%d.%m.%Y %H:%M:%S')

     # get SoC Temp
    rec.append(get_socval(TEMPERATUREFILE))

    # rec  : ['42.8', '22.1', '49']
    # rec22: ['21.4', '60.0']
    # rec11: ['20.0', '37.0']

    # get Internal Temp. and humidity
    rec += get_tempvals(MINMAXFILE)

    if USE_DHT:
        rec += get_dht22ADA(GPIO27)
        rec += get_dht11ADA(GPIO7)
    else:
        rec1 = get_tempvals(MINMAXFILE)
        rec0 = rec[-2:]
        rec += rec0
        rec += rec0

    save2CSV(CSVOUT,stringdate, rec)


if __name__ == '__main__':
    main()
