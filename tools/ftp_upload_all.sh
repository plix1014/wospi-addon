#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        ftp_upload_all.sh
# Purpose:     upload WOSPi generated weather data to homepage
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
#   PLI, 29.11.2015: atwn
#   PLI, 07.12.2015: cwop
#   PLI, 03.01.2016: wxdata path change
#   PLI, 28.07.2018: get ftp server from config.py
#   PLI, 22.10.2023: get LOCAL_TMP_DIR
#   PLI, 02.11.2023: add TRANSFER_MODE
#-------------------------------------------------------------------------------
#

# basis directory of WOSPi installation
WOSPI=/home/wospi

# activate/deactivate upload scripts
RUN_UPD=1

# https://www.awekas.at/wp/
RUN_AWEKAS=1
# http://austrian-weather.com/
RUN_ATWN=1
# APRS upload
RUN_CWOP=1
# save each precipitation values into csv (instead of daily sums)
RUN_RAIN=1

# OpenWeatherMap
RUN_OWN=1

# internal temperature
RUN_INTERN=0
# sunfile backup
RUN_SUN=0

# --------------------------------------------------------------------
[ ! -r "$WOSPI/wetter/config.py" ] && echo "ERROR: $WOSPI not found. configure script." && exit 10

# get temp dir
TMPDIR=$(grep ^TMPPATH $WOSPI/wetter/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

LOCAL_TMP_DIR=$(grep ^LOCAL_TMP_DIR $WOSPI/wetter/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g" \
    | sed -e 's,TMPPATH,$TMPDIR,g' \
    | tr '+' '/')

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
# fill html include file
$WOSPI/tools/fill_template.sh

# awekas
if [ $RUN_AWEKAS -eq 1 ]; then
    $WOSPI/tools/mk_awekas.sh
    echo
fi

# atwn
if [ $RUN_ATWN -eq 1 ]; then
    $WOSPI/tools/mk_atwn.sh
    echo
fi


if [ $RUN_UPD -eq 1 -a "$TRANSFER_MODE" = "fscp" ]; then
    echo "$(date)"
    echo
    echo "# 3 # transfer all to $REM_HOST:$REM_DIR"

    cd $TMPDIR

    # currently disabled
	#lcd $LOCAL_TMP_DIR
	#put icon.html
	#mput *.txt
	#mput *.png

    # upload to Homepage
    lftp $REM_HOST <<-EOF
	cd $REM_DIR
	put awekas.html
	put atwn.txt
	put conditions.inc
	put vitamind.inc
	put wxdata.xml
	put wxdata.txt
	bye
	quit
	EOF
fi

# upload CWOP
if [ $RUN_CWOP -eq 1 ]; then
    echo
    echo "# 4 # upload to CWOP"
    $WOSPI/tools/upload_cwop.py
    echo
fi

# save each precipitation values into csv (instead of daily sums)
if [ $RUN_RAIN -eq 1 ]; then
    echo
    echo "# 5 # save raindata"
    $WOSPI/tools/mk_raintable.sh
    echo
fi

# internal temperature
if [ $RUN_INTERN -eq 1 ]; then
    $WOSPI/wetter/plotInternal.py 
    echo
fi

# upload to Openweathermap
if [ $RUN_OWN -eq 1 ]; then
    $WOSPI/tools/openweather_upload.py
    echo
fi

# sunfile backup
if [ $RUN_SUN -eq 1 ]; then
    $WOSPI/tools/save_sunfile.sh
fi

