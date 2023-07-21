# Importing Libraries
# import the necessary packages
from picamera2 import Picamera2, MappedArray
import cv2 
import paho.mqtt.client as mqtt
import base64
import time
import numpy as np
import zlib
import libstreamvbyte as svb
import lz4.frame as lz
import rle
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class myCam(object):
  param1 = 1
  param2 = "ciao"
  param3 = True
  param4 = ()

  # Raspberry PI IP address
  MQTT_BROKER = "172.30.55.106"
  #MQTT_BROKER = "broker.emqx.io"
  #MQTT_BROKER = "192.168.100.100"
  ## oracle-03
  #MQTT_BROKER = "130.162.34.184"

  # Topic on which frame will be published
  MQTT_VIDEO_MJPEG  = "rw/host/video/mjpeg"
  MQTT_VIDEO_MJPEGD = "rw/host/video/mjpegd"

  def __init__(self):
      self.cnt = 0
      self.size = 0
      self.start = time.time()
      self.frame_diff = np.zeros((480, 640, 3), np.int16)
      self.quality = [50,25]
      self.picam2 = Picamera2()
      self.picam2.still_configuration.main.size = (640,480)
      #picam2.still_configuration.main.size = (800,600)
      #picam2.still_configuration.main.size = (320,200)
      self.picam2.still_configuration.main.format = "RGB888"
      #self.picam2.still_configuration.controls.FrameRate = 30.0
      self.picam2.still_configuration.controls.FrameRate = 10.0
      self.picam2.still_configuration.align()
      self.picam2.configure("still")
      self.picam2.pre_callback = apply_text
      self.picam2.start()

  def publishData(self,client):
      _frame = self.picam2.capture_array()
      self.cnt += 1

      if 1: #cnt == 1:
        frame = _frame
        #frame = cv2.cvtColor(_frame, cv2.COLOR_BGR2GRAY)
        topic = self.MQTT_VIDEO_MJPEG

        # Encoding the Frame
        #_, buffer = cv2.imencode('.jpg', frame)
        compression_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        #compression_params = [cv2.IMWRITE_JPEG_QUALITY, quality[cnt % len(quality)]]
        _, buffer = cv2.imencode('.jpg', frame, compression_params)
      else:
        #frame = cv2.subtract(reference, frame)
        #frame = cv2.subtract(_frame,prev)
        #frame = cv2.subtract(_frame,prev,frame_diff,mask,cv2.CV_16S)
        #_in1 = np.array(_frame, dtype='int16')
        #_in2 = np.array(prev, dtype='int16')
        #frame = cv2.subtract(_in1,_in2,frame_diff)
        frame = cv2.subtract(_frame.astype(np.int16),prev.astype(np.int16))
        #,frame_diff)
        frame += 128
        frame = frame.astype(np.uint8)
        
        #compressed_data = zlib.compress(frame)
        #compressed_data = svb.encode(frame)
        #buffer = lz.compress(frame)

        compression_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        _, buffer = cv2.imencode('.jpg', frame, compression_params)
        #compression2_params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
        #_, buffer = cv2.imencode('.png', frame, compression2_params)
        #frame = cv2.subtract(_frame,prev,frame_diff)
        #,mask)
        ##buffer = frame
        topic = self.MQTT_VIDEO_MJPEGD
        #frame = frame
    
      prev = _frame

      # Encoding the Frame
      #_, buffer = cv2.imencode('.jpg', frame)
      ##compression_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
      ##_, buffer = cv2.imencode('.jpg', frame, compression_params)

      # Converting the image into numpy array
      data_encode = np.array(buffer)
      # Converting the array to bytes.
      byte_encode = data_encode.tobytes()

      client.publish(topic, byte_encode)
      self.size += len(byte_encode)

      now = time.time()
      dt = now - self.start
      if dt > 1.5:
        self.start = time.time()
        #fps = 1/t
        #print(int(dt))
        bps = self.size / dt # bytes/sec
        pps = self.cnt / dt  # pkt/sec

        print(int(dt),"sec, band:",int((bps/1024)*8),"[Kbit/s], pkt:", self.cnt, ", pkt size:", int(self.size/self.cnt), "[bytes], pkt per sec:", int(pps))
        self.size = 0
        self.cnt = 0



def apply_text(request):
  #timestamp = "beni: " + time.strftime("%y-%m-%d %X.") + str(time.time_ns())
  #timestamp = "beni: " + time.strftime("%X.") + str(time.time_ns()/1000000)
  global cnt
  timestamp = time.strftime("%X.") #+ str(cnt)
  colour = (255, 255, 255)
  origin  = (3, 20)
  origin2 = (3, 40)

  font = cv2.FONT_HERSHEY_SIMPLEX
  scale = .5
  thickness = 1
  with MappedArray(request, "main") as m:
    cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)
    cv2.putText(m.array, "MJPEG", origin2, font, scale, colour, thickness)
    #cv2.putText(m.array, timestamp,(5, 30),cv2.FONT_HERSHEY_SIMPLEX,1,(0, 255, 255),1)

class StreamingHandler(SimpleHTTPRequestHandler):
  ##  Custom do_GET
  def do_GET(self):
      global frame
      if 'favicon.ico' in self.path:
          return
      if self.path == '/stream':
          print('\nStreaming started')
          self.send_response(200)
          self.send_header('Age', '0')
          self.send_header('Cache-Control', 'no-cache, private')
          self.send_header('Pragma', 'no-cache')
          self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
          self.end_headers()
          try:
              while True:
                  try:
                      ##frame = getFrame()
                      self.wfile.write(b'--FRAME\r\n')
                      self.send_header('Content-Type', 'image/jpeg')
                      self.send_header('Content-Length', str(len(frame)))
                      self.end_headers()
                      self.wfile.write(frame)
                      self.wfile.write(b'\r\n')
                  except Exception as e:
                      print('\nClient Disconnected with message ' + str(e))
                      break
          except Exception as e:
              print('\nRemoved client from ' + str(self.client_address) + ' with message ' + str(e))
      elif self.path == '/terminate':
          self.send_response(200)
          self.end_headers()
          ##shut_down()
      else:
          self.send_error(404)
          self.end_headers()


if __name__ == "__main__":

    # Phao-MQTT Clinet
    client = mqtt.Client()
    # Establishing Connection with the Broker
    client.connect(myCam.MQTT_BROKER)
    print("Connected")

    cam = myCam()


    try:
    # server = ThreadingHTTPServer((host, port), StreamingHandler)
    # server.daemon = True  # Make sure it stops when program does
    # server.serve_forever()

      while True:
        cam.publishData(client)
    
    except:
      #cap.release()
      client.disconnect()
      print("\nNow you can restart fresh")
 
