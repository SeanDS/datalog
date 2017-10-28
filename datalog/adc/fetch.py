"""Data retrieval from ADC unit"""

import time
import threading
import logging

# logger
logger = logging.getLogger("datalog.fetch")


class Retriever(threading.Thread):
    """Class to retrieve data from an ADC and insert it into a datastore"""

    def __init__(self, adc, datastore, config):
        """Initialises the retriever

        :param adc: the ADC object to retrieve data from
        :param datastore: the datastore to store data in
        :param config: configuration class
        """

        # initialise threading
        threading.Thread.__init__(self)

        self.config = config

        # store parameters
        self.adc = adc
        self.datastore = datastore

        # default start time
        self.start_time = None

        # default next poll time
        self._next_poll_time = None

        # retrieval flag
        self.retrieving = False

        # default context flag
        self.context = False

    def run(self):
        """Starts streaming data from the ADC"""

        if not self.context:
            raise Exception("This can only be run within "
                            "adc.adc.retriever context")

        if not self.adc.is_open():
            raise Exception("Device is not open")

        # time between polls
        poll_time = int(self.config['fetch']['poll_time'])
        logger.info("Poll time: {0:.2f} ms".format(poll_time))

        # start streaming
        self.adc.stream()

        # start time
        self.start_time = int(round(time.time() * 1000))

        # default next poll time
        self._next_poll_time = self.start_time

        # set status on
        self.retrieving = True

        # main run loop
        while self.retrieving:
            # time in ms
            current_time = int(round(time.time() * 1000))

            # ms since start
            time_since_start = current_time - self.start_time

            if current_time < self._next_poll_time:
                # skip this loop
                continue

            logger.debug("+%i polling ADC", time_since_start)

            # check if ADC has values to retrieve
            if self.adc.ready():
                # get readings
                readings = self.adc.get_readings()

                # number of readings retrieved
                n_readings = len(readings)

                # make sure readings aren't empty
                if n_readings > 0:
                    # store data
                    self.datastore.insert(readings)

                    logger.debug("Fetched %i readings", n_readings)

            # set the next poll time
            self._next_poll_time += poll_time

    def stop(self):
        """Stops the ADC data stream"""

        # stop retrieving data
        self.retrieving = False
