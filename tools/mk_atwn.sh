#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        mk_atwn.sh
# Purpose:     generate atwn.txt file from wospi data
#
# ATWN interface description
#   http://austrian-weather.com/wxconfig.php#weatherlink
# ATWN Homepage
#   http://austrian-weather.com/
#
#   ATWN configuration
#     for "Report Mode" => set: Davis Weather Link (HTX Template)
#
# depends on:  weather-tool.py
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     03.12.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
#

# basis directory of WOSPi installation
WOSPI=/home/wospi
WOSPI_HOME=$WOSPI/wetter

if [ -f "$WOSPI/tools/weather-tool.py" ]; then
    HEAT=$WOSPI/tools/weather-tool.py
else
    HEAT=$WOSPI/weather-tool.py
fi

# result file, used by ATWN to fetch data
TARGET=atwn.txt

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

# 4:25am,11/27/15,32.9,39.0,32.9,93,31.1,30.14,Steady,0,SSW,0.00,0,N/A ,6:58am,5:09pm 
# 4:37am,11/27/15,-0.5,4.3,-0.5,84,-4.2,24.39,Falling,0,NNE,0.00,0,,6:56am,4:38pm 
# 4:38a,11/27/15,51.5,51.9,51.5,96,50.4,29.868,Steady,0.0,ENE,0.00 

# 10:41,27/11/15,20.5,20.5,20.5,67,14.2,1014.2,Rising Rapidly,6.4,143,0.2,,06:56,16:53,6.4,12.9,°C|km/hr|hPa|mm
# <!--outsideHeatIndex-->,
#* <!--windChill-->, 
# <!--wind10Avg-->,
# <!--windAvg10-->,
# <!--windHigh10-->,

mk_template() {
    cat <<-EOF
<!--stationTime-->,<!--stationDate-->,<!--outsideTemp-->,<!--outsideHeatIndex-->,<!--windChill-->,<!--outsideHumidity-->,<!--outsideDewPt-->,<!--barometer-->,<!--BarTrend-->,<!--wind10Avg-->,<!--windDirection-->,<!--dailyRain-->,,<!--sunriseTime-->,<!--sunsetTime-->,<!--windAvg10-->,<!--windHigh10-->,<!--tempUnit-->|<!--windUnit-->|<!--barUnit-->|<!--rainUnit-->
EOF
}

get_heat_index() {
    ta=$1
    rh=$2

    $HEAT -r heatindex -t ${ta} -m ${rh} -u c
}

windchill_calc() {
    # equation for celsius degrees
    T="$1"
    V="$2"

    if [ -f "$HEAT" ]; then
	$HEAT -r windchill -t ${T} -w ${V} -u c
    else
	wct=$(grep "Wind Chill Temperature" $WXDATA_TXT \
	    | sed -e 's,^.*: ,,g' \
	    | awk -F"&" '{print $1}' \
	    | bc -l)
	[ -z "$wct" ] && wct=$T

	echo $wct
    fi
}

# --------------------------------------------------------------------
# The CSV data field order is as follows :
# 00. Timestamp on dd.mm.yyyy HH:MM:SS format
# 01. Outside air temperature in C
# 02. Outside relative humidity
# 03. Outside dew point temperature in C
# 04. Barometric pressure in hPa/mb
# 05. Present wind direction
# 06. Present wind speed in knots
# 07. UV index in range [0, 16]
# 08. Solar radiation (watts per m2) in range [0, 1800]
# 09. Rain rate in mm/hour
# 10. Daily rain in mm
# 11. Daily ET in mm
# 12. Monthly ET in mm
# 13. 10-minute average wind speed in knots
# 14. 2-minute average wind speed in knots
# 15. 10-minute wind gust speed in knots
# 16. 10-minute wind gust direction

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
	      -e 's,\.$,,g')
    #          -e 's/.*/\u&/')

    BAR_TREND=`echo ${BAR_TREND:0:1} | tr  '[a-z]' '[A-Z]'`${BAR_TREND:1}

    if [ "$INCHES" = "FALSE" ]; then
	WIND_V=$(echo "scale=1; ${wxArray[6]} * 1852/1000" | bc -l)
	WIND_A=$(echo "scale=1; ${wxArray[13]} * 1852/1000" | bc -l)
	WIND_G=$(echo "scale=1; ${wxArray[15]} * 1852/1000" | bc -l)

	TEMP_U="C"
	WIND_U="km/hr"
	PRESS_U="hPa"
	RAIN_U="mm"
	RRAIN_U="$RAIN_U/hr"
    else
	WIND_V=$(echo "scale=1; ${wxArray[6]} * 1151/1000" | bc -l)
	WIND_A=$(echo "scale=1; ${wxArray[13]} * 1151/1000" | bc -l)
	WIND_G=$(echo "scale=1; ${wxArray[15]} * 1151/1000" | bc -l)

	TEMP_U="F"
	WIND_U="mph"
	PRESS_U="in"
	RAIN_U="in"
	RRAIN_U="$RAIN_U/hr"
    fi

    SUN_TIMES=$(grep "SUN" $WXDATA_TXT \
	| sed -e 's,^.*occur at ,,g' \
 	      -e 's, LOCAL TIME.*$,,g')
    sunrise=$(echo $SUN_TIMES | awk '{print $1}')
    sunset=$(echo $SUN_TIMES | awk '{print $3}')

    ## TODO
    # <!--windAvg10-->,<!--windHigh10-->

    #  5: 6. Present wind direction
    #  6: 7. Present wind speed in knots
    # 13: 14. 10-minute average wind speed in knots
    # 15: 16. 10-minute wind gust speed in knots
    # 16: 17. 10-minute wind gust direction

    heatindex=$(get_heat_index ${wxArray[1]} ${wxArray[2]})
    wchill=$(windchill_calc ${wxArray[1]} ${WIND_V})

    echo "      DEBUG: $HEAT -r heatindex -t ${wxArray[1]} -m ${wxArray[2]} -u c => $heatindex"
    echo "      DEBUG: $HEAT -r windchill -t ${wxArray[1]} -w ${WIND_V} -u c  => $wchill"

    hh_mm="${HH}:${MI}"
    yy_mm_dd="${DD}/${MM}/${YY:2}"
    mk_template | sed -e "s,<!--outsideTemp-->,${wxArray[1]},g" \
	-e "s,<!--outsideHeatIndex-->,$heatindex,g" \
	-e "s,<!--outsideHumidity-->,${wxArray[2]},g" \
	-e "s,<!--outsideDewPt-->,${wxArray[3]},g" \
	-e "s,<!--barometer-->,${wxArray[4]},g" \
	-e "s,<!--dailyRain-->,${wxArray[10]},g" \
	-e "s,<!--windDirection-->,${wxArray[5]},g" \
	-e "s,<!--stationTime-->,${hh_mm},g" \
	-e "s,<!--stationDate-->,${yy_mm_dd},g" \
	-e "s,<!--BarTrend-->,${BAR_TREND},g" \
	-e "s,<!--wind10Avg-->,${WIND_A},g" \
	-e "s,<!--windAvg10-->,${WIND_A},g" \
	-e "s,<!--windChill-->,$wchill,g" \
	-e "s,<!--windHigh10-->,${WIND_G},g" \
	-e "s,<!--tempUnit-->,$TEMP_U,g" \
	-e "s,<!--windUnit-->,$WIND_U,g" \
	-e "s,<!--barUnit-->,$PRESS_U,g" \
	-e "s,<!--rainUnit-->,$RAIN_U,g" \
	-e "s,<!--sunriseTime-->,$sunrise,g" \
	-e "s,<!--sunsetTime-->,$sunset,g" \
	> $TARGET

fi

#echo "10:41,27/11/15,20.5,20.5,20.5,67,14.2,1014.2,Rapidly,6.4,143,0.2,,06:56,16:53,6.4,12.9,°C|km/hr|hPa|mm"
#echo "16:23,20/08/12,22.6,23.0,22.6,66,15.9,1015.0,Steady,3.2,S,0.0,, 6:16,20:41,1.6,1.6,°C|km/hr|mb|mm"
head -1 $TARGET | awk '{print "      "$0}'
