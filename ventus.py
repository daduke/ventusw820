import btle
import array

# read measurements from Ventus W820 weather station via bluetooth 
# (c) 2015 Christian Herzog <daduke@daduke.org>
# project website: http://daduke.org/coding/ventus.html
#
# we always provide metric units, no matter what mode the W820 is in
# temps: degC
# humidity: %
# pressure: hPa
# rain: mm
# wind speed: km/h
# wind direction: 0: N, 1: NNE ... 15: NNW
#
# reverse enginieered using a BLE sniffer and the Ventus Android app
#
# requires bluepy: https://github.com/IanHarvey/bluepy


sensorData = {}
w820 = 0

class w820Delegate(btle.DefaultDelegate):
    def __init__(self, hndl):
        btle.DefaultDelegate.__init__(self)
        self.hndl=hndl;

    def handleNotification(self, cHandle, data):
       #data = data.encode("hex")
       data = array.array('B', data)
       if data[0] == 1:
	       sensorData['degF'] = 0
	       if data[5] < 127:	#temps come in 2's complement
		       sensorData['indoorTemperature'] = ((data[5] * 256) + data[6])/10.0
	       else:
		       sensorData['outdoorTemperature'] = -(((255-data[5]) * 256) + (255-data[6]))/10.0
	       sensorData['indoorHumidity'] = data[7]
	       if data[12] < 127:	#temps come in 2's complement
		       sensorData['outdoorTemperature'] = ((data[12] * 256) + data[13])/10.0
	       else:
		       sensorData['outdoorTemperature'] = -(((255-data[12]) * 256) + (255-data[13]))/10.0
	       sensorData['outdoorHumidity'] = data[14]
	       if (data[1] & 2) != 0:	# degF
		       sensorData['indoorTemperature'] = (sensorData['indoorTemperature'] - 32) / 1.8
		       sensorData['outdoorTemperature'] = (sensorData['outdoorTemperature'] - 32) / 1.8
		       sensorData['degF'] = 1
	       if (data[1] & 8) != 0:
		       sensorData['lowBat'] = 1
	       else:
		       sensorData['lowBat'] = 0
	

       elif data[0] == 2:
	       pressureUnit = ((data[1]) & 6) >> 1
	       if pressureUnit > 2:
		       pressureUnit = 2
       	       sensorData['airPressure'] = ((data[3] * 256) + data[4])
	       if pressureUnit == 0:	#Pascalish
		       sensorData['airPressure'] /= 10.0
	       elif pressureUnit == 1:	#mm Hg, but wrong
		       sensorData['airPressure'] /= 10.0
	       elif pressureUnit == 2:	#inches Hg
		       sensorData['airPressure'] *= 0.338639
       elif data[0] == 3:
	       rainUnit = data[1] & 16	#0: mm, 16: inches
	       if rainUnit == 16:
		       rainFactor = 0.01 * 25.4
	       else:
		       rainFactor = 0.1
	       windUnit = (data[1] & 14) >> 1
	       if windUnit > 4:	#0: km/h, 1: mph, 2: m/s, 3: knots, 4: bft
		       windUnit = 4
               sensorData['UV'] = data[18]
	       sensorData['rainDaily'] = ( (data[3] * 256) + data[4] ) * rainFactor
	       sensorData['rainWeekly'] = ( (data[5] * 256) + data[6] ) * rainFactor
	       sensorData['rainMonthly'] = ( ((data[7] * 65536) + (data[8] * 256)) + data[9] ) * rainFactor
	       sensorData['rainTotal'] = ( ((data[15] * 65536) + (data[16] * 256)) + data[17] ) * rainFactor
	       sensorData['windSpeed'] = (data[11] * 256) + data[12]
	       sensorData['windChill'] = ((data[13] * 256) + data[14])/10.0
	       sensorData['windDirection'] = data[10]
	       if windUnit == 0:
		       sensorData['windSpeed'] *= 0.1
	       if windUnit == 1:
		       sensorData['windSpeed'] = sensorData['windSpeed'] * 0.1 * 1.60934
		       if sensorData['degF'] == 0:	# bug in W820: wind speeds not in km/h depend on temperature unit!!!
			       sensorData['windSpeed'] *= 0.01313868613138686131
	       elif windUnit == 2:
		       sensorData['windSpeed'] = sensorData['windSpeed'] * 0.1 * 3.6
		       if sensorData['degF'] == 0:	# bug in W820: wind speeds not in km/h depend on temperature unit!!!
			       sensorData['windSpeed'] *= 0.01157742402315484804
	       elif windUnit == 3:
		       sensorData['windSpeed'] = sensorData['windSpeed'] * 0.1 * 1.85199539525386
		       if sensorData['degF'] == 0:	# bug in W820: wind speeds not in km/h depend on temperature unit!!!
			       sensorData['windSpeed'] *= 0.03782505910165484633
	
def connect(mac):
   w820 = None
   try:
       w820 = btle.Peripheral(mac, 'random')
       return w820
   except:
       e = sys.exc_info()[0]
       print e
   finally:
       return w820


def setTime(w820, time):
   #TODO
   w820.writeCharacteristic(0x000b, time, True)
   pass

def read(w820):
   w820.setDelegate(w820Delegate(''))
   try:
	   w820.writeCharacteristic(0x000e, '\x01\x00', True)		# Turn on notificiations
	   w820.writeCharacteristic(0x000b, '\xb0\x01\x00\x00', True)	# Request data
	   w820.waitForNotifications(1)					# wait for response
	   w820.writeCharacteristic(0x000b, '\x40\x01\x00\x00', True)	# send ACK for next packet
	   w820.waitForNotifications(1)					# wait for response
	   w820.writeCharacteristic(0x000b, '\x40\x01\x00\x00', True)	# send ACK for next packet
	   w820.waitForNotifications(1)					# wait for response

   except:
       e = sys.exc_info()[0]
       print e
   finally:
           return sensorData

def disconnect(w820):
   try:
       w820.disconnect
   except:
       e = sys.exc_info()[0]
       print e
