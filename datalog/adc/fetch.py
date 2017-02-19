import time
import threading
import logging
from configparser import ConfigParser

"""Data retrieval from ADC unit"""

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

        # default context flag
        self._context = False

    def run(self):
        """Starts streaming data from the ADC"""

        # get an instance of the logger
        logger = logging.getLogger("retriever")

        if not self._context:
            raise Exception("This can only be run within "
                            "adc.device.retriever context")

        if not self.adc.is_open():
            raise Exception("Device is not open")

        # time between polls
        poll_rate = int(self.config['fetch']['poll_rate'])
        logger.info("Poll rate: {0:.2f} ms".format(poll_rate))

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

            logger.debug("+{0} polling ADC".format(time_since_start))

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

            #if time_since_start > 100000:
                # temporary hack: exit after 100 seconds
                #logger.debug("Exiting after 100s")
                #self.retrieving = False

    def stop(self):
        """Stops the ADC data stream"""

        # stop retrieving data
        self.retrieving = False
