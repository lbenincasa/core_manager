# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import paho.mqtt.client as mqtt
import json
import adafruit_bno055


#i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
#sensor = adafruit_bno055.BNO055_I2C(i2c)
i2c = {}
sensor = {}

# If you are going to use UART uncomment these lines
# uart = board.UART()
# sensor = adafruit_bno055.BNO055_UART(uart)

last_val = 0xFFFF

def DoInit():
    i2c = board.I2C()
    sensor = adafruit_bno055.BNO055_I2C(i2c)

def temperature():
    global last_val  # pylint: disable=global-statement
    result = sensor.temperature
    if abs(result - last_val) == 128:
        result = sensor.temperature
        if abs(result - last_val) == 128:
            return 0b00111111 & result
    last_val = result
    return result

#---------------------------------------------MQTT
# Raspberry PI IP address
#MQTT_BROKER = "172.30.55.106"
#OLD MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
#MQTT_BROKER = "192.168.100.100"
## oracle-03
MQTT_BROKER = "130.162.34.184"

# Topic on which frame will be published
MQTT_SENSOR_ACC = "rw/host/monitor/acc"

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected to broker '" + MQTT_BROKER + "' with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe(MQTT_CMD)
    #client.subscribe(MQTT_PONG)
    #client.subscribe(MQTT_PING)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
   pass

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER)

# Starting thread which will receive the frames
client.loop_start()


if __name__ == "__main__":
    while True:
        if 1:  
            print("Temperature: {} degrees C".format(sensor.temperature))
        #    """
        #    print(
        #        "Temperature: {} degrees C".format(temperature())
        #    )  # Uncomment if using a Raspberry Pi
        #    """
            acc = sensor.acceleration
            client.publish(MQTT_SENSOR_ACC, json.dumps(acc))
        #    print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
            print("Accelerometer (m/s^2): {}".format(acc))
            print("Magnetometer (microteslas): {}".format(sensor.magnetic))
            print("Gyroscope (rad/sec): {}".format(sensor.gyro))
            print("Euler angle: {}".format(sensor.euler))
            print("Quaternion: {}".format(sensor.quaternion))
            print("Linear acceleration (m/s^2): {}".format(sensor.linear_acceleration))
            print("Gravity (m/s^2): {}".format(sensor.gravity))
            print()

            time.sleep(0.5)
