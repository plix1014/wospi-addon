#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        minmaxBackup.sh
# Purpose:     archives minmax stats every month
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     09.02.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
#

WOSPI_HOME=/home/wospi/wetter
BK_DIR=/home/wospi/backup

YY=$(date +'%Y')
MM=$(date +'%m')
DD=$(date +'%d')

CAL=cal

OS=$(uname -s)
ARCH=$(uname -m)
if [ "$OS" = "Darwin" ]; then
    OPT=
else
    # disable highlighting of current day
    if [ "$ARCH" = "armv6l" ]; then
	OPT="-h"
    elif [ "$ARCH" = "armv7l" ]; then
	OPT="-bh"
	CAL=ncal
    else
	OPT=
    fi
fi

MMYY=${1:-$MM $YY}

SOURCEDATA=$(grep ^CSVPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

TMPDIR=$(grep ^TMPPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

MINMAXFILE=$(grep ^MINMAXFILE $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e "s,',,g" | awk -F"+" '{print $2}' | awk '{print $1}')


TMP=$(grep "^SCPTARGET" $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's,^.*:,,g' -e "s,',,g")


LASTDAY=$($CAL $OPT $MMYY | tail -n +3 | tr '\n' ' ' | sort -n | awk 'END {print $NF}')

echo "#------- DEBUG -------"
echo "CAL    : $CAL $OPT $MMYY | tail -n +3 | tr '\n' ' ' | sort -n | awk 'END {print \$NF}'"
echo "YY     : $YY"
echo "MM     : $MM"
echo "DD     : $DD"
echo "LASTDAY: $LASTDAY"
echo "SOURCE : $TMPDIR$MINMAXFILE"
echo "TARGET : $BK_DIR/$MINMAXFILE.${YY}${MM}${DD}"
echo "CHECK  : [ $LASTDAY -eq $DD ]"
echo "#------- DEBUG -------"

if [ $LASTDAY -eq $DD ]; then
    echo "$YY-$MM-$DD: today is last day of month. Backing up min-max values."
    cp -p $TMPDIR${MINMAXFILE} $BK_DIR/$MINMAXFILE.${YY}${MM}${DD}
    EL=$?
else
    echo "$YY-$MM-$DD: today is not the last day of month. Nothing to do."
fi

echo "$YY-$MM-$DD: backup png files"
echo "----------------------"
cd $TMP
tar cvf $BK_DIR/$YY$MM.png_backup.tar *.png
echo "----------------------"
echo "$YY-$MM-$DD: backup done"

