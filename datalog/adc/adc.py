"""Abstract ADC device classes"""

import logging
import abc
from contextlib import contextmanager

from datalog.device import Device
from .fetch import Retriever

# logger
logger = logging.getLogger("datalog.adc")


class Adc(Device, metaclass=abc.ABCMeta):
    """Represents ADC hardware"""

    def __init__(self, config, *args, **kwargs):
        """Initialises the ADC interface

        :param config: dict-like config object
        """

        super(Adc, self).__init__(*args, **kwargs)

        self.config = config

        # enabled channel numbers
        self.enabled_channels = set()

    @classmethod
    def load_from_config(cls, config):
        """Loads the appropriate ADC class given the settings in the specified \
        config file

        :param config: dict-like config object
        """

        logger.info("Loading ADC driver")

        # import libraries now that they are needed
        # (doing this earlier can lead to circular imports)
        from datalog.adc.hrdl.picolog import PicoLogAdc24, PicoLogAdc24Sim

        if config['adc']['type'] == 'PicoLog24':
            return PicoLogAdc24(config)
        elif config['adc']['type'] == 'PicoLog24Sim':
            return PicoLogAdc24Sim(config)

        ValueError('Unrecognised unit type')

    @contextmanager
    def get_retriever(self, datastore):
        """Get a :class:`Retriever` for the ADC to poll for readings on a \
        regular interval

        :param datastore: :class:`~datalog.data.DataStore` to send readings to
        """
        if not self.is_open():
            self.open()

        # configure device
        self.configure()

        # create the retriever
        retriever = Retriever(self, datastore, self.config)

        # set the context flag to allow it to run
        retriever.context = True

        # start the retriever thread
        retriever.start()

        # yield the retriever inside a try/finally block to handle any
        # unexpected events
        try:
            # return the retriever to the caller
            yield retriever
        finally:
            # stop the thread and wait until it finishes
            retriever.stop()
            logger.debug("Waiting for retriever to stop")
            retriever.join()
            logger.info("Retriever stopped")

            # close the device
            self.close()

    @abc.abstractmethod
    def open(self):
        """Opens unit"""

        return NotImplemented

    @abc.abstractmethod
    def stream(self):
        """Streams from unit"""

        return NotImplemented

    @abc.abstractmethod
    def close(self):
        """Closes unit"""

        return NotImplemented

    @abc.abstractmethod
    def is_open(self):
        """Checks if unit is open"""

        return NotImplemented

    @abc.abstractmethod
    def configure(self):
        """Configures unit"""

        return NotImplemented

    @abc.abstractmethod
    def ready(self):
        """Checks if unit is ready"""

        return NotImplemented

    @abc.abstractmethod
    def get_unit_info(self, info_type):
        """Gets unit info

        :param info_type: info to get
        :type info_type: int
        :return: unit information
        :rtype: string
        """

        return NotImplemented

    @abc.abstractmethod
    def get_formatted_unit_info(self, info_type):
        """Fetches the specified information from the unit, with context

        :return: formatted unit information
        :rtype: string
        """

        return NotImplemented

    @abc.abstractmethod
    def get_full_unit_info(self):
        """Fetches formatted string of all available unit info

        :return: full unit information
        :rtype: string
        """

        return NotImplemented

    @abc.abstractmethod
    def get_last_error_code(self):
        """Fetches the last error code from the unit

        :return: error status code
        :rtype: int
        """

        return NotImplemented

    @abc.abstractmethod
    def get_last_error_message(self):
        """Fetches the last error string from the unit

        :return: error status message
        :rtype: string
        """

        return NotImplemented

    @abc.abstractmethod
    def get_last_settings_error_code(self):
        """Fetches the last settings error code from the unit

        :return: settings error status code
        :rtype: int
        """

        return NotImplemented

    @abc.abstractmethod
    def get_last_settings_error_message(self):
        """Fetches the last settings error string from the unit

        :return: settings error message
        :rtype: string
        """

        return NotImplemented

    @abc.abstractmethod
    def raise_unit_error(self):
        """Checks the unit for errors and settings errors

        :raises Exception: upon discovering an error
        """

        return NotImplemented

    @abc.abstractmethod
    def raise_unit_settings_error(self):
        """Checks the unit for settings error

        :raises Exception: upon discovering a settings error
        """

        return NotImplemented

    @abc.abstractmethod
    def set_analog_in_channel(self, channel, enabled, vrange, itype):
        """Sets analog input channel"""

        return NotImplemented

    @abc.abstractmethod
    def set_sample_time(self, sample_time, conversion_time):
        """Sets sample time"""

        return NotImplemented

    @abc.abstractmethod
    def get_readings(self):
        """Gets readings"""

        return NotImplemented

    @abc.abstractmethod
    def get_enabled_channels_count(self):
        """Gets number of enabled channels

        :return: number of enabled channels
        :rtype: int
        """

        return NotImplemented

    def get_calibration(self, channel):
        """Returns the conversion factor from counts to volts for the
        specified channel

        The conversion factor is in volts per count, so you can get the
        voltage by multiplying this factor by the raw channel counts:
        `voltage = conversion × counts`.

        :param channel: the channel to fetch the conversion factor for
        :type channel: int
        :return: conversion factor
        :rtype: float
        """

        # get minimum and maximum counts for this channel
        _, max_counts = self._get_min_max_adc_counts(channel)

        # get maximum voltage (on a single side of the input)
        v_max = self._get_channel_max_voltage(channel)

        # calculate conversion
        return v_max / max_counts

    def counts_to_volts(self, counts, channel):
        """Converts the specified counts to volts

        :param counts: the counts to convert
        :type counts: int
        :param channel: the channel number this measurements corresponds to
        :type channel: int
        :return: voltage equivalent of counts
        :rtype: float
        """

        # get conversion
        scale = self.get_calibration(channel)

        # return voltages
        return [count * scale for count in counts]

    @abc.abstractmethod
    def _get_min_max_adc_counts(self, channel):
        """Gets minimum and maximum ADC counts"""

        return NotImplemented

    @abc.abstractmethod
    def _get_channel_max_voltage(self, channel):
        """Gets maximum channel voltage"""

        return NotImplemented
