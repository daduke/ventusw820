#!/usr/bin/env python
#
# weewx driver for Ventus W820 weather station
# (c) 2015 Christian Herzog <daduke@daduke.org>
# requires companion library to read the Ventus data via bluetooth: http://daduke.org/coding/ventus.html


"""Driver for Ventus W820 weather stations.

"""

from __future__ import with_statement
import syslog
import time
import ventus

import weewx.drivers

DRIVER_NAME = 'W820'
DRIVER_VERSION = '0.01'


def loader(config_dict, _):
    return W820Driver(**config_dict[DRIVER_NAME])

def confeditor_loader():
    return W820ConfEditor()

DEBUG_READ = 0


def logmsg(level, msg):
    syslog.syslog(level, 'ventusw820.py: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

class W820Driver(weewx.drivers.AbstractDevice):
    """weewx driver that communicates with a Ventus W820 station
    
    mac - mac address of the BLE interface
    [Required. No default]

    polling_interval - time between two readings in seconds
    [Optional. Default is 60]
    """
    def __init__(self, **stn_dict):
        self.mac = stn_dict.get('mac')
        self.polling_interval = int(stn_dict.get('polling_interval', 60))
        self._last_rain = None
        loginf('driver version is %s' % DRIVER_VERSION)
        global DEBUG_READ
        DEBUG_READ = int(stn_dict.get('debug_read', DEBUG_READ))
        self.station = Station(self.mac)

    def closePort(self):
        if self.station is not None:
            self.station = None

    @property
    def hardware_name(self):
        return "W820"

    def genLoopPackets(self):
        while True:
            data = self.station.get_readings()
            if Station.validate_data(data):
                packet = Station.data_to_packet(data, int(time.time() + 0.5), last_rain=self._last_rain)
                self._last_rain = packet['rainTotal']
                yield packet
                time.sleep(self.polling_interval)

class Station(object):
    def __init__(self, mac):
        self.mac = mac
        self.handle = None
        self.sensorData = {}

    def get_readings(self):
        sensorData = {}
        sensorData['indoorTemperature'] = None
        if self.handle is None:
            try:
                #JW logdbg("open bluetooth connection to MAC %s" % self.mac)
                self.handle = ventus.connect(self.mac)
                sensorData = ventus.read(self.handle)
                #loginf(sensorData)
            except:
                e = sys.exc_info()[0]
                loginf("could not open BLE connection: %s" % e)
            finally:
                if self.handle is not None:
                    #JW logdbg("close bluetooth connection to %s" % self.mac)
                    ventus.disconnect(self.handle)
                    self.handle = None
                return sensorData


    @staticmethod
    def validate_data(sensorData):
#TODO
        if sensorData and sensorData['indoorTemperature'] is not None:
            return 1
        else:
            return 0

    @staticmethod
    def data_to_packet(data, ts, last_rain=None):
        """Convert raw data to format and units required by weewx.

                        WS820        weewx (metric)
        temperature     degree C     degree C
        humidity        percent      percent
        uv index        unitless     unitless
        pressure        mbar/hPa     mbar
        wind speed      km/h         km/h
        wind dir        0..15 (N->E) degree
        rain            mm           cm
        """

        #JW: logdbg("data received are: %s" % data)
        packet = dict()
        packet['usUnits'] = weewx.METRIC
        packet['dateTime'] = ts
        packet['inTemp'] = data['indoorTemperature']
        packet['inHumidity'] = data['indoorHumidity']
        packet['outTemp'] = data['outdoorTemperature']
        packet['outHumidity'] = data['outdoorHumidity']
        packet['barometer'] = data['airPressure']
        packet['outTempBatteryStatus'] = data['lowBat']

        ws, wd, wso, wsv = (data['windSpeed'], data['windDirection'], 0, 0)
        if wso == 0 and wsv == 0:
                packet['windSpeed'] = ws
                packet['windDir'] = wd*22.5 if packet['windSpeed'] else None
        else:
                loginf('invalid wind reading: speed=%s dir=%s overflow=%s invalid=%s' % (ws, wd, wso, wsv))
                packet['windSpeed'] = None
                packet['windDir'] = None

        packet['windGust'] = None
        packet['windGustDir'] = None

        packet['rainTotal'] = data['rainTotal']
        if packet['rainTotal'] is not None:
                packet['rainTotal'] /= 10.0 # weewx wants cm
        packet['rain'] = weewx.wxformulas.calculate_rain(packet['rainTotal'], last_rain)

        #JW: one could add UV as well
        #packet['UV'] = data['UV']

        #station provides some derived variables
#       packet['rainRate'] = data['rh']
#       if packet['rainRate'] is not None:
#               packet['rainRate'] /= 10 # weewx wants cm/hr
#       packet['dewpoint'] = data['dp']
#       packet['windchill'] = data['wc']

        return packet


class W820ConfEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return 
"""
[W820]
    # This section is for the Ventus W820 weather station.

    # MAC address of bluetooth interface
    mac = ff:ff:ff:ff:ff:ff

    # The driver to use:
    driver = weewx.drivers.ventusw820
"""

    def prompt_for_settings(self):
        print("Specify the MAC address of your W820 bluetooth interface")
        mac = self._prompt('mac', 'ff:ff:ff:ff:ff:ff')
        return {'mac': mac}


# define a main entry point for basic testing of the station without weewx
# engine and service overhead.  invoke this as follows from the weewx root dir:
#
# PYTHONPATH=bin python bin/weewx/drivers/ventusw820.py

if __name__ == '__main__':
    import optparse

    usage = """%prog [options] [--help]"""

    syslog.openlog('ventusw820', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--mac', dest='mac', metavar='MAC',
                      help='MAC address of W820 bluetooth interface',
                      default='')
    (options, args) = parser.parse_args()

    if options.version:
        print("Ventus W820 driver version %s" % DRIVER_VERSION)
        exit(0)

    with Station(options.mac) as s:
        while True:
            print(time.time(), s.get_readings())
