#!/usr/bin/python3

from threading import Thread, Lock, Event

from helpers.config_parser import conf
from helpers.logger import logger
from helpers.modem_support.default import BaseModule

from cm import manage_connection, modem
from nm import manage_network
from monitor import monitor
from configurator import configure
from geolocation import update_geolocation

#from modules.imu import sensor
import modules.imu as imu
import modules.remote_gpio as rgpio
import paho.mqtt.client as mqtt
import time
import struct

try:# Use monotonic clock if available
    ## Beni, disabilitata per il momento: time_func = time.monotonic
    time_func = time.monotonic
except AttributeError:
    time_func = time.time

lock = Lock()
event = Event()
#modem = BaseModule() --> gia' dichiarata in cm.py

client = mqtt.Client()
latency  = 0.0
latency2 = 0.0

#---------------------------------------------MQTT
# Raspberry PI IP address
MQTT_BROKER = "172.30.55.106"
#OLD MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
#MQTT_BROKER = "192.168.100.100"
## oracle-03
#MQTT_BROKER = "130.162.34.184"

MQTT_PING = "rw/host/ping"
MQTT_PONG = "rw/host/pong"

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    msg = f"Connected to broker '{client._host}' with result code {str(rc)}"
    print(msg)
    logger.info(msg)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    if rc == 0:
        msg = f" Broker '{client._host}': subscribing to topics..."
        print(msg)
        logger.info(msg)
        #client.subscribe(MQTT_CMD)
        client.subscribe(MQTT_PING)
        client.subscribe(MQTT_PONG)
        rgpio.onConnect(client, userdata, flags, rc)

def on_connect_fail(client, userdata):
    msg = f"Connect fail to the broker '{client._host}'"
    print(msg)
    logger.warning(msg)

def on_disconnect(client, userdata, rc):
    msg = f"Disconnected from broker '{client._host}' with result code {str(rc)}"
    print(msg)
    logger.warning(msg)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global latency, latency2

    if msg.topic == MQTT_PONG:
       #_t = struct.unpack('>f',msg.payload)[0]
       latency = time_func() - float(msg.payload)
    
    if msg.topic == MQTT_PING:
       #_t = struct.unpack('>f',msg.payload)[0]
       latency2 = time_func() - float(msg.payload)
    
    rgpio.onMessage(client, userdata, msg)


def thread_manage_connection(event_object):
    global modem
    interval = 0
    while True:
        with lock:
            res = manage_connection()
            if not isinstance(res, tuple):
                interval = res
            else:
                interval = res[0]
                modem = res[1]
        event_object.wait(interval)


def thread_monitor_and_config(event_object):
    global modem
    while True:
        with lock:
            logger.debug("Configurator is working...")

            configure()
            logger.debug("Network manager is working...")
            network = manage_network(modem)
            logger.debug("Monitor is working...")
            monitor(modem, network)
            logger.debug("Geolocation is working...")
            update_geolocation(modem)
        event_object.wait(conf.get_send_monitoring_data_interval_config())

def thread_monitor(event_object):
    global modem, client
    logger.info("Monitor thread started.")

    while True:
      if modem.monitor["cellular_connection"]: # is internet ok ?!?
        #imu.printSensors()
        #print(f"Quaternion: {imu.getSensors().quaternion}")
        imu.publishSensors(client)
        rgpio.publishData(client)
        pass

      time.sleep(0.5)

def thread_mqtt(event_object):
    global modem, client
    logger.info("MQTT thread started.")

    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client._reconnect_delay = 0.5
    client.reconnect_delay_set(1,5)

    while True:
      if modem.monitor["cellular_connection"]: # is internet ok ?!?
        try:
            client.connect_async(MQTT_BROKER)
            client.loop_start() 
        except:
            logger.warning("Exception on connecting to the mqtt broker...")
        else:
            pass
        
        while True:
            now = time_func()
            _now = struct.pack('>f', now)
            client.publish(MQTT_PING, now)

            time.sleep(0.1)

      time.sleep(0.5)



def main():
    Thread(target=thread_manage_connection, args=(event,)).start()
    #Thread(target=thread_monitor_and_config, args=(event,)).start()
    
    # Monitor thread (es. IMU, etc.)
    myMonitor = Thread(target=thread_monitor, args=(event,))
    myMonitor.setName("thread_monitor")
    myMonitor.start()

    # MQTT thread
    myMQTT = Thread(target=thread_mqtt, args=(event,))
    myMQTT.setName("thread_mqtt")
    myMQTT.start()



if __name__ == "__main__":
    main()
