#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        fill_template.sh
# Purpose:     generate conditions.inc file from wospi data 
#              for use with index.shtml
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     05.04.2014
# Updated:     07.09.2017
# Copyright:   (c) Peter Lidauer 2014, 2017
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

# WOSPi installation directory
WOSPI_HOME=/home/wospi/wetter

# HTML include file
TARGET=conditions.inc
VIT_TGT=vitamind.inc

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

WX_LANG=$(grep ^beaufortText $WOSPI_HOME/config.py \
    | awk -F"=" '{print $2}' \
    | sed -e 's, ,,g' -e "s,',,g")

WXDATA_TXT=$TMPDIR/$OUTFILE

# --------------------------------------------------------------------

mk_cond_template() {
    cat <<-EOF
<b>Observations at __TIME__ LT</b><p/>

<table>
<tr>
<td>OAT  </td><td>__TEMP__&deg;C </td>
</tr>
<tr>
<td>WIND </td><td>__WIND_DEG__&deg; / __WIND_V__ __WIND_U__ </td>
</tr>
<tr>
<td>GUST </td><td>__GUST_DEG__&deg; / __GUST_V__ __WIND_U__ </td>
</tr>
<tr>
<td>QNH  </td><td>__BAR__ __PRESS_U__ </td>
</tr>
<tr>
<td>UV   </td><td>__UV__</td>
</tr>
<tr>
<td>SR   </td><td>__SR__ W </td>
</tr>
</table> <br />
__FORECAST__

EOF
}

mk_vitamin_template() {
    cat <<-EOF
<div align="center">
__VITAMIN_D_MSG__ 
</div>
EOF
}

# --------------------------------------------------------------------

cd $TMPDIR
[ ! -r "$WXDATA_TXT" ]  && echo "$WXDATA_TXT not found. configure script." && exit 2
[ -f "$TARGET" ] && rm -f "$TARGET"

TIME=$(grep "Received on"               $WXDATA_TXT | awk '{print $3" "$5}')
TEMP=$(grep "Outside Air Temperature"   $WXDATA_TXT | awk -F":" '{print $2}' \
    | sed -e 's,&.*$,,g' | awk '{print $1}' )
WIND_DEG=$(grep "Present Wind Velocity" $WXDATA_TXT | awk -F":" '{print $2}' \
    | sed -e 's,&.*$,,g' | bc)
WIND_KTS=$(grep "Present Wind Velocity" $WXDATA_TXT | awk -F":" '{print $2}' \
    | awk '{print $3}')
GUST_DEG=$(grep "10-Minute Wind Gust"   $WXDATA_TXT | awk -F":" '{print $2}' \
    | sed -e 's,&.*$,,g' | bc)
GUST_KTS=$(grep "10-Minute Wind Gust"   $WXDATA_TXT | awk -F":" '{print $2}' \
    | awk '{print $3}')
BAR=$(grep "Barometric Pressure"        $WXDATA_TXT | awk -F":" '{print $2}' \
    | awk '{print $1}' )
SR=$(grep "Solar Radiation"             $WXDATA_TXT | awk -F":" '{print $2}' \
    | awk '{print $1}' )
UV=$(grep "UV Index"                    $WXDATA_TXT | awk -F":" '{print $2}')

FORECAST=$(sed -n '/GENERAL FORECAST/,/---------------------------/p' $WXDATA_TXT \
    | head -n -2)
#FORECAST=$(sed -n '/GENERAL FORECAST/,/--------------------------/p' $WXDATA_TXT \
#    | head -n -2 \
#    | awk '{print "<br>"$0"</br>"}')

if [ "$INCHES" = "FALSE" ]; then
    WIND_V=$(echo "scale=1; $WIND_KTS * 1852/1000" | bc -l)
    GUST_V=$(echo "scale=1; $GUST_KTS * 1852/1000" | bc -l)

    WIND_U="km/h"
    PRESS_U="hPa"
else
    WIND_V=$WIND_KTS
    GUST_V=$GUST_KTS

    WIND_U="mph"
    PRESS_U="in"
fi

DOES_VITAD=$(bc <<< "$UV>3.0")
if [ $DOES_VITAD -eq 1 ]; then
    if [[ $WX_LANG =~ GE ]]; then
	VITAMIN_D_MSG="Vitamin D3 Synthese durch UV-B<br /> Strahlung ist nun möglich.<br /> Nutze die Sonne jetzt."
    else
	VITAMIN_D_MSG="Vitamin D3 synthesis by UV-B rays<br /> possible, if you expose<br /> your skin now"
    fi
else
    if [[ $WX_LANG =~ GE ]]; then
	VITAMIN_D_MSG="Derzeit ist leider keine<br />Vitamin D3 Synthese möglich"
    else
	VITAMIN_D_MSG="currently no Vitamin D3 synthesis<br /> possible"
    fi
fi

echo "# 1 # create $TARGET file"
mk_cond_template | sed -e "s,__TIME__,$TIME,g" \
    -e "s,__TEMP__,$TEMP,g" \
    -e "s,__WIND_DEG__,$WIND_DEG,g" \
    -e "s,__WIND_V__,$WIND_V,g" \
    -e "s,__WIND_U__,$WIND_U,g" \
    -e "s,__GUST_DEG__,$GUST_DEG,g" \
    -e "s,__GUST_V__,$GUST_V,g" \
    -e "s,__PRESS_U__,$PRESS_U,g" \
    -e "s,__BAR__,$BAR,g" \
    -e "s,__UV__,$UV,g" \
    -e "s,__SR__,$SR,g" \
    | awk -v FC="$FORECAST" '{ sub(/__FORECAST__/,FC); print }' > $TARGET



echo "# 1 # create $VIT_TGT file"
echo "      UV index is '$UV'. $VITAMIN_D_MSG"
mk_vitamin_template | sed -e "s#__VITAMIN_D_MSG__#$VITAMIN_D_MSG#g" > $VIT_TGT

echo

