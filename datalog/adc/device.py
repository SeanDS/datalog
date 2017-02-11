import logging
import abc
from configparser import ConfigParser
from contextlib import contextmanager
import collections

from datalog.data import Reading
from datalog.adc.fetch import Retriever

class Adc(object):
    """Represents ADC hardware"""

    def __init__(self, config):
        """Initialises the ADC interface

        :param config: path to config file, or list of paths to config files, \
        which will be parsed to provide contextual settings
        """

        self.config = config

        # load ADC library
        self._load_library()

    def _load_library(self):
        """Loads the ADC unit library, either hardware or emulated"""

        logging.getLogger("adc").info("Loading ADC driver")

        # import libraries now that they are needed
        # (doing this earlier can lead to circular imports)
        from datalog.adc.hrdl.picolog import PicoLogAdcLib, PicoLogAdcLibSim

        if self.config['unit']['type'] == 'PicoLog24':
            self.library = PicoLogAdcLib(self.config)
        elif self.config['unit']['type'] == 'PicoLog24Sim':
            self.library = PicoLogAdcLibSim(self.config)
        else:
            raise ValueError('Unrecognised unit type')

    def is_open(self):
        return self.library.is_open()

    @contextmanager
    def retriever(self, datastore):
        if not self.is_open():
            self.library.open()

        # create the retriever
        retriever = Retriever(self, datastore, self.config)

        # set the context flag to allow it to run
        retriever._context = True

        # start the retriever thread
        retriever.start()

        # return the retriever to the caller
        yield retriever

        # stop the thread and wait until it finishes
        retriever.stop()
        logging.getLogger("device").debug("Waiting for retriever to stop")
        retriever.join()
        logging.getLogger("device").info("Retriever stopped")

        # close the device
        self.library.close()

    def stream(self):
        self.library.configure()

        # start stream
        self.library.stream()

    def readings_available(self):
        return self.library.ready()

    def get_readings(self):
        return self.library.get_readings()

class AbstractHwLib(object, metaclass=abc.ABCMeta):
    """Required interfaces for ADC hardware or emulated software"""

    def __init__(self):
        # enabled channel numbers
        self.enabled_channels = set()

    @abc.abstractmethod
    def open(self):
        raise NotImplemented()

    @abc.abstractmethod
    def close(self):
        raise NotImplemented()

    @abc.abstractmethod
    def is_open(self):
        raise NotImplemented()

    @abc.abstractmethod
    def configure(self):
        raise NotImplemented()

    @abc.abstractmethod
    def ready(self):
        raise NotImplemented()

    @abc.abstractmethod
    def get_unit_info(self, info_type):
        raise NotImplemented()

    @abc.abstractmethod
    def get_formatted_unit_info(self, info_type):
        """Fetches the specified information from the unit, with context

        :return: formatted information string
        """
        raise NotImplemented()

    @abc.abstractmethod
    def get_full_unit_info(self):
        """Fetches formatted string of all available unit info

        :return: full unit information string
        """
        raise NotImplemented()

    @abc.abstractmethod
    def get_last_error_code(self):
        """Fetches the last error code from the unit

        :return: error status code
        """
        raise NotImplemented()

    @abc.abstractmethod
    def get_last_error_message(self):
        """Fetches the last error string from the unit

        :return: error status string
        """
        raise NotImplemented()

    @abc.abstractmethod
    def get_last_settings_error_code(self):
        """Fetches the last settings error code from the unit

        :return: settings error status code
        """
        raise NotImplemented()

    @abc.abstractmethod
    def get_last_settings_error_message(self):
        """Fetches the last settings error string from the unit

        :return: settings error string
        """
        raise NotImplemented()

    @abc.abstractmethod
    def raise_unit_error(self):
        """Checks the unit for errors and settings errors

        :raises Exception: upon discovering an error
        """
        raise NotImplemented()

    @abc.abstractmethod
    def raise_unit_settings_error(self):
        """Checks the unit for settings error

        :raises Exception: upon discovering a settings error
        """
        raise NotImplemented()

    @abc.abstractmethod
    def set_analog_in_channel(self, channel, enabled, vrange, itype):
        raise NotImplemented()

    @abc.abstractmethod
    def set_sample_time(self, sample_time, conversion_time):
        raise NotImplemented()

    @abc.abstractmethod
    def stream(self):
        raise NotImplemented()

    @abc.abstractmethod
    def get_readings(self):
        raise NotImplemented()

    @abc.abstractmethod
    def get_enabled_channels_count(self):
        raise NotImplemented()

    def get_calibration(self, channel):
        """Returns the conversion factor from counts to volts for the
        specified channel

        The conversion factor is in volts per count, so you can get the
        voltage by multiplying this factor by the raw channel counts:

            volts = conversion * counts

        :param channel: the channel to fetch the conversion factor for
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
        :param channel: the channel number this measurements corresponds to
        :return: voltage equivalent of counts
        """

        # get conversion
        scale = self.get_calibration(channel)

        # return voltages
        return [count * scale for count in counts]

    @abc.abstractmethod
    def _get_min_max_adc_counts(self, channel):
        raise NotImplemented()

    @abc.abstractmethod
    def _get_channel_max_voltage(self, channel):
        raise NotImplemented()
