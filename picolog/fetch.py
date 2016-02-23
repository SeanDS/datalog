from __future__ import division

import time
import threading

"""Data retrieval from ADC unit"""

class Retriever(threading.Thread):
    """Class to retrieve data from an ADC and insert it into a datastore"""

    """The connected ADC"""
    _adc = None

    """The connected datastore"""
    _datastore = None

    """Retrieval status"""
    retrieving = None

    def __init__(self, adc, datastore):
        # call thread init
        threading.Thread.__init__(self)

        # store parameters
        self._adc = adc
        self._datastore = datastore

    def start(self):
        """Starts streaming data from the ADC"""

        # calculate the fetch delay, just a bit longer than the total sample time
        fetch_delay = (self._adc.sample_time + 0.001) / 1000 # 1ms delay

        # set status on
        self.retrieving = True

        # main run loop
        while self.retrieving:
            # check if ADC has values to retrieve
            if self._adc.ready():
                # get readings
                readings = adc.get_readings()

                # make sure readings aren't empty
                if readings:
                    # store data
                    self._datastore.insert(readings)

            # wait until next samples should be ready
            time.sleep(fetch_delay)

    def stop(self):
        """Stops the ADC data stream"""

        # stop retrieving data
        self.retrieving = False
