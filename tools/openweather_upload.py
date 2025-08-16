#!/usr/bin/env python3
#
# Uploads weather data to OpenWeatherMap
#
# Created:     15.08.2025
# Copyright:   (c) Peter Lidauer 2025
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
#

import sys,os

CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME)

import time
import xml.etree.ElementTree as ET
from datetime import datetime
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from wxtools import print_dbg
import config


# Konfiguration
API_KEY = config.OWM_API_KEY
STATION_ID = config.OWM_STATION_ID

# read environment
WXIN                  = os.environ.get('WXIN', '/var/tmp/wxdata.xml')

INFO  = True
WARN  = True
ERROR = True
DEBUG = True

#--------------------------------------------------------------------------------

def parse_xml(xml_file):
    """Extracts weather data from XML file."""

    tree = ET.parse(xml_file)
    root = tree.getroot()

    print_dbg(INFO, f"getting data from {xml_file}.")
    data = {
        "timestamp"  : int(time.mktime(datetime.strptime(root.find("timestamp").text, "%d.%m.%Y %H:%M:%S").timetuple())),
        "temperature": float(root.find("outtemp_c").text),      # Direct float (no nested object)
        "humidity"   : int(root.find("outhum_p").text),         # Direct int
        "dew_point"  : float(root.find("dewpoint_c").text),     # Direct float
        "pressure"   : float(root.find("barometer_hpa").text),  # Direct float
        "wind_speed" : float(root.find("wind_msec").text),      # Direct float
        "wind_deg"   : int(root.find("winddir").text),          # Direct int
        "wind_gust"  : float(root.find("gust10_msec").text),    # Direct float
        "rain_1h"    : float(root.find("rainfall60_mm").text),  # Direct float
        "rain_24h"   : float(root.find("rainfall24h_mm").text), # Direct float
    }

    return data


def upload_to_openweathermap(data):
    """Uploads weather data to OpenWeatherMap using urllib."""
    url = f"https://api.openweathermap.org/data/3.0/measurements?appid={API_KEY}"


    payload = [{
        "station_id" : STATION_ID,
        "dt"         : data["timestamp"],
        "temperature": data["temperature"],  # Direct value
        "humidity"   : data["humidity"],     # Direct value
        "dew_point"  : data["dew_point"],    # Direct value
        "pressure"   : data["pressure"],     # Direct value
        "wind_speed" : data["wind_speed"],   # Direct value
        "wind_deg"   : data["wind_deg"],     # Direct value
        "wind_gust"  : data["wind_gust"],    # Direct value
        "rain": {"1h": data["rain_1h"],
                "24h": data["rain_24h"]
                 },    # Only "rain" is an object (API requirement)
    }]

    # Convert payload to JSON bytes
    print_dbg(DEBUG, json.dumps(payload, indent=2))
    data_bytes = json.dumps(payload).encode("utf-8")

    # Create request
    req = Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(req) as response:
            print_dbg(INFO, "Data uploaded successfully!")
            print_dbg(DEBUG, response.read().decode("utf-8"))
    except HTTPError as e:
        print_dbg(ERROR, f"HTTP Error: {e.code} - {e.reason}")
        print_dbg(ERROR, e.read().decode("utf-8"))  # Print server response
    except URLError as e:
        print_dbg(ERROR, f"URL Error: {e.reason}")

#---------------------------------------------------------------------

def main():

    if STATION_ID == '' or API_KEY == '':
        print('OpenWeatherMap API_KEY/ID not set. No upload possible.')
        return


    if os.path.exists(WXIN):
        print_dbg(DEBUG, f"Watching file: {WXIN}")

        # XML-Daten parsen
        weather_data = parse_xml(WXIN)

        # Zu OpenWeatherMap hochladen
        upload_to_openweathermap(weather_data)
    else:
        print_dbg(ERROR, f"xml input file {WXIN} does not exist.")


#---------------------------------------------------------------------
if __name__ == "__main__":
    main()

