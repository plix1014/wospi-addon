#!/usr/bin/env python3
#
# triggers mqtt publish after four updates to the wxdata.xml
#
# Created:     18.08.2018
# Copyright:   (c) Peter Lidauer 2018
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 24.10.2023: use enviroment variables for basic setings
#  PLI, 18.07.2025: changes for python3
#

import time
import sys, os
from xml.etree import ElementTree as ET
import paho.mqtt.client as mqtt
import json
import pyinotify

# Define Variables
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_QOS   = 1

# read environment
WXIN                  = os.environ.get('WXIN', '/var/tmp/wxdata.xml')
#
MQTT_HOST             = os.environ.get('MQTT_HOST', '192.168.20.74')
MQTT_PORT             = os.environ.get('MQTT_PORT', '1883')
MQTT_TOPIC_BASE       = os.environ.get('MQTT_TOPIC_BASE', 'athome/eg/wospi')

# define subjects
MQTT_TOPIC_OTEMP      = MQTT_TOPIC_BASE + "/outtemp"
MQTT_TOPIC_ITEMP      = MQTT_TOPIC_BASE + "/intemp"
MQTT_TOPIC_PRESSURE   = MQTT_TOPIC_BASE + "/pressure"
MQTT_TOPIC_RAINFALL24 = MQTT_TOPIC_BASE + "/rainfall24h"
MQTT_TOPIC_DAYRAIN    = MQTT_TOPIC_BASE + "/dayrain"
MQTT_TOPIC_UVINDEX    = MQTT_TOPIC_BASE + "/uvindex"
MQTT_TOPIC_ALL        = MQTT_TOPIC_BASE + "/wxdata"

# init variables
#MQTT_MSG_OTEMP      = {"outtemp_c"     : None}
#MQTT_MSG_ITEMP      = {"intemp_c"      : None}
#MQTT_MSG_PRESSURE   = {"barometer_hpa" : None}
#MQTT_MSG_RAINFALL24 = {"rainfall24h_mm": None}
#MQTT_MSG_DAYRAIN    = {"dayrain_mm"    : None}
#MQTT_MSG_UVINDEX    = {"uvindex"       : None}
#MQTT_MSG_ALL          = ''

MQTT_MSG_OTEMP = None
MQTT_MSG_ITEMP = None
MQTT_MSG_PRESSURE = None
MQTT_MSG_RAINFALL24 = None
MQTT_MSG_DAYRAIN = None
MQTT_MSG_UVINDEX = None
MQTT_MSG_ALL = None


# empty
WXDATA = {}

INFO  = True
WARN  = True
ERROR = True
DEBUG = False

Connected = False

#---------------------------------------------------------------------
def print_dbg(level,msg):
    now = time.strftime('%a %b %e %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now,msg))
    return

def parseXML(file):
    """ <?xml version="1.0"?>
        <wxdata>
            <timestamp>03.06.2018 09:07:03</timestamp>
            <outtemp_c>20.8</outtemp_c>
            <intemp_c>23.3</intemp_c>
            <rainfall24h_mm>0.0</rainfall24h_mm>
            <dayrain_mm>0.0</dayrain_mm>
            <uvindex>1.4</uvindex>
        </wxdata>
    """
    wxdata={}

    if os.path.exists(file):
        # xml.etree.ElementTree.ParseError: not well-formed (invalid token): line 61, column 45

        # additional wait. Sometimes, the pyinotify leads to above error
        time.sleep(2)
        try:
            # try to parse
            tree = ET.parse(file)
            root = tree.getroot()
            for child in root:
                wxdata[child.tag] = child.text

            print_dbg(DEBUG, "xml new outtemp_c: %s" % wxdata['outtemp_c'])

        except Exception as e:
            print(f"An error occurred during parsing of {file}: {e}")


    return wxdata


#---------------------------------------------------------------------
# Define on_publish event function
def on_publish(client, userdata, mid):
    print_dbg(INFO, "Message Published...")

def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC_OTEMP)
    client.subscribe(MQTT_TOPIC_ITEMP)
    client.subscribe(MQTT_TOPIC_PRESSURE)
    client.subscribe(MQTT_TOPIC_RAINFALL24)
    client.subscribe(MQTT_TOPIC_DAYRAIN)
    client.subscribe(MQTT_TOPIC_UVINDEX)
    client.subscribe(MQTT_TOPIC_ALL)

    # Only publish if messages exist (file was read successfully)
    if MQTT_MSG_OTEMP is not None:
        client.publish(MQTT_TOPIC_OTEMP, MQTT_MSG_OTEMP, MQTT_QOS)
    if MQTT_MSG_ITEMP is not None:
        client.publish(MQTT_TOPIC_ITEMP, MQTT_MSG_ITEMP, MQTT_QOS)
    if MQTT_MSG_PRESSURE is not None:
        client.publish(MQTT_TOPIC_PRESSURE, MQTT_MSG_PRESSURE, MQTT_QOS)
    if MQTT_MSG_RAINFALL24 is not None:
        client.publish(MQTT_TOPIC_RAINFALL24, MQTT_MSG_RAINFALL24, MQTT_QOS)
    if MQTT_MSG_DAYRAIN is not None:
        client.publish(MQTT_TOPIC_DAYRAIN, MQTT_MSG_DAYRAIN, MQTT_QOS)
    if MQTT_MSG_UVINDEX is not None:
        client.publish(MQTT_TOPIC_UVINDEX, MQTT_MSG_UVINDEX, MQTT_QOS)

    global Connected
    Connected = True



def on_message(client, userdata, msg):
    print_dbg(DEBUG, "received topic  : %s" % msg.topic)
    print_dbg(DEBUG, "received payload: %s" % msg.payload)

    try:
        # Decode bytes to str first
        payload_str = msg.payload.decode('utf-8')
        payload = json.loads(payload_str)

        if isinstance(payload, dict):
            for key in payload.keys():
                print_dbg(INFO, "received %s: %s" % (key, payload[key]))
        else:
            print_dbg(WARN, f"Payload is not a dict: {payload} (type: {type(payload).__name__})")

    except json.JSONDecodeError as e:
        print_dbg(ERROR, f"JSON decode error: {e}")
    except Exception as e:
        print_dbg(ERROR, f"Unexpected error: {e}")

    time.sleep(0.1)
    # client.disconnect()



def on_disconnect(client, userdata,rc=0):
    print_dbg(DEBUG,"DisConnected result code "+str(rc))
    client.loop_stop()


def reread_xml():
    global MQTT_MSG_OTEMP
    global MQTT_MSG_ITEMP
    global MQTT_MSG_PRESSURE
    global MQTT_MSG_RAINFALL24
    global MQTT_MSG_DAYRAIN
    global MQTT_MSG_UVINDEX
    global MQTT_MSG_ALL
    global WXDATA

    WXDATA = parseXML(WXIN) or {}

    if WXDATA:  # Only update messages if we got valid data
        MQTT_MSG_OTEMP = json.dumps({"outtemp_c": WXDATA.get('outtemp_c')})
        MQTT_MSG_ITEMP = json.dumps({"intemp_c": WXDATA.get('intemp_c')})
        MQTT_MSG_PRESSURE = json.dumps({"barometer_hpa": WXDATA.get('barometer_hpa')})
        MQTT_MSG_RAINFALL24 = json.dumps({"rainfall24h_mm": WXDATA.get('rainfall24h_mm')})
        MQTT_MSG_DAYRAIN = json.dumps({"dayrain_mm": WXDATA.get('dayrain_mm')})
        MQTT_MSG_UVINDEX = json.dumps({"uvindex": WXDATA.get('uvindex')})
        MQTT_MSG_ALL = json.dumps(WXDATA)
    else:
        # Clear all messages if file doesn't exist or is invalid
        MQTT_MSG_OTEMP = None
        MQTT_MSG_ITEMP = None
        MQTT_MSG_PRESSURE = None
        MQTT_MSG_RAINFALL24 = None
        MQTT_MSG_DAYRAIN = None
        MQTT_MSG_UVINDEX = None
        MQTT_MSG_ALL = None


def initialize():
    reread_xml()
    global mqttc

    # Initiate MQTT Client
    mqttc = mqtt.Client()

    # Register publish callback function
    #mqttc.on_publish = on_publish
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect

    # Connect with MQTT Broker
    print_dbg(INFO, "trying to connect to %s:%s" % (MQTT_HOST,MQTT_PORT))
    mqttc.connect(MQTT_HOST, int(MQTT_PORT), int(MQTT_KEEPALIVE_INTERVAL))

    return mqttc



class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, wm, path, mask, rec=False, mqtt=None):
        self.wm = wm
        self.path = path
        self.mask = mask
        self.rec = rec
        self.mqtt = mqtt
        self.delayCounter = 0
        self.messages = {}
        self.watches = smart_add_watch(wm, path, mask, rec)
        super().__init__()


    def process_IN_CREATE(self, event):
        """Handle new file creation in watched directory"""
        if event.pathname == self.path:
            print_dbg(INFO, f"File appeared: {self.path}")
            try:
                # Add the file watch
                self.watches['file'] = self.wm.add_watch(self.path, self.mask, rec=self.rec)
                print_dbg(INFO, f"Added file watch: {self.path}")
            except Exception as e:
                print_dbg(ERROR, f"Error adding file watch: {e}")


    def _is_valid_payload(self, payload):
        """
        Check if payload contains valid data
        Handles both string numbers ("19.0") and actual numbers
        """
        try:
            # If payload is a JSON string, parse it first
            if isinstance(payload, str):
                payload = json.loads(payload)

            if not isinstance(payload, dict):
                return False

            for value in payload.values():
                if value is None:
                    continue

                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped:  # Non-empty string
                        return True

                elif isinstance(value, (int, float)):
                    return True

            return False
        except json.JSONDecodeError:
            return False

    def process_IN_CLOSE_WRITE(self, event):
        time.sleep(0.1)
        self.delayCounter += 1
        reread_xml()

        # Create fresh message dictionaries with current values
        self.messages = {
            MQTT_TOPIC_OTEMP: {"outtemp_c": WXDATA.get('outtemp_c')},
            MQTT_TOPIC_ITEMP: {"intemp_c": WXDATA.get('intemp_c')},
            MQTT_TOPIC_PRESSURE: {"barometer_hpa": WXDATA.get('barometer_hpa')},
            MQTT_TOPIC_RAINFALL24: {"rainfall24h_mm": WXDATA.get('rainfall24h_mm')},
            MQTT_TOPIC_DAYRAIN: {"dayrain_mm": WXDATA.get('dayrain_mm')},
            MQTT_TOPIC_UVINDEX: {"uvindex": WXDATA.get('uvindex')}
        }

        print_dbg(INFO, "New wxdata written: %s (%d)" % (event.pathname, self.delayCounter))

        if self.delayCounter >= 2:
            print_dbg(INFO, "#-- publish start ----------------------------")

            for topic, payload in self.messages.items():
                print_dbg(DEBUG, f"Checking {topic}: {payload}")
                if self._is_valid_payload(payload):
                    self.mqtt.publish(topic, json.dumps(payload), MQTT_QOS)
                    print_dbg(INFO, f"Published to {topic}: {payload}")
                else:
                    print_dbg(DEBUG, f"Skipping {topic} - no valid data: {payload}")

            print_dbg(INFO, "#-- publish end ------------------------------")
            self.delayCounter = 0



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
            print_dbg(WARN, f"Parent directory does not exist: {dir_path}")
            return watches
    except Exception as e:
        print_dbg(ERROR, f"Error watching directory: {e}")
        return watches

    # Then try to watch the file if it exists
    try:
        if os.path.exists(path):
            watches['file'] = wm.add_watch(path, mask, rec=rec)
            print_dbg(DEBUG, f"Watching file: {path}")
    except Exception as e:
        print_dbg(ERROR, f"Error watching file: {e}")

    return watches



#---------------------------------------------------------------------

def main():

    print_dbg(DEBUG, "MQTT_HOST      : %s" % (MQTT_HOST))
    print_dbg(DEBUG, "MQTT_PORT      : %s" % (MQTT_PORT))
    print_dbg(DEBUG, "MQTT_TOPIC_BASE: %s" % (MQTT_TOPIC_BASE))
    print_dbg(DEBUG, "WXDATA         : %s" % (WXIN))

    mqttc    = initialize()

    wm       = pyinotify.WatchManager()   # Watch Manager
    mask     = pyinotify.IN_CLOSE_WRITE   # watched events
    handler  = EventHandler(wm=wm, path=WXIN, mask=pyinotify.IN_CLOSE_WRITE, rec=True, mqtt=mqttc)
    notifier = pyinotify.Notifier(wm, handler)
    wdd      = smart_add_watch(wm, WXIN, mask, rec=True)

    mqttc.loop_start()

    while Connected != True:
        time.sleep(0.5)

    try:
        notifier.loop()

    except KeyboardInterrupt:
        mqttc.disconnect()
        mqttc.loop_stop()


#---------------------------------------------------------------------
if __name__ == "__main__":
    main()

