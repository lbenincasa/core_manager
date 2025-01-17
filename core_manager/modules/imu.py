# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import paho.mqtt.client as mqtt
import json
import adafruit_bno055
import platform


i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sensors = adafruit_bno055.BNO055_I2C(i2c)
#MQTT_SENSOR_IMU = "rw/host/sensors/imu/"
MQTT_SENSOR_IMU = f"rw/{platform.node()}/sensors/imu/"


# If you are going to use UART uncomment these lines
# uart = board.UART()
# sensor = adafruit_bno055.BNO055_UART(uart)

last_val = 0xFFFF

#vedi tabella 3.5 del datasheet
mode2string = ["CONFIG","ACCONLY","MAGONLY","GYRONLY", "ACCMAG","ACCGYRO","MAGGYRO","AMG","IMUPLUS","COMPASS","M4G","NDOF_FMC_OFF","NDOF"]

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
    client.publish(topic+"calib", json.dumps([sensors.calibrated, sensors.calibration_status]))
    client.publish(topic+"mode", json.dumps(sensors.mode))
    client.publish(topic+"offsets", json.dumps([sensors.offsets_magnetometer,
                                                sensors.offsets_accelerometer,
                                                sensors.offsets_gyroscope]))


def printSensors():
    print(f"Temperature: {sensors.temperature} degrees C")
#    """
#    print(
#        "Temperature: {} degrees C".format(temperature())
#    )  # Uncomment if using a Raspberry Pi
#    """
    acc = sensors.acceleration
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

def printInfo():
    print(f"Calibration status...: {sensors.calibration_status}")
    print(f"                  sys: {sensors.calibration_status[0]}")
    print(f"                 gyro: {sensors.calibration_status[1]}")
    print(f"                accel: {sensors.calibration_status[2]}")
    print(f"                  mag: {sensors.calibration_status[3]}")
    print(f"Calibrated  status...: {sensors.calibrated}")
    print(f"Mode.................: {mode2string[sensors.mode]} ({sensors.mode})")
    print(f"Offsets Magnetometer.: {sensors.offsets_magnetometer}")
    print(f"Offsets Accelerometer: {sensors.offsets_accelerometer}")
    print(f"Offsets Gyroscope....: {sensors.offsets_gyroscope}")
    print()
    


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
            printInfo()
            publishSensors(client)
            time.sleep(0.5)
