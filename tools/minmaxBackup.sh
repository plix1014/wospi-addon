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

DEBUG=1

YY=$(date +'%Y')
MM=$(date +'%m')
DD=$(date +'%d')

# try to find cal program
CAL=$(which cal)
if [ -z "$CAL" ]; then
    CAL=$(which ncal)
    if [ -z "$CAL" ]; then
	CAL=$(which gcal)
    fi
fi
if [ -z "$CAL" ]; then
    echo "ERROR: could not find 'cal' program. Exiting."
    exit 2
fi

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
    elif [ "$ARCH" = "aarch64" ]; then
	OPT="-H no"
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

if [ $DEBUG ]; then
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
fi

[ ! -d "$BK_DIR" ] && mkdir -p $BK_DIR


if [ $LASTDAY -eq $DD ]; then
    echo "$YY-$MM-$DD: today is last day of month. Backing up min-max values."
    cp -p $TMPDIR${MINMAXFILE} $BK_DIR/$MINMAXFILE.${YY}${MM}${DD}
    EL=$?
else
    echo "$YY-$MM-$DD: today is not the last day of month. Nothing to do."
fi

cd $TMP
if [ $(ls *.png > /dev/null 2>&1) ]; then
    echo "$YY-$MM-$DD: backup png files"
    echo "----------------------"
    tar cvf $BK_DIR/$YY$MM.png_backup.tar *.png
    echo "----------------------"
    echo "$YY-$MM-$DD: backup done"
else
    echo "$YY-$MM-$DD: no png files found"

fi

