"""Simple data printer example

By default, this script will create a default ADC instance and print any data
it produces to stdout. On first run, the datalog library will copy the default
configuration, "adc.conf", into your operating system's configuration directory.
You can find this directory by opening up a Python console and typing:

> import datalog.adc.config
> datalog.adc.config.AdcConfig.get_config_filepath()

The default configuration uses the "PicoLog24Sim" class, which *simulates* a
PicoLog ADC-24 unit, but generates random values instead of real measurements,
and doesn't require a real unit to be plugged in. If you wish to use a real
unit with this example, change this setting to e.g. "PicoLog24".

Some channels are also already configured in the default configuration. Change
these channels as appropriate.

Sean Leavey
https://github.com/SeanDS/
"""

import time

from datalog.adc.adc import Adc
from datalog.adc.config import AdcConfig
from datalog.data import DataStore

# load ADC with default config
adc = Adc.load_from_config(AdcConfig())

# datastore holding last 1000 readings
datastore = DataStore(1000)

# open ADC
with adc.get_retriever(datastore) as retriever:
    # default last reading time
    last_reading = 0

    while(True):
        # look for new readings
        new_readings = datastore.get_readings(pivot_time=last_reading)

        if len(new_readings):
            # display readings
            for reading in new_readings:
                print(reading)

            # get the last fetched reading's time
            last_reading = new_readings[-1].reading_time

        # sleep for 1 second
        time.sleep(1)
