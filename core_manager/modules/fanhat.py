import smbus
import RPi.GPIO as GPIO
import os
import time
from threading import Thread
rev = GPIO.RPI_REVISION
if rev == 2 or rev == 3:
	bus = smbus.SMBus(1)
else:
	bus = smbus.SMBus(0)


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
	fanconfig = ["65=100", "60=55", "55=10"]
#	tmpconfig = load_config("")
#	if len(tmpconfig) > 0:
#		fanconfig = tmpconfig
	address=0x1a
	prevblock=0
	bus.write_byte(address,60)
	while True:
		try:
			tempfp = open("/sys/class/thermal/thermal_zone0/temp", "r")
			temp = tempfp.readline()
			tempfp.close()
			val = float(int(temp)/1000)
		except IOError:
			val = 0
		block = get_fanspeed(val, fanconfig)
		if block < prevblock:
			time.sleep(5)
		prevblock = block
		try:
			if block > 0:
				bus.write_byte(address,100)
				time.sleep(1)
			bus.write_byte(address,block)
		except IOError:
			temp=""
		time.sleep(5)

if __name__ == "__main__":
    try:
        t2 = Thread(target = temp_check)
        t2.start()
    except:
        t2.stop()
