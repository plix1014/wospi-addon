#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        save_sunfiles
# Purpose:     saves sunrise and sunset times with full timestamp in csv
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     29.05.2014
# Copyright:   (c) Peter Lidauer 2014
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------


# WOSPi installation directory
WOSPI_HOME=/home/wospi/wetter

# --------------------------------------------------------------------
[ ! -r "$WOSPI_HOME/config.py" ] && echo "$WOSPI_HOME not found. configure script." && exit 10

SOURCEDATA=$(grep ^CSVPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

TMPDIR=$(grep ^TMPPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

OUTFILE=${SOURCEDATA}/vantage_suntimes.csv

DATE=$(date +'%d.%m.%Y %H:%M:%S')


cd $TMPDIR

if [ -f "sunrise.tmp" -a -f "sunset.tmp" ]; then
    rise=$(<sunrise.tmp)
    sset=$(<sunset.tmp)

    echo "adding times for $(awk '{print $1}' sunrise.tmp)"
    echo "$DATE | $rise | $sset" >> $OUTFILE
fi

