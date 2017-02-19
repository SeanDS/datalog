"""Abstract ADC device classes"""

import logging
import abc
from contextlib import contextmanager

from datalog.device import Device
from datalog.data import Reading
from .fetch import Retriever


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

        logging.getLogger("adc").info("Loading ADC driver")

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
        retriever._context = True

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
            logging.getLogger("adc").debug("Waiting for retriever to stop")
            retriever.join()
            logging.getLogger("adc").info("Retriever stopped")

            # close the device
            self.close()

    @abc.abstractmethod
    def open(self):
        raise NotImplemented()

    @abc.abstractmethod
    def stream(self):
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
