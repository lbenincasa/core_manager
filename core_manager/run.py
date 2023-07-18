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

import time


lock = Lock()
event = Event()
#modem = BaseModule() --> gia' dichiarata in cm.py

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
    global modem
    logger.info("Monitor started.")
    imu.DoInit()

    while True:
      if modem.monitor["cellular_connection"]: # is internet ok ?!?

        print(f"Temperature: {imu.sensor.temperature} degrees C")
        #    """
        #    print(
        #        "Temperature: {} degrees C".format(temperature())
        #    )  # Uncomment if using a Raspberry Pi
        #    """
        acc = imu.sensor.acceleration
        #client.publish(MQTT_SENSOR_ACC, json.dumps(acc))
    #    print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
        print("Accelerometer (m/s^2): {}".format(acc))
        print("Magnetometer (microteslas): {}".format(imu.sensor.magnetic))
        print("Gyroscope (rad/sec): {}".format(imu.sensor.gyro))
        print("Euler angle: {}".format(imu.sensor.euler))
        print("Quaternion: {}".format(imu.sensor.quaternion))
        print("Linear acceleration (m/s^2): {}".format(imu.sensor.linear_acceleration))
        print("Gravity (m/s^2): {}".format(imu.sensor.gravity))
        print()

        time.sleep(0.5)

def main():
    Thread(target=thread_manage_connection, args=(event,)).start()
    #Thread(target=thread_monitor_and_config, args=(event,)).start()
    myMonitor = Thread(target=thread_monitor, args=(event,))
    myMonitor.start()


if __name__ == "__main__":
    main()
