#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        get_minmax_temp.sh
# Purpose:     show min/max values of a month
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     13.08.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 01.01.2024: make it work inside and outside of a container
#

WOSPI_HOME=/home/wospi/wetter
CONTAINER_HOME=/opt/docker/wospi

if [ -f "$WOSPI_HOME/config.py" ]; then
   CFG=$WOSPI_HOME/config.py 
elif [ -f "$CONTAINER_HOME/config/config.py" ]; then
   CFG=$CONTAINER_HOME/config/config.py
fi

TMP=$(mktemp -t .wxdata.XXXXXX)


CSV=$(grep "^CSVPATH" $CFG \
     | awk -F"=" '{print $2}' \
     | sed -e "s,',,g" \
     | awk '{print $1}' \
     | sed -e 's,/$,,g')


usage() {
    echo 
    echo "usage: ${0##*/} <month> { <day> <year> }"
    echo
    echo "  e.g.: ${0##*/} 08         ... show this august and this year min/max values"
    echo "  e.g.: ${0##*/} 08 17      ... show this august and this year min/max values and for this day"
    echo "  e.g.: ${0##*/} 08 17 2016 ... show august and year min/max values and for day"
    echo
    rm -f $TMP
    exit
}


prepare_data() {
    infile=$1
    year=$2
    month=$3
    day=$4

    if [ $# -eq 2 ]; then
	wxdate=$(echo ${infile##*/} | awk -F"-" '{print $1}')
	cat $CSV/${wxdate}-*-wxdata.csv > $TMP
    elif [ $# -eq 3 ]; then
	cat $infile > $TMP
    else
	cur_date=${day}.${month}.${year}
	grep "$cur_date" $infile > $TMP
    fi
}


max_val() {
    curmax=$(awk -F"," '{
    if (max == "") {
	max = $2; dt=$1
        } 
    {
	if ($2>max) {
	    max=$2; dt=$1;
        }
    }
    } 
    END {
	printf("%s => %5.1f\n",dt,max)}' $TMP)

    echo "$curmax"
}


min_val() {
    curmin=$(awk -F"," '{
    if (min == "") {
	min = $2; dt=$1
        } 
    {
	if ($2<min) {
	    min=$2; dt=$1;
        }
    }
    } 
    END {
	printf("%s => %5.1f\n",dt,min)}' $TMP)

    echo "$curmin"
}


if [ $# -eq 0 ]; then
    usage
fi

# get parameter
# 2017-08-wxdata.csv
MONTH=${1:-$(date '+%m')}
DAY=${2:-$(date '+%d')}
YEAR=${3:-$(date '+%Y')}


# normalize input
MONTH=$(echo $MONTH | bc)
DAY=$(echo $DAY | bc)

if [ $MONTH -lt 10 ]; then
    MONTH="0${MONTH}"
fi

if [ $DAY -lt 10 ]; then
    DAY="0${DAY}"
fi

if [ $YEAR -lt 100 ]; then
    YEAR="20${YEAR}"
fi

chk_date=${DAY}.${MONTH}.${YEAR}

# not found, eventually not in container
if [ ! -d "$CSV" ]; then
    CSV=$CONTAINER_HOME/csv_data
fi

# get input file
IN=$CSV/${YEAR}-${MONTH}-wxdata.csv

# -------------------------------------------------------------------

if [ -f "$IN" ]; then
    cd $CSV

    prepare_data $IN $YEAR $MONTH
    curmax=$(max_val)
    curmin=$(min_val)

    prepare_data $IN $YEAR
    thisymax=$(max_val)
    thisymin=$(min_val)

    echo
    echo "YEAR : $YEAR"
    echo "  MAX temp : ${thisymax}°C"
    echo "  MIN temp : ${thisymin}°C"
    echo
    echo "MONTH: $YEAR-${MONTH}"
    echo "  MAX temp : ${curmax}°C"
    echo "  MIN temp : ${curmin}°C"
    echo

    if [ -n "$chk_date" ]; then
	prepare_data $IN $YEAR $MONTH $DAY
	echo "DAY  : $YEAR-${MONTH}-${DAY}"
	echo "  MAX temp : $(max_val)°C"
	echo "  MIN temp : $(min_val)°C"
    fi
    echo


    rm $TMP

else
    if [ ! -f "$IN" ]; then
	echo "ERROR: input file '$IN' not found"
    fi

    usage
fi

