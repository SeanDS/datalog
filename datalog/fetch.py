from __future__ import division

import time
import threading
import logging
from configparser import ConfigParser

"""Data retrieval from ADC unit"""

class RetrieverConfig(ConfigParser):
    def __init__(self, *args, **kwargs):
        super(RetrieverConfig, self).__init__(*args, **kwargs)

        # retriever settings
        self['retriever'] = {}
        # time to wait between ADC polls (ms)
        self['retriever']['poll_rate'] = '3000'

class Retriever(threading.Thread):
    """Class to retrieve data from an ADC and insert it into a datastore"""

    def __init__(self, adc, datastore, config=None):
        """Initialises the retriever

        :param adc: the ADC object to retrieve data from
        :param datastore: the datastore to store data in
        """

        # initialise threading
        threading.Thread.__init__(self)

        self.config = RetrieverConfig()

        if config is not None:
            if isinstance(config, collections.Mapping):
                # merge config dict into config
                logging.getLogger("fetcher").debug("Merging provided dict into "
                                                "config")
                self.config.read_dict(config)
            else:
                # parse provided config file(s)
                logging.getLogger("fetcher").debug("Merging provided file(s) "
                                                "into config")
                self.config.read(config)

        # store parameters
        self.adc = adc
        self.datastore = datastore

    def run(self):
        """Starts streaming data from the ADC"""

        # start time
        self.start_time = int(round(time.time() * 1000))

        # default next poll time
        self._next_poll_time = self.start_time

        # time between polls
        poll_rate = int(self.config['retriever']['poll_rate'])

        with self.adc:
            # start streaming from ADC
            self.adc.stream()

            # set status on
            self.retrieving = True

            # get the logger
            logger = logging.getLogger("fetcher")

            # main run loop
            while self.retrieving:
                # time in ms
                current_time = int(round(time.time() * 1000))

                # ms since start
                time_since_start = current_time - self.start_time

                if current_time < self._next_poll_time:
                    # skip this loop
                    continue

                logger.debug("+{0} polling ADC".format(time_since_start))

                # check if ADC has values to retrieve
                if self.adc.readings_available():
                    # get readings
                    readings = self.adc.get_readings()

                    # number of readings retrieved
                    n_readings = len(readings)

                    # make sure readings aren't empty
                    if n_readings > 0:
                        # store data
                        self.datastore.insert(readings)

                        logger.debug("Fetched {0} readings".format(n_readings))

                        print(readings)

                # set the next poll time
                self._next_poll_time += poll_rate

                # sleep for the difference between now and then, minus some processing time
                sleep_time = 0.001 * (self._next_poll_time \
                            - int(round(time.time() * 1000)) \
                            - 20) # some ms for the processing of this expression

                # don't sleep unless we have to
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def stop(self):
        """Stops the ADC data stream"""

        # stop retrieving data
        self.retrieving = False
