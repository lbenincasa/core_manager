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


def apply_text(request):
  #timestamp = "beni: " + time.strftime("%y-%m-%d %X.") + str(time.time_ns())
  #timestamp = "beni: " + time.strftime("%X.") + str(time.time_ns()/1000000)
  global cnt
  timestamp = time.strftime("%X.") + str(cnt)
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


# Raspberry PI IP address
#MQTT_BROKER = "172.30.45.93"
#MQTT_BROKER = "broker.emqx.io"
MQTT_BROKER = "192.168.100.100"
## oracle-03
#MQTT_BROKER = "130.162.34.184"

# Topic on which frame will be published
##TO BE DELETED: MQTT_SEND = "home/server/normal"
##TO BE DELETED: MQTT_SEND_REF = "home/server/ref"
MQTT_VIDEO_MJPEG  = "rw/host/video/mjpeg"
MQTT_VIDEO_MJPEGD = "rw/host/video/mjpegd"

local = False
frame_diff = np.zeros((480, 640, 3), np.int16)
#quality = [50,40,30,20,30,40]
quality = [50,25]
#mask = np.zeros((480, 640, 3), np.int16)
#frame_diff = np.zeros((480, 640, 3), np.uint8)
#mask = np.zeros((480, 640, 3), np.uint8)


picam2 = Picamera2()
#picam2.preview_configuration.main.size = (1280,720)
#picam2.preview_configuration.main.format = "RGB888"
#picam2.preview_configuration.align()
#picam2.configure("preview")
#picam2.still_configuration.main.size = (1280,720)
picam2.still_configuration.main.size = (640,480)
#picam2.still_configuration.main.size = (800,600)
#picam2.still_configuration.main.size = (320,200)
picam2.still_configuration.main.format = "RGB888"
picam2.still_configuration.controls.FrameRate = 30.0
#picam2.still_configuration.controls.FrameRate = 10.0
picam2.still_configuration.align()

picam2.configure("still")

picam2.pre_callback = apply_text

#video_config = picam2.create_video_configuration({"size": (1280, 720)})
#picam2.configure(video_config)


picam2.start()
#while True:
#    im= picam2.capture_array()
    #cv2.imshow("Camera", im)
#    if cv2.waitKey(1)==ord('q'):
#        break
#cv2.destroyAllWindows()

# Phao-MQTT Clinet
client = mqtt.Client()
# Establishing Connection with the Broker
client.connect(MQTT_BROKER)
print("Connected")
start = time.time()
size = 0
cnt = 0

host = '0.0.0.0'
port = 8090


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



try:
  # server = ThreadingHTTPServer((host, port), StreamingHandler)
  # server.daemon = True  # Make sure it stops when program does
  # server.serve_forever()

 while True:
  #start = time.time()
  # Read Frame
  #ret, frame = cap.read()
  #current frame from camera
  _frame = picam2.capture_array()
  cnt += 1

  if 1: #cnt == 1:
    frame = _frame
    #frame = cv2.cvtColor(_frame, cv2.COLOR_BGR2GRAY)
    topic = MQTT_VIDEO_MJPEG

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
    topic = MQTT_VIDEO_MJPEGD
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
  size = size + len(byte_encode)

  now = time.time()
  dt = now - start
  if dt > 1.5:
    start = time.time()
    #fps = 1/t
    #print(int(dt))
    bps = size / dt # bytes/sec
    pps = cnt / dt  # pkt/sec

    print(int(dt),"sec, band:",int((bps/1024)*8),"[Kbit/s], pkt:", cnt, ", pkt size:", int(size/cnt), "[bytes], pkt per sec:", int(pps))
    size = 0
    cnt = 0



#  frame32 = cv2.cvtColor(_frame, cv2.COLOR_BGR2BGRA)
#  fbframe = cv2.resize(_frame, (1920,1080))
#  with open('/dev/fb0', 'rb+') as buf:
#    buf.write(fbframe)

  #cv2.imshow("Local stream", _frame)
  #if local:
    #cv2.imshow("Local stream", frame)
    #img = base64.b64decode(msg.payload)
    # converting into numpy array from buffer
    #npimg = np.frombuffer(img, dtype=np.uint8)
    # Decode to Original Frame
    #frame = cv.imdecode(npimg, 1)
    
except:
 #cap.release()
 client.disconnect()
 print("\nNow you can restart fresh")
 # closing all open windows
 if local:
   cv2.destroyAllWindows()
 
