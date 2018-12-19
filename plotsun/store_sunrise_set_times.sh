#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        store_sunrise_set_times.sh
# Purpose:     saves sunrise and sunset times in csv for further processing
#              with plotSun.py
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     31.01.2016
# Copyright:   (c) Peter Lidauer 2016
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

# WOSPi installation directory
WOSPI_HOME=/home/wospi/weather

# --------------------------------------------------------------------
[ ! -r "$WOSPI_HOME/config.py" ] && echo "$WOSPI_HOME not found. configure script." && exit 10

SOURCEDATA=$(grep ^CSVPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

TMPDIR=$(grep ^TMPPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

OUTFILE=${SOURCEDATA}/suntimes.csv

cd $TMPDIR

if [ -f "sunrise.tmp" -a -f "sunset.tmp" ]; then
    rise=$(<sunrise.tmp)
    sset=$(awk '{print $2}' sunset.tmp)

    if [ -f "$OUTFILE" ]; then
	NR=$(grep -c "$rise $sset" $OUTFILE)
    else
	echo "Date       Sunrise  Sunset" >> $OUTFILE
	NR=0
    fi
    if [ $NR -eq 0 ]; then
	echo "adding times for $(awk '{print $1}' sunrise.tmp)"
	echo "$rise $sset" >> $OUTFILE
    else
	echo "times for $(awk '{print $1}' sunrise.tmp) already stored."
    fi
fi

