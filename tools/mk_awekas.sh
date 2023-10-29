#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        mk_awekas.sh
# Purpose:     generate awekas.txt file from wospi data
#
# AWEKAS interface description
#   http://www.awekas.at/for2/index.php?page=Thread&threadID=229
# AWEKAS Homepage
#   http://www.awekas.at
#
#   AWEKAS configuration
#     for "Report Mode" => set: Davis Weather Link (HTX Template)
#
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
#

# basis directory of WOSPi installation
WOSPI_HOME=/home/wospi/wetter

# result file, used by awekas to fetch data
TARGET=awekas.txt

# --------------------------------------------------------------------
[ ! -r "$WOSPI_HOME/config.py" ] && echo "$WOSPI_HOME not found. configure script." && exit 10

# get config dirs
SOURCEDATA=$(grep ^CSVPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

TMPDIR=$(grep ^TMPPATH $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

INCHES=$(grep ^INCHES $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g" | tr '[:lower:]' '[:upper:]')

OUTFILE=$(grep ^OUTFILE $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | awk '{print $3}' \
    | sed -e 's, ,,g' -e "s,',,g")


DATE=$(date +'%Y-%m')
WXDATA=$SOURCEDATA/${DATE}-wxdata.csv
WXDATA_TXT=$TMPDIR/$OUTFILE

# --------------------------------------------------------------------

mk_template() {
    cat <<-EOF
AWEKAS_Template_start<br>
#temp#<br>
#hum#<br>
#press#<br>
#rfall#<br>
#wspeed#<br>
#bearing#<br>
#hour#:#minute#<br>
#day#/#month#/#year#<br>
#presstrend#<br>
-<br>
-<br>
-<br>
-<br>
-<br>
-<br>
-<br>
#wgust#<br>
#SolarRad#<br>
#UV#<br>
#rrate#<br>
---<br>
&deg;#tempunit#<br>
%<br>
#windunit#<br>
#pressunit#<br>
#rainunit#<br>
W/m&sup2;<br>
#rainrateunit#<br>
index<br>
Template_V1.5<br>

EOF
}


cd $TMPDIR
[ -f "$TARGET" ] && rm -f "$TARGET"
[ ! -r "$OUTFILE" ] && echo "$OUTFILE not found. configure script." && exit 1
[ ! -r "$WXDATA" ]  && echo "$WXDATA not found. configure script." && exit 2

if [ -f "$WXDATA" ]; then
    WX=$(tail -1 $WXDATA)

    echo "# 2 # generate $TARGET file..."
    echo "      last record from $WXDATA."
    echo "      $WX"

    # read line into array
    IFS="," read -a wxArray <<< "${WX}"

    # get special values
    DD=$(echo ${wxArray[0]} | awk -F"." '{print $1}')
    MM=$(echo ${wxArray[0]} | awk -F"." '{print $2}')
    YY=$(echo ${wxArray[0]} | awk -F"." '{print $3}' | awk '{print $1}')
    HH=$(echo ${wxArray[0]} | awk '{print $2}' | awk -F":" '{print $1}')
    MI=$(echo ${wxArray[0]} | awk '{print $2}' | awk -F":" '{print $2}')

    BAR_TREND=$(grep "Barometric Trend" $WXDATA_TXT \
	| awk -F":" '{print $2}' \
	| sed -e 's,^ ,,g' \
              -e 's,Barometric pressure is ,,g' \
	      -e 's,\.$,,g' \
              -e 's/.*/\u&/')

    if [ "$INCHES" = "FALSE" ]; then
	WIND_V=$(echo "scale=1; ${wxArray[6]} * 1852/1000" | bc -l)

	TEMP_U="C"
	WIND_U="km/hr"
	PRESS_U="hPa"
	RAIN_U="mm"
	RRAIN_U="$RAIN_U/hr"
    else
	WIND_V=$(echo "scale=1; ${wxArray[6]} * 1151/1000" | bc -l)

	TEMP_U="F"
	WIND_U="mph"
	PRESS_U="in"
	RAIN_U="in"
	RRAIN_U="$RAIN_U/hr"
    fi

    mk_template | sed -e "s,#temp#,${wxArray[1]},g" \
	-e "s,#hum#,${wxArray[2]},g" \
	-e "s,#press#,${wxArray[4]},g" \
	-e "s,#rfall#,${wxArray[10]},g" \
	-e "s,#wspeed#,${WIND_V},g" \
	-e "s,#bearing#,${wxArray[5]},g" \
	-e "s,#hour#,${HH},g" \
	-e "s,#minute#,${MI},g" \
	-e "s,#day#,${DD},g" \
	-e "s,#month#,${MM},g" \
	-e "s,#year#,${YY},g" \
	-e "s,#presstrend#,${BAR_TREND},g" \
	-e "s,#wgust#,${wxArray[15]},g" \
	-e "s,#SolarRad#,${wxArray[8]},g" \
	-e "s,#UV#,${wxArray[7]},g" \
	-e "s,#rrate#,${wxArray[9]},g" \
	-e "s,#tempunit#,$TEMP_U,g" \
	-e "s,#windunit#,$WIND_U,g" \
	-e "s,#pressunit#,$PRESS_U,g" \
	-e "s,#rainunit#,$RAIN_U,g" \
	-e "s,#rainrateunit#,$RRAIN_U,g" \
	> $TARGET

        # additionally save as html
        cp $TARGET ${TARGET%.txt}.html
fi

