import smbus
import RPi.GPIO as GPIO
import os
import time
from threading import Thread
import platform
import paho.mqtt.client as mqtt
import json



MQTT_SENSOR_FANHAT = f"rw/{platform.node()}/sensors/fanhat"
info = {}
sensors = {'temp':-1.0, 'info':info}


def publishSensors(client,topic=MQTT_SENSOR_FANHAT):
    client.publish(topic+"/temp", json.dumps(sensors['temp']))
    client.publish(topic+"/info", json.dumps(sensors['info']))

def printSensors():
    print(sensors)

#---------------------------------------------MQTT
# Raspberry PI IP address
#MQTT_BROKER = "172.30.55.106"
#OLD MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
#MQTT_BROKER = "192.168.100.100"
## oracle-03
MQTT_BROKER = "130.162.34.184"

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print(f"Connected to broker '{client._host}' with result code {str(rc)}")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe(MQTT_CMD)
    #client.subscribe(MQTT_PONG)
    #client.subscribe(MQTT_PING)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
   pass


rev = GPIO.RPI_REVISION
if rev == 2 or rev == 3:
	bus = smbus.SMBus(1)
else:
	bus = smbus.SMBus(0)

speed_min = 40

def get_fanspeed(tempval, configlist):
	for curconfig in configlist:
		curpair = curconfig.split("=")
		tempcfg = float(curpair[0])
		fancfg = int(float(curpair[1]))
		if tempval >= tempcfg:
			if fancfg < 1:
				return 0
			elif fancfg < 25:
				return 25
			return fancfg
	return 0

def load_config(fname):
	newconfig = []
	try:
		with open(fname, "r") as fp:
			for curline in fp:
				if not curline:
					continue
				tmpline = curline.strip()
				if not tmpline:
					continue
				if tmpline[0] == "#":
					continue
				tmppair = tmpline.split("=")
				if len(tmppair) != 2:
					continue
				tempval = 0
				fanval = 0
				try:
					tempval = float(tmppair[0])
					if tempval < 0 or tempval > 100:
						continue
				except:
					continue
				try:
					fanval = int(float(tmppair[1]))
					if fanval < 0 or fanval > 100:
						continue
				except:
					continue
				newconfig.append( "{:5.1f}={}".format(tempval,fanval))
		if len(newconfig) > 0:
			newconfig.sort(reverse=True)
	except:
		return []
	return newconfig

def temp_check():
	fanconfig = ["50=100", "45=80", "40=70", "35=50", "30=40", "25=25"]
#test	fanconfig = ["38=100", "35=80", "33=65", "32=50", "30=40", "25=25"]
#	tmpconfig = load_config("")
#	if len(tmpconfig) > 0:
#		fanconfig = tmpconfig
	address=0x1a
#	bus.write_byte(address,speed_min)
	try:
		tempfp = open("/sys/class/thermal/thermal_zone0/temp", "r")
		temp = tempfp.readline()
		tempfp.close()
		val = float(int(temp)/1000)
		sensors['temp'] = val
	except IOError:
		val = 0
	
	speed = get_fanspeed(val, fanconfig)
	info['speed_tgt'] = speed

	if speed == 0:
		speed = speed_min

	info['speed'] = speed
	#info['config'] = fanconfig

	try:
		bus.write_byte(address,speed)
	except IOError:
		pass


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER)

    # Starting thread which will receive the frames
    client.loop_start()

    while True:
      temp_check()
      printSensors()
      publishSensors(client)

      time.sleep(1)
