#!/usr/bin/python
#
# triggers mqtt publish after four updates to the wxdata.xml
#
# Created:     18.08.2018
# Copyright:   (c) Peter Lidauer 2018
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 24.10.2023: use enviroment variables for basic setings
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
MQTT_HOST             = os.environ.get('MQTT_HOST', '192.168.20.70')
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
MQTT_MSG_OTEMP        = 0
MQTT_MSG_ITEMP        = 0
MQTT_MSG_PRESSURE     = 0
MQTT_MSG_RAINFALL24   = 0
MQTT_MSG_DAYRAIN      = 0
MQTT_MSG_UVINDEX      = 0
MQTT_MSG_ALL          = ''


# empty
WXDATA = {}

INFO  = True
DEBUG = False

Connected = False

#---------------------------------------------------------------------
def print_dbg(level,msg):
    now = time.strftime('%a %b %d %H:%M:%S %Y LT:')
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
        tree = ET.parse(file)
        root = tree.getroot()
        for child in root:
            wxdata[child.tag] = child.text

        print_dbg(DEBUG, "xml new outtemp_c: %s" % wxdata['outtemp_c'])

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

    client.publish(MQTT_TOPIC_OTEMP,      MQTT_MSG_OTEMP,      MQTT_QOS)
    client.publish(MQTT_TOPIC_ITEMP,      MQTT_MSG_ITEMP,      MQTT_QOS)
    client.publish(MQTT_TOPIC_PRESSURE,   MQTT_MSG_PRESSURE,   MQTT_QOS)
    client.publish(MQTT_TOPIC_RAINFALL24, MQTT_MSG_RAINFALL24, MQTT_QOS)
    client.publish(MQTT_TOPIC_DAYRAIN,    MQTT_MSG_DAYRAIN,    MQTT_QOS)
    client.publish(MQTT_TOPIC_UVINDEX,    MQTT_MSG_UVINDEX,    MQTT_QOS)

    global Connected
    Connected = True


def on_message(client, userdata, msg):
    print_dbg(DEBUG,"received topic  : %s" % msg.topic)
    print_dbg(DEBUG,"received payload: %s" % msg.payload) # <- do you mean this payload = {...} ?

    payload = json.loads(msg.payload) # you can use json.loads to convert string to json

    for key in payload.keys():
        print_dbg(INFO, "received %s: %s" % (key,payload[key]))


    time.sleep(0.1)
    #client.disconnect() # Got message then disconnect


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

    WXDATA = parseXML(WXIN)

    if WXDATA:
        MQTT_MSG_OTEMP      = json.dumps({"outtemp_c"     : WXDATA['outtemp_c']});
        MQTT_MSG_ITEMP      = json.dumps({"intemp_c"      : WXDATA['intemp_c']});
        MQTT_MSG_PRESSURE   = json.dumps({"barometer_hpa" : WXDATA['barometer_hpa']});
        MQTT_MSG_RAINFALL24 = json.dumps({"rainfall24h_mm": WXDATA['rainfall24h_mm']});
        MQTT_MSG_DAYRAIN    = json.dumps({"dayrain_mm"    : WXDATA['dayrain_mm']});
        MQTT_MSG_UVINDEX    = json.dumps({"uvindex"       : WXDATA['uvindex']});
        MQTT_MSG_ALL        = json.dumps(WXDATA);


def initialize():
    reread_xml()
    global mqttc

    # Initiate MQTT Client
    mqttc = mqtt.Client()

    # Register publish callback function
    mqttc.on_publish = on_publish
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect

    # Connect with MQTT Broker
    mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

    return mqttc


class EventHandler(pyinotify.ProcessEvent):
    def my_init(self, mqtt):
        self.mqtt = mqtt
        self.delayCounter = 0

    def process_IN_CLOSE_WRITE(self, event):
        time.sleep(0.1)
        self.delayCounter += 1
        reread_xml()
        print_dbg(INFO, "New wxdata written: %s (%d)" % (event.pathname,self.delayCounter))
        if self.delayCounter >= 2:
            print_dbg(DEBUG, "#-- publish start ----------------------------")
            self.mqtt.publish(MQTT_TOPIC_OTEMP,      MQTT_MSG_OTEMP,      MQTT_QOS)
            self.mqtt.publish(MQTT_TOPIC_ITEMP,      MQTT_MSG_ITEMP,      MQTT_QOS)
            self.mqtt.publish(MQTT_TOPIC_PRESSURE,   MQTT_MSG_PRESSURE,   MQTT_QOS)
            self.mqtt.publish(MQTT_TOPIC_RAINFALL24, MQTT_MSG_RAINFALL24, MQTT_QOS)
            self.mqtt.publish(MQTT_TOPIC_DAYRAIN,    MQTT_MSG_DAYRAIN,    MQTT_QOS)
            self.mqtt.publish(MQTT_TOPIC_UVINDEX,    MQTT_MSG_UVINDEX,    MQTT_QOS)
            #self.mqtt.publish(MQTT_TOPIC_ALL,        MQTT_MSG_ALL,        MQTT_QOS)
            print_dbg(INFO, "#-- publish end ------------------------------")
            self.delayCounter = 0

#---------------------------------------------------------------------

def main():

    mqttc    = initialize()

    wm       = pyinotify.WatchManager()   # Watch Manager
    mask     = pyinotify.IN_CLOSE_WRITE   # watched events
    handler  = EventHandler(mqtt=mqttc)
    notifier = pyinotify.Notifier(wm, handler)
    wdd      = wm.add_watch(WXIN, mask, rec=True)

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

