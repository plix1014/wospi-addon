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
#-------------------------------------------------------------------------------
#

# basis directory of WOSPi installation
WOSPI=/home/wospi

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

SCPTARGET=$(grep ^FSCPTARGET $WOSPI/wetter/config.py \
    | awk -F"=" '{print $2}' \
    | tail -1 \
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
$WOSPI/tools/mk_awekas.sh
echo

# atwn
$WOSPI/tools/mk_atwn.sh
echo


echo "$(date)"
echo
echo "# 3 # transfer all to $REM_HOST:$REM_DIR"

cd $TMPDIR

# upload to Homepage
lftp $REM_HOST <<-EOF
cd $REM_DIR
put awekas.html
put atwn.txt
put conditions.inc
put vitamind.inc
put wxdata.xml
put wxdata.txt
lcd $LOCAL_TMP_DIR
put icon.html
mput *.txt
mput *.png
bye
quit
EOF

# upload CWOP
echo
echo "# 4 # upload to CWOP"
$WOSPI/tools/upload_cwop.py
echo

#$WOSPI/wetter/plotInternal.py 
#echo
#$WOSPI/tools/save_sunfile.sh

$WOSPI/tools/mk_raintable.sh

