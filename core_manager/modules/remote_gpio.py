# Importing Libraries
# import the necessary packages
import base64
import time
import paho.mqtt.client as mqtt


import pigpio
import struct
import sys
import psutil
import json


# connect to localhost pigpiod
pi = pigpio.pi()

if not pi.connected:
   print("Aborting: pigpio not connected!!")
   exit()


# Raspberry PI IP address
#MQTT_BROKER = "172.30.55.106"
#OLD MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
#MQTT_BROKER = "192.168.100.100"
## oracle-03
MQTT_BROKER = "130.162.34.184"

# Topic on which frame will be published
MQTT_PIGPIO = "rw/host/pigpio/"
MQTT_PIGPIO_BANK = MQTT_PIGPIO + "bank/"
MQTT_PIGPIO_CMD  = MQTT_PIGPIO + "cmd"
#MQTT_PONG = "rw/host/pong"
#MQTT_PING = "rw/host/ping"

# The callback for when the client receives a CONNACK response from the server.
def onConnect(client, userdata, flags, rc):
    #print("Connected to broker '" + MQTT_BROKER + "' with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(MQTT_PIGPIO_CMD)
#    client.subscribe(MQTT_PONG)
#    client.subscribe(MQTT_PING)


# The callback for when a PUBLISH message is received from the server.
def onMessage(client, userdata, msg):

    if msg.topic == MQTT_PIGPIO_CMD:
        print("msg:" + str(msg.payload))
        cmd = struct.unpack('>IIII',msg.payload)

        if cmd[0] == pigpio._PI_CMD_SERVO:
            pi.set_servo_pulsewidth(cmd[1], cmd[2])
        elif cmd[0] == pigpio._PI_CMD_PWM:
            pi.set_PWM_dutycycle(cmd[1], cmd[2])
        elif cmd[0] == pigpio._PI_CMD_WRITE:
            pi.write(cmd[1], cmd[2])
        else:
            print("unknown cmd received!!")

def publishBanks(client,topic=MQTT_PIGPIO_BANK):

    levels = pi.read_bank_1()
    p = struct.pack('>ii', levels, 1)
    client.publish(topic+"1", p)

def publishData(client,topic=MQTT_PIGPIO):
    publishBanks(client,topic+"bank/")
   
   



if __name__ == "__main__":

    levels = 0
    levels_old = levels

    client = mqtt.Client()
    client.connect_async(MQTT_BROKER)

    # Starting thread which will receive the frames
    client.loop_start()

    print("byte order:", sys.byteorder)

    start = time.time()
    while True:

        #levels = pi.read_bank_1()
        #p = struct.pack('>ii', levels, 1)
        #client.publish(MQTT_SEND, p)

        if levels != levels_old:
            levels_old = levels
            print("levels:",str(levels))

        now = time.time()
        dt = now - start
        if dt > 0.1:
            #print(" > latency [ms]:", str(latency*1000.0)) #ms
            #_l1 = latency*1000.0/2
            #_l2 = latency2*1000.0/2
            #print(" > latency [ms]: " + str(int(_l2)) + " - " + str(int(_l1))) #ms
            #print(" > latency2 [ms]:", format((latency2*1000.0), '.2f')) #ms

            #psutil
            cpu_usage = psutil.cpu_percent(interval=1, percpu=True)
            client.publish("rw/host/monitor/cpu/usage", cpu_usage[0])

            temps = psutil.sensors_temperatures(fahrenheit=False)
            client.publish("rw/host/monitor/cpu/temp", temps['cpu_thermal'][0][1])
            client.publish("rw/host/monitor/cpu/obj", json.dumps(temps))
            print(temps['cpu_thermal'][0][1])
            
            start = time.time()

        time.sleep(0.1)

        
    #except:
    #cap.release()
    #client.disconnect()

    # Stop the Thread
    #client.loop_stop()

