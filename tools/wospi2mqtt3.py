#!/usr/bin/env python3
#
# triggers mqtt publish after four updates to the wxdata.xml
# New Version with Category JSON & HA-friendly keys
#
# Created:     18.08.2018
# Copyright:   (c) Peter Lidauer 2018
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 24.10.2023: use enviroment variables for basic setings
#  PLI, 18.07.2025: changes for python3
#  PLI, 16.11.2025: New Version with Category JSON
#

import time
import os
from xml.etree import ElementTree as ET
import paho.mqtt.client as mqtt
import json
import pyinotify

# Define Variables
MQTT_KEEPALIVE = 45
MQTT_QOS = 1

# read environment
WXIN      = os.environ.get('WXIN', '/var/tmp/wxdata.xml')
#
MQTT_HOST = os.environ.get('MQTT_HOST', '192.168.20.74')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
MQTT_BASE = os.environ.get('MQTT_TOPIC_BASE', 'athome/eg/wospi')

# Category topics
TOPIC_OUTDOOR  = f"{MQTT_BASE}/outdoor"
TOPIC_INDOOR   = f"{MQTT_BASE}/indoor"
TOPIC_RAIN     = f"{MQTT_BASE}/rain"
TOPIC_PRESSURE = f"{MQTT_BASE}/pressure"
TOPIC_SYSTEM   = f"{MQTT_BASE}/system"
TOPIC_ALL      = f"{MQTT_BASE}/wxdata"

DEBUG = False
Connected = False

#---------------------------------------------------------------------
def print_dbg(level,msg):
    now = time.strftime('%a %b %e %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now,msg))
    return


def parse_xml(path):
    """Read wxdata.xml and return all tags as a dict."""
    if not os.path.exists(path):
        return {}

    time.sleep(0.2)  # avoid file-write race condition

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return {c.tag: c.text for c in root}

    except Exception as e:
        print("XML parse error:", e)
        return {}


def build_category_payloads(wx):
    """Convert wxdata XML tags into categorized JSON objects with HA-friendly keys."""

    outdoor = {
        "temperature": wx.get("outtemp_c"),
        "humidity": wx.get("outhum_p"),
        "dew_point": wx.get("dewpoint_c"),
        "wind_speed": wx.get("wind_msec"),
        "wind_gust": wx.get("gust10_msec"),
        "wind_direction": wx.get("winddir"),
        "wind_cardinal": wx.get("wind_cardinal"),
        "wind_chill": wx.get("wc_c"),
        "heat_index": wx.get("hindex_c"),
        "feels_like": wx.get("thsw_c"),
        "solar_radiation": wx.get("solar_w"),
        "uv_index": wx.get("uvindex"),
    }

    indoor = {
        "temperature": wx.get("intemp_c"),
        "humidity": wx.get("inhum_p"),
    }

    rain = {
        "rain_rate": wx.get("rainrate_mmhr"),
        "rain_day": wx.get("dayrain_mm"),
        "rain_24h": wx.get("rainfall24h_mm"),
        "rain_month": wx.get("monthrain_mm"),
        "rain_year": wx.get("yearrain_mm"),
        "rain_storm": wx.get("stormrain_mm"),
    }

    pressure = {
        "pressure": wx.get("barometer_hpa"),
        "pressure_trend": wx.get("barotrend"),
        "pressure_trend_text": wx.get("barotrendtext"),
        "forecast_text": wx.get("fctext"),
        "forecast_icon": wx.get("fcicon"),
    }

    system = {
        "sunrise": wx.get("sunrise_lt"),
        "sunset": wx.get("sunset_lt"),
        "battery_status": wx.get("batterystatus"),
        "voltage": wx.get("voltage"),
        "timestamp": wx.get("timestamp"),
    }

    return outdoor, indoor, rain, pressure, system


def publish_categories(client, wx):
    """Publish all five category JSON documents + master JSON."""

    outdoor, indoor, rain, pressure, system = build_category_payloads(wx)

    client.publish(TOPIC_OUTDOOR,  json.dumps(outdoor),  MQTT_QOS)
    client.publish(TOPIC_INDOOR,   json.dumps(indoor),   MQTT_QOS)
    client.publish(TOPIC_RAIN,     json.dumps(rain),     MQTT_QOS)
    client.publish(TOPIC_PRESSURE, json.dumps(pressure), MQTT_QOS)
    client.publish(TOPIC_SYSTEM,   json.dumps(system),   MQTT_QOS)

    # Publish master JSON (raw XML tags + HA names)
    client.publish(TOPIC_ALL, json.dumps(wx), MQTT_QOS)


def on_connect(client, userdata, flags, rc):
    global Connected
    Connected = True
    print("Connected to MQTT.")


def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT.")


#---------------------------------------------------------------------

def main():
    mqttc = mqtt.Client()
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect

    print(f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}")
    mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    mqttc.loop_start()

    # Wait until connected
    while not Connected:
        time.sleep(0.1)

    # Use pyinotify to watch wxdata.xml updates
    wm = pyinotify.WatchManager()
    mask = pyinotify.IN_CLOSE_WRITE

    class Handler(pyinotify.ProcessEvent):
        def process_IN_CLOSE_WRITE(self, event):
            wx = parse_xml(WXIN)
            if wx:
                publish_categories(mqttc, wx)
                print("Published updated weather data.")

    handler = Handler()
    notifier = pyinotify.Notifier(wm, handler)
    wm.add_watch(WXIN, mask)

    print("Monitoring for changes…")
    try:
        notifier.loop()

    except KeyboardInterrupt:
        mqttc.disconnect()
        mqttc.loop_stop()


#---------------------------------------------------------------------
if __name__ == "__main__":
    main()

