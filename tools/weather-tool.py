#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#-------------------------------------------------------------------------------
# Name:        weather-tool.py
# Purpose:     calculate some weather indices
#
# used by:     mk_atwn.sh
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     03.12.2015
# Copyright:   (c) Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------

import getopt
import sys
from math import log, e, exp


# C is default unit
CELSIUS = True

# text language of heat/hum- index message
LANG_DE=True

# DEBUG
# display text info
DEBUG=False

#----------------------------------------------------------------------
# functions
#----------------------------------------------------------------------

def c_to_f(to_f):
    """ celsius to fahrenheit conversion
    """
    to_f = float(to_f)
    return to_f * 9.0/5.0 + 32.0

def f_to_c(to_c):
    """ fahrenheit to celsius conversion
    """
    to_c = float(to_c)
    return (to_c - 32.0) * 5.0/9.0

def mph2kmh(v):
    """ convert mph to km/h
    """
    v = float(v)
    return v * 1.609344

def kmh2mph(v):
    """ convert km/h to mph
    """
    v = float(v)
    return v/1.609344

def kn2kmh(v):
    """ convert kn to km/h
        1 kn = 463m/900s
    """
    v = float(v)
    return v * 463/900*3.6

def kmh2kn(v):
    """ convert km/h to kn
    """
    v = float(v)
    return v*900/463/3.6

def log10(n):
    """ logarithm to base 10
    """
    return log(n,10)

def ln(n):
    """ natural logarithm
    """
    # just to be save. log(0) is not defined
    if (n == 0):
        n = 0.000000001

    return log(n,e)


def c2kelvin(T):
    """ convert temperatur to Kelvin
    """
    T = float(T)
    return (T + 273.15)


def usage(EL=10):
    """ usage for this program
    """
    print " select result type"
    print "  -r (result) {type}     ... result of calculation"
    print "        heatindex        ... heat index calculation"
    print "        hi_txt           ... descriptiv heat index"
    print "        humidex          ... canadian humidex calculation"
    print "        hu_txt           ... descriptiv canadian humidex"
    print "        ssi              ... summer-simmer-index"
    print "        ssi_txt          ... descriptiv summer-simmer-index"
    print "        THW              ... THW index"
    print "        THSW             ... THSW index"
    print "        dewpoint         ... dewpoint calculation"
    print "        humidity         ... relativ humidity calculation"
    print "        windchill        ... windchill calculation\n"

    print " input values, depending of type selection"
    print "  -t (temp)     {deg }   ... current air temperature"
    print "  -m (rhum)     {hum %}  ... humidity"
    print "  -d (dewpoint) {deg }   ... dewpoint"
    print "  -w (wind)     {kmh }   ... windspeed\n"

    print "  -u (unit) {c|f}        ... [c]elsius (is default) or [f]ahrenheit"
    print "  -h (help)              ... this help screen\n"

    sys.exit(EL)
    return

#----------------------------------------------------------------------

def rh_limit(rh):
    """ limit relative humidity
        to valid borders
    """
    if (rh < 1  ):
        rh = 1
    if (rh > 100):
        rh = 100

    return rh


def heat_c(h_tf,h_rh):
    """ calculate heatindex for celsius deg
    """
    # https://en.wikipedia.org/wiki/Heat_index
    # http://www.iweathernet.com/educational/heat-index-calculator-and-conversion-table
    #

    h_tf = float(h_tf)
    h_rh = rh_limit(float(h_rh))

    if (h_tf >= 24):
	return (-8.784695 + 1.61139411 * h_tf
	+ 2.338549 * h_rh
	- 0.14611605 * h_tf * h_rh
	- (1.2308094 * 10**(-2)) * (h_tf**(2))
	- (1.6424828 * 10**(-2)) * (h_rh**(2))
	+ (2.211732 * 10**(-3)) * (h_tf**(2)) * h_rh
	+ (7.2546 * 10**(-4)) * h_tf * (h_rh**(2))
	- (3.582 * 10**(-6)) * (h_tf**(2.0)) * (h_rh**(2.0)))
    else:
	return h_tf


def heat_f(h_tf,h_rh):
    """ calculate heatindex for fahrenheit deg
    """
    # https://en.wikipedia.org/wiki/Heat_index
    # http://www.iweathernet.com/educational/heat-index-calculator-and-conversion-table
    #

    h_tf = float(h_tf)
    h_rh = rh_limit(float(h_rh))

    if (h_tf >= 75):
	return (-42.379 + 2.04901523 * h_tf
            + 10.14333127 * h_rh
            - 0.22475541 * h_tf * h_rh
            - (6.83783 * 10**(-3)) * (h_tf**(2))
            - (5.481717 * 10**(-2)) * (h_rh**(2))
            + (1.22874 * 10**(-3)) * (h_tf**(2)) * h_rh
            + (8.5282 * 10**(-4)) * h_tf * (h_rh**(2))
            - (1.99 * 10**(-6)) * (h_tf**(2)) * (h_rh**(2)))
    else:
	return h_tf

def heatdew_f(tair,tdew):
    """ calculate heatindex from temperature and dewpoint
    """
    return


def humidex(tair,rhum):
    """ calculates the Humidex
        http://www.csgnetwork.com/canhumidexcalc.html
    """

    tair = float(tair)
    rhum = rh_limit(float(rhum))

    t_kelvin = c2kelvin(tair)
    y = (-2937.4/t_kelvin)-4.9283 * log(t_kelvin)/ln(10) + 23.5471
    eTs = 10**y
    eTd = eTs * rhum/100.0

    hidx = (tair + (eTd - 10) * 5.0/9.0)

    if (hidx < tair):
        hidx = tair

    return hidx


def THW_f(tair,rhum,wind):
    """ calc the temp/hum/wind index
        HI ... in F
        W  ... in miles/h
        THW = HI - 1.072 * W
    """
    wind = float(wind)
    THW = heat_f(tair,rhum) -  1.072 * wind

    return THW

def dewpoint_c(tair,rhum):
    """ dewpoint calculated
        by Davis Vantage weather stations
    """

    tair = float(tair)
    rhum = rh_limit(float(rhum))

    # for -45C <= tair <= 60C
    K1 = 6.112
    K2 = 17.62
    K3 = 243.12

    y = K2*tair/(tair + K3)

    vp     = rhum * 0.01 * K1*exp(y)
    lnvp   = ln(vp)
    dewp   = (K3*lnvp - 440.1)/(19.43 - lnvp)

    return dewp

def dewpoint_magnus(tair,rhum):
    """ dewpoint calculated
        based by Magnus-Equation
        http://www.schweizer-fn.de/lueftung/feuchte/feuchte.php
    """

    tair = float(tair)
    rhum = rh_limit(float(rhum))

    if (tair > 0.0):
        # -50 < tair <= +100
        c1=6.1078
        c2=17.08085
        c3=234.175
    else:
        # -50 < tair <= 0
        c1=6.1078
        c2=17.84362
        c3=245.425

    y    = c2*tair/(c3 + tair)
    lnrh = ln(rhum/100)

    dewp   = (c3*(lnrh + y)/(c2 - lnrh - y))

    return dewp


def windchill_c(T,V):
    """ windchill calculated
        by Davis Vantage weather stations
    """
    # if wxDict['WC_C'] >= -40 and wxDict['WC_C'] <= 60:

    T = float(T)
    V = float(V)

    # 
    K1 = 13.12
    K2 = 0.6215
    K3 = 11.37
    K4 = 0.3965

    vx = V**0.16

    WCT = K1 + K2*T - K3*vx + K4*T*vx

    if (WCT > T):
        # windchill temp cannot be higher than air temperature
        WCT = T

    return WCT

def windchill_f(T,V):
    """ windchill calculated
        by Davis Vantage weather stations
    """

    T = float(T)
    V = float(V)

    # 
    K1 = 35.74
    K2 = 0.6215
    K3 = 35.75
    K4 = 0.4275

    vx = V**0.16

    WCT = K1 + K2*T - K3*vx + K4*T*vx

    return WCT


def humidity_c(T,TD):
    """ humidity from temp. and dewpoint
        http://www.wetterochs.de/wetter/feuchte.html
    """

    T  = float(T)
    TD = float(TD)

    # Td cannot be higher then T
    if ( TD > T ):
        TD = T

    # 
    if (T >= 0.0):
        a = 7.5
        b = 237.3
    else:
        a = 7.6
        b = 240.7

    vpt = 6.1078 * 10**((a*T)/(b+T))
    vpd = 6.1078 * 10**((a*TD)/(b+TD))

    rh  = 100 * vpd / vpt

    return rh

def humidity_eq_c(T,TD):
    """ humidity from temp. and dewpoint with different equation
        http://www.theweatherprediction.com/habyhints/186/
    """

    T  = float(T)
    TD = float(TD)

    # Td cannot be higher then T
    if ( TD > T ):
        TD = T

    L = 2.453 * 10**6
    R = 461.401

    # 
    et  = L/R*(1/273 - 1/c2kelvin(T)) -ln(6.11)
    etd = L/R*(1/273 - 1/c2kelvin(TD)) -ln(6.11)

    vpt = exp(et)
    vpd = exp(etd)

    rh  = 100 * vpd / vpt

    return rh


def SSI_f(tair,rhum):
    """ Summer Simmer Index (fahrenheit)
        http://myscope.net/hitzeindex-gefuehle-temperatur/
    """
    tair = float(tair)
    rhum = rh_limit(float(rhum))

    ssi = 1.98 * (tair - (0.55 - 0.0055 * rhum) * (tair - 58)) - 56.83

    return ssi


#----------------------------------------------------------------------

def calc_humidex_txt(TAIR,RHUM,CELSIUS=True):
    """ shows a descriptiv text describing the Humidex
        http://www.csgnetwork.com/canhumidexcalc.html
        http://www.climate-service-center.de/049116/index_0049116.html.de
    """


    if CELSIUS:
	humidex_c = humidex(TAIR,RHUM)
    else:
	humidex_c = humidex(f_to_c(TAIR),RHUM)


    if ( humidex_c <  29):
        # Stufe 1
	comment_en = "Little or no discomfort."
        comment_de = "Keine Beschwerden"
    if ((humidex_c >= 29) and (humidex_c < 34)):
        # Stufe 2
	comment_en = "Noticeable discomfort"
	comment_de = "Leichtes Unbehagen";
    if ((humidex_c >= 34) and (humidex_c < 39)):
        # Stufe 3
	comment_en = "Evident discomfort"
        comment_de = "Vorsicht: Starkes Unbehagen";
    if ((humidex_c >= 39) and (humidex_c < 45)):
        # Stufe 4
	comment_en = "Intense discomfort; avoid exertion"
        comment_de = "Erhoehte Vorsicht: Starkes Unwohlsein";
    if ((humidex_c >= 45) and (humidex_c < 54)):
        # Stufe 5
	comment_en = "Dangerous discomfort"
	comment_de = "Erhoehte Gefahr";
    if ( humidex_c >= 54):
        # Stufe 6
	comment_en = "Heat stroke probable"
        comment_de = "Sehr ernste Gefahr: Hitzeschlag und Sonnestich sind wahrscheinlich";

    if LANG_DE:
        comment = comment_de
    else:
        comment = comment_en

    if DEBUG:
        print "humidex: %.1f = %s" % (humidex_c,comment)

    return comment


def calc_heatindex_txt(TAIR,RHUM,CELSIUS=True):
    """ shows a descriptiv text describing the Heatindex
        https://en.wikipedia.org/wiki/Heat_index
    """

    if CELSIUS:
	heat_idx_c = heat_c(TAIR,RHUM)
    else:
	heat_idx_c = f_to_c(heat_c(TAIR,RHUM))

    if ( heat_idx_c <  27):
        # Stufe 1
	comment_en = "Little or no discomfort."
        comment_de = "Keine Beschwerden"

    if ((heat_idx_c >= 27) and (heat_idx_c < 32)):
	# Stufe 2
        comment_en = "Caution: Continuing activity could result in heat cramps."
        comment_de = u"Vorsicht: Bei längeren Zeiträumen und körperlicher Aktivität kann es zu Erschöpfungserscheinungen kommen."
    if ((heat_idx_c >= 32) and (heat_idx_c < 41)):
	# Stufe 3
        comment_en = "Extreme caution: Continuing activity could result in heat stroke."
	comment_de = u"Erhöhte Vorsicht: Es besteht die Möglichkeit von Hitzeschäden wie Sonnenstich, Hitzekrampf und Hitzekollaps."
    if ((heat_idx_c >= 41) and (heat_idx_c < 54)):
	# Stufe 4
        comment_en = "Danger: heat stroke is probable with continued activity"
        comment_de = u"Gefahr: Sonnenstich, Hitzekrampf und Hitzekollaps sind wahrscheinlich; Hitzschlag ist möglich."
    if ( heat_idx_c >= 54):
	# Stufe 5
        comment_en = "Extreme danger: Heat stroke is imminent."
        comment_de = u"Erhöhte Gefahr: Hitzschlag und Sonnenstich sind wahrscheinlich."

    if LANG_DE:
        comment = comment_de
    else:
        comment = comment_en

    if DEBUG:
        print "heatidex: %.1f = %s" % (heat_idx_c,comment)

    return comment


def calc_SSI_txt(TAIR,RHUM,CELSIUS=True):
    """ shows a descriptiv text describing the SSI
	http://myscope.net/hitzeindex-gefuehle-temperatur/
    """

    if CELSIUS:
	ssi = f_to_c(SSI_f(c_to_f(TAIR),RHUM))
    else:
	ssi = SSI_f(TAIR,RHUM)


    if ( ssi <  21.3):
        # Stufe 0
	comment_en = "Cool"
        comment_de = u"Kühl"

    if ((ssi >= 21.3) and (ssi < 25)):
	# Stufe 1
        comment_en = "Slightly cool: Majority feels convenient."
        comment_de = u"Etwas kühl. Die meisten Personen fühlen sich wohl."
    if ((ssi >= 25) and (ssi < 28.3)):
	# Stufe 2
	comment_en = "Convenient: Almost anyone feels convenient."
	comment_de = u"Optimal. Fast jeder fühlt sich wohl."
    if ((ssi >= 28.3) and (ssi < 32.8)):
	# Stufe 3
        comment_en = "Slightly hot: Majority feels convenient."
        comment_de = u"Etwas heiß. Die meisten Personen fühlen sich wohl."
    if ((ssi >= 32.8) and (ssi < 37.8)):
	# Stufe 4
	comment_en = "Hot: Potential increased discomfort."
        comment_de = u"Heiß. Teilweises Unwohlsein."
    if ((ssi >= 37.8) and (ssi < 44.4)):
	# Stufe 5
	comment_en = "Medium hot: Significant discomfort. Danger of sunstroke."
        comment_de = u"Medium hot. Unwohlsein. Gefahr von Hitzeschlag."
    if ((ssi >= 44.4) and (ssi < 51.7)):
	# Stufe 6
	comment_en = "Very hot: Severe discomfort. Danger of heat stroke."
        comment_de = u"Sehr heiß. Gefahr von Hitzeschlag."
    if ((ssi >= 51.7) and (ssi < 65.6)):
	# Stufe 7
	comment_en = "Extreme hot: Maximum discomfort. Increased danger of heat stroke."
        comment_de = u"Extrem Heiß. Sehr große Gefahr eines Hitzeschlages."
    if ( ssi >= 65.6):
	# Stufe 8
	comment_en = "Extreme hot: Maximum discomfort. Increased danger of heat stroke."
        comment_de = u"Extrem Heiß. Sehr große Gefahr eines Hitzeschlages."

    if LANG_DE:
        comment = comment_de
    else:
        comment = comment_en

    if DEBUG:
        print "SSI     : %.1f = %s" % (ssi,comment)

    return comment


def calc_THW(TAIR,RHUM,WIND,CELSIUS=True):
    # need to convert temp. if in F
    thw = 0
    if CELSIUS:
	thw = f_to_c(THW_f(c_to_f(TAIR),RHUM,WIND))
    else:
	thw = THW_f(TAIR,RHUM,WIND)

    if DEBUG:
        print "THW    : %.1f" % thw

    return thw


def calc_humidex(TAIR,RHUM,CELSIUS=True):
    # need to convert temp. if in F
    hu = 0
    if CELSIUS:
	hu = humidex(TAIR,RHUM)
    else:
	hu = c_to_f(humidex(f_to_c(TAIR),RHUM))

    if DEBUG:
        print "humidex: %.1f" % hu

    return hu


def calc_dewpoint(TAIR,RHUM,CELSIUS=True):
    dp = 0
    if CELSIUS:
	dp = dewpoint_c(TAIR,RHUM)
    else:
	dp = c_to_f(dewpoint_c(f_to_c(TAIR),RHUM))

    if DEBUG:
        print "dewpoint: %.1f" % dp

    return dp


def calc_windchill(TAIR,WIND,CELSIUS=True):
    wct = 0
    if CELSIUS:
	wct = windchill_c(TAIR,WIND)
    else:
	wct = windchill_f(TAIR,WIND)

    if DEBUG:
        print "windchill: %.1f" % wct

    return wct


def calc_humidity(TAIR,TDEWP,CELSIUS):
    r = 0
    if CELSIUS:
	r = humidity_c(TAIR,TDEWP)
    else:
	r = c_to_f(humidity_c(f_to_c(TAIR),f_to_c(TDEWP)))

    if DEBUG:
        print "humidity: %.1f" % r

    return r


def calc_heatindex(TAIR,RHUM,CELSIUS=True):
    """ calculate heatindex \
        https://en.wikipedia.org/wiki/Heat_index
        http://www.iweathernet.com/educational/heat-index-calculator-and-conversion-table
    """
    hi = 0
    if CELSIUS:
	hi = heat_c(TAIR,RHUM)
    else:
	hi = heat_f(TAIR,RHUM)

    if DEBUG:
        print "heatidx: %.1f" % hi

    return hi


def calc_SSI(TAIR,RHUM,CELSIUS=True):
    """ Summer Simmer Index (fahrenheit)
        http://myscope.net/hitzeindex-gefuehle-temperatur/
    """
    ssi = 0
    if CELSIUS:
	ssi = f_to_c(SSI_f(c_to_f(TAIR),RHUM))
    else:
	ssi = SSI_f(TAIR,RHUM)

    if DEBUG:
        print "SSI    : %.1f" % ssi

    return ssi

#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
def main():
    """ main program.  Evaluate commandline and ini-File
    """

    # just flags for commandline evaluation
    has_set_r = 0
    has_set_t = 0
    has_set_m = 0
    has_set_d = 0
    has_set_w = 0
    has_set_u = 0

    global CTYP
    global TAIR
    global RHUM
    global DEWP
    global WSPEED
    global TUNIT
    global CELSIUS

    # default values
    TAIR = 0
    RHUM = 0
    DEWP = 0
    WSPEED = 0
    TUNIT = "c"


    if sys.version_info < (2, 4):
        print "Sorry, your version of Python is too old (" + str(sys.version[0:5]) + \
                "). Please upgrade to Python 2.4 or higher."
        sys.exit(11)


    # check for options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:t:m:d:w:u:", ["help", "result=", "temp=", "rhum=", "dewpoint=", "wind=", "unit="])
        if (len(opts) < 1):
            # empty commandline
            usage()
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-r", "--result"):
            CTYP = a
            has_set_r = 1
        elif o in ("-t", "--temp"):
            TAIR = a
            has_set_t = 1
        elif o in ("-m", "--rhum"):
            RHUM = a
            has_set_m = 1
        elif o in ("-d", "--dewpoint"):
            DEWP = a
            has_set_d = 1
        elif o in ("-w", "--wind"):
            WSPEED = a
            has_set_w = 1
        elif o in ("-u", "--unit"):
            TUNIT = a
            has_set_u = 1
        else:
            assert False, "unhandled option"


    # check for temperatur unit
    if has_set_u:
        if ( TUNIT.lower() == "f" ):
            CELSIUS = False
        elif ( TUNIT.lower() == "c" ):
            CELSIUS = True
        else:
            print "ERROR: invalid parameter '%s' for '-u'" % CTYP
            usage()

    # check for temperature (mandatory)
    if not has_set_t:
        print "ERROR: mandatory parameter '-t' is missing"
        usage(12)

    # check for type of calculation (mandatory)
    if has_set_r:
        if ( CTYP.lower() == "heatindex" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_heatindex(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "hi_txt" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%s" % calc_heatindex_txt(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "humidex" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_humidex(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "hu_txt" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%s" % calc_humidex_txt(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "ssi" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_SSI(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "ssi_txt" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%s" % calc_SSI_txt(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "thw" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            elif not has_set_w:
                print "ERROR: mandatory parameter '-w' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_THW(TAIR,RHUM,WSPEED,CELSIUS)

        elif ( CTYP.lower() == "thsw" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            elif not has_set_w:
                print "ERROR: mandatory parameter '-w' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "currently not implemented"
                # print "%.1f" % calc_THSW(TAIR,RHUM,WSPEED,CELSIUS)

        elif ( CTYP.lower() == "windchill" ):
            if not has_set_w:
                print "ERROR: mandatory parameter '-w' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_windchill(TAIR,WSPEED,CELSIUS)

        elif ( CTYP.lower() == "dewpoint" ):
            if not has_set_m:
                print "ERROR: mandatory parameter '-m' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_dewpoint(TAIR,RHUM,CELSIUS)

        elif ( CTYP.lower() == "humidity" ):
            if not has_set_d:
                print "ERROR: mandatory parameter '-d' is missing for type '%s'" % CTYP
                usage(12)
            else:
                print "%.1f" % calc_humidity(TAIR,DEWP,CELSIUS)

        else:
            print "ERROR: invalid parameter '%s' for '-r'" % CTYP
            usage()

    else:
        print "ERROR: mandatory parameter '-r' is missing"
        usage(12)



#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
#
if __name__ == "__main__":
    main()

#
# END
#
