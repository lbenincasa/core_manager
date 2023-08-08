#!/usr/bin/python3

from threading import Thread, Lock, Event

from helpers.config_parser import conf
from helpers.logger import logger, update_log_mqtt
from helpers.modem_support.default import BaseModule

from cm import manage_connection, modem
from nm import manage_network
from monitor import monitor
from configurator import configure
from geolocation import update_geolocation

#from modules.imu import sensor
import modules.imu as imu
import modules.remote_gpio as rgpio
import modules.cam as mycam

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
latency  = [
    #latency,last,cnt,old,name
    [0.0,[0],0,0,"latency0"],  # 0: ritardo tra device e broker MQTT
    [0.0,[0],0,0,"latency1"],  # 1: ritardo tra device e app finale (con UI, anche attraverso broker MQTT)
]

#---------------------------------------------MQTT
# Raspberry PI IP address
#MQTT_BROKER = "172.30.55.106"
#OLD MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
MQTT_BROKER = "192.168.100.100"
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
    global latency

    # ritardo tra device e broker MQTT
    if msg.topic == MQTT_PING:
       #_t = struct.unpack('>f',msg.payload)[0]
       latency[0][0] = time_func() - float(msg.payload)
       latency[0][1].append(msg.payload)
       if len(latency[0][1]) > 10:
          latency[0][1].pop(0)
       latency[0][2] += 1


    # ritardo tra device e app finale (con UI, anche attraverso broker MQTT)
    if msg.topic == MQTT_PONG:
       #_t = struct.unpack('>f',msg.payload)[0]
       latency[1][0] = time_func() - float(msg.payload)
       latency[1][1].append(msg.payload)
       if len(latency[1][1]) > 10:
          latency[1][1].pop(0)
       latency[1][2] += 1
    
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
        
        update_log_mqtt(logger,client,True)

        while True:
            now = time_func()
            _now = struct.pack('>f', now)
            client.publish(MQTT_PING, now)

            time.sleep(0.1)

      time.sleep(0.5)

def thread_cam(event_object):
    global modem, client
    logger.info("CAM thread started.")
    excpt_cnt = 0

    try:
      cam = mycam.myCam()
    except:
      logger.warning("Exception on creating myCam...")
      time.sleep(1)

    while True:
      if 'cam' not in locals():
        try:
            cam = mycam.myCam()
        except:
            excpt_cnt += 1
            if (excpt_cnt < 5) or (excpt_cnt % 30 == 0):
              logger.warning(f"Exception ({excpt_cnt}) on creating myCam...")
            time.sleep(1)
      else:
        if modem.monitor["cellular_connection"]: # is internet ok ?!?
            while True:
                cam.publishData(client, latency)

      time.sleep(0.1)


FAILSAFE_INIT = 1
FAILSAFE_OFF  = 2
FAILSAFE_ON   = 3
failsafe_state = FAILSAFE_INIT

def thread_failsafe(event_object):
    global modem, client, failsafe_state,latency
    logger.info("FAILSAFE thread started.")
    toggle = 0
    cnt = 0

    while True:
      if failsafe_state == FAILSAFE_INIT:
         failsafe_state = FAILSAFE_ON
      elif failsafe_state == FAILSAFE_OFF:
        #------------------------------------------------------------------- OFF.i
        if not modem.monitor["cellular_connection"]: # is internet nok ?!?
            failsafe_state = FAILSAFE_ON

        if cnt >= 5:
            if toggle: rgpio.UserLedOn()
            else:      rgpio.UserLedOff()
            toggle = 0 if toggle else 1
            cnt = 0
        cnt += 1

        if latency[1][2] != latency[1][3]:
            latency[1][3] = latency[1][2]
        else:
           failsafe_state = FAILSAFE_ON

        #------------------------------------------------------------------- OFF.f
      elif failsafe_state == FAILSAFE_ON:
        #------------------------------------------------------------------- ON.i
        cnt = 0
        rgpio.onFailSafe()

        if toggle: rgpio.UserLedOn()
        else:      rgpio.UserLedOff()
        toggle = 0 if toggle else 1

        if modem.monitor["cellular_connection"]: # is internet nok ?!?
            failsafe_state = FAILSAFE_OFF
        
        if latency[1][2] != latency[1][3]:
            latency[1][3] = latency[1][2]
            failsafe_state = FAILSAFE_OFF

        #------------------------------------------------------------------- ON.f
      
      time.sleep(0.1)



def main():
    rgpio.UserLedOff()

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

    # CAM thread
    myCAM = Thread(target=thread_cam, args=(event,))
    myCAM.setName("thread_cam")
    myCAM.start()

    # FailSafe thread
    myFAILSAFE = Thread(target=thread_failsafe, args=(event,))
    myFAILSAFE.setName("thread_failsafe")
    myFAILSAFE.start()



if __name__ == "__main__":
    main()
