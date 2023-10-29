#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        mk_raintable.sh
# Purpose:     save hourly rain data into csv file
#
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     11.08.2017
# Copyright:   (c) Peter Lidauer 2017
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
#

# basis directory of WOSPi installation
WOSPI_HOME=/home/wospi/wetter


# --------------------------------------------------------------------
[ ! -r "$WOSPI_HOME/config.py" ] && echo "$WOSPI_HOME not found. configure script." && exit 10

# get config dirs
SOURCEDATA=$(grep ^CSVPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g" -e 's,\/$,,g')

TMPDIR=$(grep ^TMPPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

XMLFILE=$(grep ^XMLFILE $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | awk '{print $3}' \
    | sed -e 's, ,,g' -e "s,',,g")


DATE=$(date +'%Y-%m')
WXDATA=$SOURCEDATA/${DATE}-wxdata.csv

# result file, to store rain data
TARGET=$SOURCEDATA/${DATE}-rain.csv

# --------------------------------------------------------------------

cd $TMPDIR
[ ! -r "$WXDATA" ]  && echo "WXDATA $WXDATA not found. configure script." && exit 2

if [ -f "$WXDATA" ]; then
    WX=$(tail -1 $WXDATA)

    echo "# 5 # adding to $TARGET file..."

    # read line into array
    IFS="," read -a wxArray <<< "${WX}"

    # get special values
    DD=$(echo ${wxArray[0]} | awk -F"." '{print $1}')
    MM=$(echo ${wxArray[0]} | awk -F"." '{print $2}')
    YY=$(echo ${wxArray[0]} | awk -F"." '{print $3}' | awk '{print $1}')
    HH=$(echo ${wxArray[0]} | awk '{print $2}' | awk -F":" '{print $1}')
    MI=$(echo ${wxArray[0]} | awk '{print $2}' | awk -F":" '{print $2}')
    SS=$(echo ${wxArray[0]} | awk '{print $2}' | awk -F":" '{print $3}')

    # egrep "rain" wxdata.xml |sort
    # <dayrain_mm>0.0</dayrain_mm>
    # <monthrain_mm>7.8</monthrain_mm>
    # <rainfall15_mm>0.0</rainfall15_mm>
    # <rainfall24h_mm>0.0</rainfall24h_mm>
    # <rainfall60_mm>0.0</rainfall60_mm>
    # <rainrate_mmhr>0.0</rainrate_mmhr>
    # <stormrain_mm>0.0</stormrain_mm>
    # <yearrain_mm>307.2</yearrain_mm>
    #
    dayrain_mm=$(egrep "dayrain_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    monthrain_mm=$(egrep "monthrain_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    rainfall15_mm=$(egrep "rainfall15_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    rainfall24h_mm=$(egrep "rainfall24h_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    rainfall60_mm=$(egrep "rainfall60_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    rainrate_mmhr=$(egrep "rainrate_mmhr" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    stormrain_mm=$(egrep "stormrain_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')
    yearrain_mm=$(egrep "yearrain_mm" $XMLFILE | awk -F">" '{print $2}' | sed -e 's,<.*$,,g')

    # egrep "timestamp_pc" wxdata.xml
    # <timestamp_pc>2017-08-10 15:11:31.625682</timestamp_pc>
    #
    timestamp_pc=$(egrep "timestamp_pc" $XMLFILE |awk -F">" '{print $2}' | sed -e 's,<.*$,,g' -e 's,\..*$,,g')


    echo "      time of ${WXDATA##*/} ($YY-$MM-$DD $HH:$MI:$SS) vs. ${XMLFILE##*/} ($timestamp_pc)."

    echo "      header: timestamp,dayrain_mm,monthrain_mm,rainfall15_mm,rainfall24h_mm,rainfall60_mm,rainrate_mmhr,stormrain_mm,yearrain_mm"
    echo "      adding: $timestamp_pc,$dayrain_mm,$monthrain_mm,$rainfall15_mm,$rainfall24h_mm,$rainfall60_mm,$rainrate_mmhr,$stormrain_mm,$yearrain_mm"
    echo "$timestamp_pc,$dayrain_mm,$monthrain_mm,$rainfall15_mm,$rainfall24h_mm,$rainfall60_mm,$rainrate_mmhr,$stormrain_mm,$yearrain_mm" >> $TARGET

fi

