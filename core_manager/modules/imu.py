# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import paho.mqtt.client as mqtt
import json
import adafruit_bno055


i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sensors = adafruit_bno055.BNO055_I2C(i2c)
MQTT_SENSOR_IMU = "rw/host/sensors/imu/"

# If you are going to use UART uncomment these lines
# uart = board.UART()
# sensor = adafruit_bno055.BNO055_UART(uart)

last_val = 0xFFFF

def temperature():
    global last_val  # pylint: disable=global-statement
    result = sensors.temperature
    if abs(result - last_val) == 128:
        result = sensors.temperature
        if abs(result - last_val) == 128:
            return 0b00111111 & result
    last_val = result
    return result

def publishSensors(client,topic=MQTT_SENSOR_IMU):
    client.publish(topic+"acceleration", json.dumps(sensors.acceleration))
    client.publish(topic+"magnetic", json.dumps(sensors.magnetic))
    client.publish(topic+"gyro", json.dumps(sensors.gyro))
    client.publish(topic+"euler", json.dumps(sensors.euler))
    client.publish(topic+"quaternion", json.dumps(sensors.quaternion))
    client.publish(topic+"linear_acceleration", json.dumps(sensors.linear_acceleration))
    client.publish(topic+"gravity", json.dumps(sensors.gravity))


def printSensors():
    print(f"Temperature: {sensors.temperature} degrees C")
#    """
#    print(
#        "Temperature: {} degrees C".format(temperature())
#    )  # Uncomment if using a Raspberry Pi
#    """
    acc = sensors.acceleration
    #client.publish(MQTT_SENSOR_ACC, json.dumps(acc))
#    print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
    print(f"Accelerometer (m/s^2): {acc}")
    print(f"Magnetometer (microteslas): {sensors.magnetic}")
    print(f"Gyroscope (rad/sec): {sensors.gyro}")
    print(f"Euler angle: {sensors.euler}")
    print(f"Quaternion: {sensors.quaternion}")
    print(f"Linear acceleration (m/s^2): {sensors.linear_acceleration}")
    print(f"Gravity (m/s^2): {sensors.gravity}")
    print()

def getSensors():
    return sensors

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
    print(f"Connected to broker '{client._host}' with result code {str(rc)}")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe(MQTT_CMD)
    #client.subscribe(MQTT_PONG)
    #client.subscribe(MQTT_PING)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
   pass


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER)

    # Starting thread which will receive the frames
    client.loop_start()

    while True:
        if 1:  
            printSensors()
            publishSensors(client)
            time.sleep(0.5)
