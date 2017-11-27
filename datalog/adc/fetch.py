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

        # retrieval flag
        self.retrieving = False

        # default context flag
        self.context = False

        # time in ms between polls
        poll_time = int(self.config['fetch']['poll_time'])

        if poll_time < 1000:
            # since the runner sleeps for 1s between checks, times less than
            # 1 second aren't supported
            raise ValueError("Poll times less than 1000 ms aren't supported")

        self.poll_time = poll_time
        logger.info("Poll time: {0:.2f} ms".format(self.poll_time))

    def run(self):
        """Starts streaming data from the ADC"""

        if not self.context:
            raise Exception("This can only be run within "
                            "adc.adc.retriever context")

        if not self.adc.is_open():
            raise Exception("Device is not open")

        # start streaming
        self.adc.stream()

        # start time
        self.start_time = int(round(time.time() * 1000))

        # next poll time is now plus the poll time (in ms)
        next_poll_time = int(round(time.time() * 1000)) + self.poll_time

        # set status on
        self.retrieving = True

        # main run loop
        while self.retrieving:
            # time in ms
            now = int(round(time.time() * 1000))

            if now < next_poll_time:
                # sleep, but not for too long so that the thread exits quickly
                # when asked
                time.sleep(1)
            else:
                # fetch latest readings
                self.fetch_readings()

                # set the next poll time
                next_poll_time += self.poll_time

    def fetch_readings(self):
        logger.debug("Polling ADC")

        # check if ADC has values to retrieve
        if not self.adc.ready():
            logger.debug("No new readings")
            return

        # get readings
        readings = self.adc.get_readings()

        # number of readings retrieved
        n_readings = len(readings)

        # make sure readings aren't empty
        if n_readings > 0:
            # store data
            self.datastore.insert(readings)

            logger.debug("Fetched %i readings", n_readings)

    def stop(self):
        """Stops the ADC data stream"""

        # stop retrieving data
        self.retrieving = False
