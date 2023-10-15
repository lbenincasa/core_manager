
import time
import paho.mqtt.client as mqtt
import json
import pynmea2
import serial
import platform
import io
from threading import Thread, Lock, Event

try:# Use monotonic clock if available
    ## Beni, disabilitata per il momento: time_func = time.monotonic
    time_func = time.monotonic
except AttributeError:
    time_func = time.time



MQTT_SENSOR_GPS = f"rw/{platform.node()}/sensors/gps/"

ser = serial.Serial('/dev/ttyUSB1', 115200, timeout=5.0)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))


position = {}
info = {}
sensors = {'position':position, 'info':info}


def publishSensors(client,topic=MQTT_SENSOR_GPS):
    client.publish(topic+"position", json.dumps(sensors['position']))
    client.publish(topic+"info", json.dumps(sensors['info']))
#    client.publish(topic+"gyro", json.dumps(sensors.gyro))
#    client.publish(topic+"euler", json.dumps(sensors.euler))
#    client.publish(topic+"quaternion", json.dumps(sensors.quaternion))
#    client.publish(topic+"linear_acceleration", json.dumps(sensors.linear_acceleration))
#    client.publish(topic+"gravity", json.dumps(sensors.gravity))
    pass


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


def thread_gps():

    global sensors, position, info
    GPS_INIT     = 1
    GPS_NO_DATA  = 2
    GPS_IDLE     = 3
    gps_state = GPS_INIT

    _now = time_func()
    _old = _now
    _cnt = 0

    while 1:
        try:
#            line = sio.readline()
            line = ser.readline().decode('utf-8')
            sdata = line.split(",")
            _cnt += 1

            _now = time_func()
            delta = _now - _old
            _old = _now

            if gps_state == GPS_INIT:
                gps_state = GPS_NO_DATA
                info['state'] = "init"

            elif gps_state == GPS_NO_DATA:
                # position = {}
                info['state'] = "no data"

                if sdata[0] == "$GPRMC":
                    if sdata[2] != 'V':
                       gps_state = GPS_IDLE 

            elif gps_state == GPS_IDLE:
              info['state'] = "idle"

              if sdata[0] == "$GPRMC" and sdata[2] == 'V':
                   gps_state = GPS_NO_DATA
              else:

                msg = pynmea2.parse(line)
                #print(repr(msg))

                if msg.sentence_type == 'GGA':
                    position['time'] = sdata[1][0:2] + ":" + sdata[1][2:4] + ":" + sdata[1][4:6] + "." + sdata[1][7:9]
                    position['latitude'] = msg.latitude
                    position['lat'] = float(msg.lat)
                    position['lat_dir'] = msg.lat_dir
                    position['longitude'] = msg.longitude
                    position['lon'] = float(msg.lon)
                    position['lon_dir'] = msg.lon_dir
                    position['hdop'] = float(msg.horizontal_dil)
                    position['altitude'] = msg.altitude
                    position['num_sats'] = int(msg.num_sats)

                elif msg.sentence_type == 'GSA':
                    position['fix'] = msg.mode_fix_type

                elif msg.sentence_type == 'RMC':
                    position['time'] = sdata[1][0:2] + ":" + sdata[1][2:4] + ":" + sdata[1][4:6] + "." + sdata[1][7:9]
                    position['date'] = sdata[9][0:2] + "/" + sdata[9][2:4] + "/" + "20" + sdata[9][4:6] #date
                    position['latitude'] = msg.latitude
                    position['longitude'] = msg.longitude
                    position['status'] = msg.status
                    position['nav_status'] = msg.nav_status
                    position['spkn'] = msg.spd_over_grnd

                elif msg.sentence_type == 'VTG':
                    position['cog'] = msg.true_track
                    position['spkm'] = msg.spd_over_grnd_kmph
    #                position['spkn'] = 0.0 #msg.spd_over_grnd_kts

                elif msg.sentence_type == 'GSV':
                    position['num_sats_in_view'] = int(msg.num_sv_in_view)

            #sensors[msg.sentence_type] = msg
            info['delta'] = delta
            info['cnt'] = _cnt

        except serial.SerialException as e:
            print('Device error: {}'.format(e))
            break
        except pynmea2.ParseError as e:
            print('Parse error: {}'.format(e))
            continue
        except ValueError as e:
            print(f'Parse error: {e}')
            continue
        #time.sleep(0.1)

def main():
    # Serial NMEA sentences thread
    myGPS = Thread(target=thread_gps, args=())
    myGPS.setName("thread_gps")
    myGPS.start()

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER)

    # Starting thread which will receive the frames
    client.loop_start()
    main()

    while True:
        if 1:  
            #printSensors()
            publishSensors(client)
            time.sleep(0.5)
