"""Example of a network-accessible PicoLog ADC

By default, this uses the fake PicoLog ADC24 driver.
"""

import logging

from datalog.adc.config import AdcConfig
from datalog.adc.adc import Adc
from datalog.data import DataStore
from datalog.network import run_server

# configure logging output
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(name)-16s - %(levelname)-10s - %(message)s'))
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# fetch configuration
config = AdcConfig()

# override config to use fake server
config["adc"]["type"] = "PicoLog24Sim"

# create ADC device
adc = Adc.load_from_config(config)

# create datastore with storage for 1000 readings
datastore = DataStore(1000)

# get retriever context
with adc.get_retriever(datastore) as retriever:
    # start server
    run_server(datastore)
