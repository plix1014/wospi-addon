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
#  PLI, 18.11.2025: Fixed file watching logic - simpler approach like old version
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

INFO  = True
DEBUG = False
Connected = False

#---------------------------------------------------------------------
def print_dbg(level, msg):
    now = time.strftime('%a %b %e %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now, msg))
    return


def parse_xml(path):
    """Read wxdata.xml and return all tags as a dict."""
    if not os.path.exists(path):
        print_dbg(INFO, f"WARN File does not exist: {path}")
        return {}

    time.sleep(0.2)  # avoid file-write race condition

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return {c.tag: c.text for c in root}

    except Exception as e:
        print_dbg(INFO, f"XML parse error for {path}: {e}")
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
    print_dbg(DEBUG, "Published updated weather data to MQTT")


def on_connect(client, userdata, flags, rc):
    global Connected
    Connected = True
    print_dbg(INFO, f"Connected to MQTT with result code {rc}")


def on_disconnect(client, userdata, rc):
    global Connected
    Connected = False
    print_dbg(INFO, f"Disconnected from MQTT with result code {rc}")


def smart_add_watch(wm, path, mask, rec=False):
    """
    Continuously tries to add watch for file, falls back to directory watching.
    Returns both file and directory watches (if any).
    """
    watches = {}
    dir_path = os.path.dirname(path)

    # First try to watch the directory (should always exist)
    try:
        if os.path.exists(dir_path):
            watches['dir'] = wm.add_watch(dir_path, pyinotify.IN_CREATE)
            print_dbg(DEBUG, f"Watching directory: {dir_path}")
        else:
            print_dbg(INFO, f"Parent directory does not exist: {dir_path}")
            return watches
    except Exception as e:
        print_dbg(INFO, f"Error watching directory: {e}")
        return watches

    # Then try to watch the file if it exists
    try:
        if os.path.exists(path):
            watches['file'] = wm.add_watch(path, mask, rec=rec)
            print_dbg(INFO, f"Watching file: {path}")
    except Exception as e:
        print_dbg(INFO, f"Error watching file: {e}")

    return watches


class Handler(pyinotify.ProcessEvent):
    def __init__(self, wm, path, mask, client):
        self.wm = wm
        self.path = path
        self.mask = mask
        self.client = client
        self.delayCounter = 0
        self.watches = {}
        super().__init__()

    def process_IN_CREATE(self, event):
        """Handle new file creation in watched directory"""
        if event.pathname == self.path:
            print_dbg(INFO, f"File appeared: {self.path}")
            try:
                # Add the file watch if it doesn't exist
                if 'file' not in self.watches or not self.watches['file']:
                    self.watches['file'] = self.wm.add_watch(self.path, self.mask, rec=False)
                    print_dbg(INFO, f"Added file watch: {self.path}")
                    
                    # Publish initial data from the new file
                    wx = parse_xml(self.path)
                    if wx:
                        publish_categories(self.client, wx)
                        print_dbg(INFO, "Published initial data from newly created file")
            except Exception as e:
                print_dbg(INFO, f"Error adding file watch: {e}")

    def process_IN_CLOSE_WRITE(self, event):
        """Handle file write completion"""
        if event.pathname == self.path:
            self.delayCounter += 1
            print_dbg(INFO, f"File modified: {event.pathname} (count: {self.delayCounter})")
            
            # Only process every 2nd update (like the old version)
            if self.delayCounter >= 2:
                wx = parse_xml(self.path)
                if wx:
                    publish_categories(self.client, wx)
                    print_dbg(DEBUG, f"Published weather data (update #{self.delayCounter})")
                self.delayCounter = 0


def main():
    global Connected
    
    # Print startup info
    print_dbg(INFO, f"Starting wospi2mqtt3.py")
    print_dbg(INFO, f"MQTT Host: {MQTT_HOST}:{MQTT_PORT}")
    print_dbg(INFO, f"MQTT Base Topic: {MQTT_BASE}")
    print_dbg(INFO, f"Input file: {WXIN}")
    
    # Check if file exists at startup
    if os.path.exists(WXIN):
        print_dbg(INFO, "Input file exists at startup")
    else:
        print_dbg(INFO, "Input file does not exist at startup - waiting for it to be created")
    
    # Initialize MQTT client
    mqttc = mqtt.Client()
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect

    print_dbg(INFO, f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}")
    try:
        mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
        mqttc.loop_start()
    except Exception as e:
        print_dbg(INFO, f"Failed to connect to MQTT: {e}")
        return

    # Wait until connected
    wait_time = 0
    while not Connected and wait_time < 10:  # 10 second timeout
        time.sleep(0.5)
        wait_time += 0.5
    
    if not Connected:
        print_dbg(INFO, "Failed to connect to MQTT broker")
        return

    # Use pyinotify to watch wxdata.xml updates - SIMPLER APPROACH
    wm = pyinotify.WatchManager()
    
    # Watch for both file modifications and file creation
    mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CREATE
    
    # Create handler
    handler = Handler(wm=wm, path=WXIN, mask=pyinotify.IN_CLOSE_WRITE, client=mqttc)
    
    # Setup watches using smart_add_watch
    wdd = smart_add_watch(wm, WXIN, pyinotify.IN_CLOSE_WRITE, rec=False)
    handler.watches = wdd  # Store watches in handler
    
    # Create notifier
    notifier = pyinotify.Notifier(wm, handler)
    
    # If file exists at startup, publish initial data
    if os.path.exists(WXIN):
        wx = parse_xml(WXIN)
        if wx:
            publish_categories(mqttc, wx)
            print_dbg(INFO, "Published initial weather data")
    
    print_dbg(INFO, "Monitoring for changes...")
    
    try:
        # Use the standard notifier loop - this is the key change
        notifier.loop()
        
    except KeyboardInterrupt:
        print_dbg(INFO, "Shutting down by user request...")
    except Exception as e:
        print_dbg(INFO, f"Error in notifier loop: {e}")
    finally:
        print_dbg(INFO, "Cleaning up...")
        mqttc.disconnect()
        mqttc.loop_stop()


#---------------------------------------------------------------------
if __name__ == "__main__":
    main()
