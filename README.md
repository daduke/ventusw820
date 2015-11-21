Ventus W820 bluetooth driver and weewx connector
================================================

The Ventus W820 is a bluetooth enabled weather station. This repository provides a library to read the values of the sensors and a driver for the [weewx](http://www.weewx.com/) weather station software 

The library requires [bluepy](https://github.com/IanHarvey/bluepy) for the BLE communication 

Project website: [http://daduke.org/code/ventus.html](http://daduke.org/code/ventus.html)

How to use it:
  * install [bluepy](https://github.com/IanHarvey/bluepy)
  * `ventus.py` is the low level library that talks to the weather station, copy it to a standard python library path (e.g. `/usr/local/lib/python2.7/site-packages/`
  * `ventusw820.py` is the weewx driver, it goes into the weewx driver directory
  * define your Ventus station in the weewx config file:
```
[W820]
    # This section is for the Ventus W820 weather station.

    # MAC address of bluetooth interface
    mac = <your W820 bluetooth MAC address goes here>

    # The driver to use:
    driver = weewx.drivers.ventusw820

    polling_interval = 60
```
  * define your default station as a W820:
```
station_type = W820
```

that's it! Contact me if you have any questions.
