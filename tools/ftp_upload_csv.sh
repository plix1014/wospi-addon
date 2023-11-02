#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        ftp_upload_all.sh
# Purpose:     upload csv to homepage
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     05.04.2014
# Copyright:   (c) Peter Lidauer 2014
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 06.01.2016: csv
#  PLI, 28.07.2018: get ftp server from config.py
#  PLI, 24.10.2023: add REM_DIR to infoline
#   PLI, 02.11.2023: add TRANSFER_MODE
#

# basis directory of WOSPi installation
WOSPI=/home/wospi

# activate/deactivate upload scripts
RUN_UPD=1

# --------------------------------------------------------------------
[ ! -r "$WOSPI/wetter/config.py" ] && echo "ERROR: $WOSPI not found. configure script." && exit 10

# csv data
CSVPATH=$(grep ^CSVPATH $WOSPI/wetter/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

SCPTARGET=$(grep ^SCPTARGET $WOSPI/wetter/config.py \
    | awk -F"=" '{print $2}' \
    | tail -1 \
    | sed -e 's, ,,g' -e "s,',,g")

TRANSFER_MODE=$(grep ^SCP $WOSPI/wetter/config.py \
    | egrep -v "SCPTARGET|SCPCOMMAND" \
    | awk -F"=" '{print $2}'  \
    | sed -e 's, ,,g' -e "s,',,g")

REM_DIR=$(echo "$SCPTARGET"  | awk -F":" '{print $2}')


# last field should be ftp server
REM_HOST=$(echo "$SCPTARGET" \
    | awk -F":" '{print $1}' \
    | awk -F"@" '{print $NF}')


# --------------------------------------------------------------------


YYMM=$(date +'%Y-%m')
YY=$(date +'%Y')

if [ $RUN_UPD -eq 1 -a "$TRANSFER_MODE" = "fscp" ]; then
    echo "$(date)"
    echo
    echo "# 3 # transfer all to $REM_HOST:$REM_DIR"

    cd $CSVPATH

    # upload to Homepage
    lftp $REM_HOST <<-EOF
	cd $REM_DIR
	put $YYMM.rain
	put $YYMM-wxdata.csv
	put $YYMM-rain.csv
	put uptime.csv
	put ${YY}-soctemp.csv
	put suntimes.csv
	put ${YY}-internal.csv
	bye
	quit
	EOF
fi

