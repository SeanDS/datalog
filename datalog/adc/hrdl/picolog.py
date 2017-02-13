import sys
import time
import logging
from configparser import ConfigParser
import ctypes
import collections
import random

from datalog.adc.device import AbstractHwLib
from datalog.data import Reading
from datalog.adc.hrdl.constants import Handle, Channel, Status, Info, \
Error, SettingsError, Progress, VoltageRange, InputType, ConversionTime, \
SampleMethod


class PicoLogAdcLib(AbstractHwLib):
    NUM_CHANNELS = 16
    DEFAULT_CHANNEL_VOLTAGE = VoltageRange.RANGE_MAX
    DEFAULT_CHANNEL_TYPE = InputType.SINGLE

    def __init__(self, config, *args, **kwargs):
        # call parent
        super(PicoLogAdcLib, self).__init__(*args, **kwargs)

        self.config = config

        # default handle
        self._c_handle = None

        # string, times and values buffers
        self.str_buf = ctypes.create_string_buffer( \
                        int(self.config['unit']['str_buf_len']))
        self.sample_times = (ctypes.c_long \
                            * int(self.config['unit']['sample_buf_len']))()
        self.sample_values = (ctypes.c_long \
                            * int(self.config['unit']['sample_buf_len']))()

        # default channel voltages
        self.channel_voltages = {i: self.DEFAULT_CHANNEL_VOLTAGE \
                                for i in range(1, self.NUM_CHANNELS + 1)}
        self.channel_types = {i: self.DEFAULT_CHANNEL_VOLTAGE \
                                for i in range(1, self.NUM_CHANNELS + 1)}

        # load library
        self._load_library()

    def _load_library(self):
        # load library
        self.library = ctypes.CDLL( \
                        self.config['picolog_lib_paths']['adc24'])

        logging.getLogger("adc").debug("C library for unit loaded")

    def open(self):
        """Opens the PicoLog unit for communication"""

        if self._c_handle is not None:
            raise Exception("Only one PicoLog unit can be opened at a time")

        # open unit and store handle as C short
        self._c_handle = int(self.library.HRDLOpenUnit())

        if not Handle.is_valid_handle(self._c_handle):
            if self._c_handle is Handle.UNIT_NOT_FOUND:
                raise Exception('Unit not found')
            elif self._c_handle is Handle.UNIT_NOT_OPENED:
                raise Exception('Unit found but not opened')
            else:
                raise Exception('Unknown invalid handle status')

        logging.getLogger("adc").info("Unit opened")

    def close(self):
        """Closes the currently open PicoLog unit"""

        if self._c_handle is None:
            raise Exception("No PicoLog unit is currently open")

        # close, recording status
        status = int(self.library.HRDLCloseUnit(self._c_handle))

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # reset handle
        self._c_handle = None

        logging.getLogger("adc").info("Unit closed")

    def configure(self):
        # set the sample rates
        self.set_sample_time(int(self.config['unit']['sample_time']), \
            int(self.config['unit']['conversion_time']))

        # TODO: set up the channels properly
        self.set_analog_in_channel(
            11,
            True,
            VoltageRange.RANGE_2500_MV,
            InputType.SINGLE)

    def is_open(self):
        """Checks if the unit is open"""
        return self._c_handle is not None

    def ready(self):
        """Checks if the unit has readings ready to be retrieved

        Note: this function cannot distinguish between a "not ready" message and
        an invalid handle. They both return False.

        :return: ready status
        """

        return int(self.library.HRDLReady(self._c_handle))

    def get_unit_info(self, info_type):
        """Fetches the specified information from the unit

        :param info_type: the :class:`~picolog.constants.Status` \
        constant to retrieve
        :return: specified information string
        """

        logging.getLogger("adc").debug("Getting unit info")

        # validate info type
        info_type = int(info_type)

        # check info type validity
        if not Info.is_valid_constant(info_type):
            raise Exception('Invalid info constant')

        # get unit info, returning number of characters written to buffer
        length = int(self.library.HRDLGetUnitInfo(self._c_handle, \
                 ctypes.pointer(self.str_buf), \
                 ctypes.c_short(len(self.str_buf)), \
                 info_type))

        # length is zero if one of the parameters specified in the function call
        # above is out of range, or a null message pointer is specified
        if length is 0:
            raise Exception('Info type out of range or null message pointer')
        elif length >= len(self.str_buf):
            logging.getLogger("adc").warning("Buffer length reached or exceeded")

        # extract and return string from buffer
        return str(self.str_buf.value[:length])

    def get_formatted_unit_info(self, info_type):
        """Fetches the specified information from the unit, with context

        :return: formatted information string
        """

        return Info.format(self.get_unit_info(info_type), info_type)

    def get_full_unit_info(self):
        """Fetches formatted string of all available unit info

        :return: full unit information string
        """

        # get all unit info as a list
        info = map(self.get_formatted_unit_info, Info.get_info_constants())

        # reduce list to string
        return "\n".join(info)

    def get_last_error_code(self):
        """Fetches the last error code from the unit

        :return: error status code
        """

        # cast error into int and return
        return int(self.get_unit_info(Info.ERROR))

    def get_last_error_message(self):
        """Fetches the last error string from the unit

        :return: error status string
        """

        # look up and return corresponding error code message
        return Error.get_error_string(self.get_last_error_code())

    def get_last_settings_error_code(self):
        """Fetches the last settings error code from the unit

        :return: settings error status code
        """

        # cast settings error into int and return
        return int(self.get_unit_info(Info.SETTINGS_ERROR))

    def get_last_settings_error_message(self):
        """Fetches the last settings error string from the unit

        :return: settings error string
        """

        # look up and return corresponding settings error code message
        return SettingsError.get_error_string(self.get_last_settings_error_code())

    def raise_unit_error(self):
        """Checks the unit for errors and settings errors

        :raises Exception: upon discovering an error
        """

        logging.getLogger("adc").debug("Checking for error")

        # check for errors
        error = self.get_last_error()

        if Error.is_error(error):
            raise Exception("Error: {0}".format(Error.get_error_string(error)))

    def raise_unit_settings_error(self):
        """Checks the unit for settings error

        :raises Exception: upon discovering a settings error
        """

        logging.getLogger("adc").debug("Checking for settings error")

        # check for settings errors
        settings_error = self.get_last_settings_error()

        if SettingsError.is_error(settings_error):
            raise Exception("Settings error: {0}".format( \
                            SettingsError.get_error_string(settings_error)))

    def set_analog_in_channel(self, channel, enabled, vrange, itype):
        """Sets the specified channel to be an analog input

        :param channel: channel number to set
        :param enabled: whether channel is enabled or not
        :param vrange: voltage range to use for this channel
        :param itype: input type, single ended or differential
        :raises Exception: when channel is invalid, or voltage range is \
        invalid, or input type is invalid
        """

        logging.getLogger("adc").debug("Setting analog input channel")

        # check validity of channel
        if not Channel.is_valid(channel):
            raise Exception("Invalid channel specified")

        # check validity of range
        if not VoltageRange.is_valid(vrange):
            raise Exception("Invalid voltage range specified")

        # check validity of input type
        if not InputType.is_valid(itype):
            raise Exception("Invalid input type")

        # change enabled to integer
        enabled = int(enabled)

        vrange = int(vrange)
        itype = int(itype)

        # print warning to user if differential input is specified on an even
        # channel
        if itype is InputType.DIFFERENTIAL and channel % 2 == 0:
            logging.getLogger("adc").warning("Setting a differential input on "
            "a secondary channel is not possible. Instead set the input on the"
            " primary channel number.")

        # set the channel
        status = int( \
            self.library.HRDLSetAnalogInChannel(self._c_handle, \
            ctypes.c_short(channel), ctypes.c_short(enabled), \
            ctypes.c_short(vrange), ctypes.c_short(itype)))

        # check return status
        if not Status.is_valid_status(status):
            # channel setting failed
            self.raise_unit_settings_error()

        # add channel to enabled set
        self.enabled_channels.update([channel])

        # set the channel voltage dict
        self.channel_voltages[channel] = vrange
        self.channel_types[channel] = itype

        logging.getLogger("adc").debug("Analog input channel {0} set to "
            "enabled={1}, vrange={2}, type={3}".format(channel, enabled,
            vrange, itype))

    def set_sample_time(self, sample_time, conversion_time):
        """Sets the time the unit can take to sample all active inputs.

        The sample_time must be large enough to allow all active channels to
        convert sequentially, i.e.

            sample_time > conversion_time * active_channels

        where active_channels can be obtained from
        `~picolog.hrdl.adc.get_enabled_channels_count`

        :param sample_time: the time in milliseconds the unit has to sample \
        all active inputs
        :param conversion_time: the time a single channel has to sample its \
        input
        """

        sample_time = int(sample_time)

        # check validity of conversion time
        if not ConversionTime.is_valid(conversion_time):
            raise Exception("Invalid conversion time")

        # set sample time
        status = int(self.library.HRDLSetInterval(self._c_handle, \
            ctypes.c_long(sample_time), ctypes.c_short(conversion_time)))

        # check return status
        if not Status.is_valid_status(status):
            # setting failure
            self.raise_unit_settings_error()

        # save sample time
        self.sample_time = sample_time

        logging.getLogger("adc").debug("Sample time set to {0}, conversion "
            "time set to {1}".format(sample_time, conversion_time))

    def _run(self, sample_method):
        """Runs the unit recording functionality

        :param sample_method: sampling method
        :raises Exception: if sample_method is invalid or if run failed
        """

        # check validity of sample method
        if not SampleMethod.is_valid(sample_method):
            raise Exception("Invalid sample method")

        # run
        status = int(
            self.library.HRDLRun(
                self._c_handle,
                ctypes.c_long(int(self.config['unit']['sample_buf_len'])),
                ctypes.c_short(sample_method)
            ))

        # check return status
        if not Status.is_valid_status(status):
            # run failure
            self.raise_unit_error()

    def stream(self):
        """Streams data from the unit"""

        logging.getLogger("adc").info("Starting unit streaming")

        # run stream
        self._run(SampleMethod.STREAM)

        # save timestamp
        self.stream_start_timestamp = int(round(time.time() * 1000))

    def get_readings(self):
        """Fetches uncollected ADC readings

        A reading is a full set of channel samples for a given time. This method
        returns a list of readings, in chronological order.
        """

        # get payload
        (times, samples) = self._get_payload()

        # empty list of readings
        readings = []

        # loop over times, adding readings
        for time, data in zip(times, samples):
            time = int(time)
            data = list(data)

            if len(data) == 0:
                # empty data
                break

            # convert time from ms since stream start to UNIX timestamp (in ms)
            real_time = self.stream_start_timestamp + time

            readings.append(Reading(real_time, self.enabled_channels, data))

        return readings

    def _get_payload(self):
        """Fetches uncollected sample payload from the unit"""

        # calculate number of values to collect for each channel
        samples_per_channel = int(self.config['unit']['sample_buf_len']) \
                            // len(self.enabled_channels)

        # get samples, without using the overflow short parameter (None == NULL)
        num_values = int(
            self.library.HRDLGetTimesAndValues(self._c_handle,
                ctypes.pointer(self.sample_times),
                ctypes.pointer(self.sample_values),
                None,
                ctypes.c_long(samples_per_channel)
            ))

        # check return status
        if num_values is 0:
            raise Exception("Call failed or no values available")

        # convert times and values into Python lists
        raw_times, raw_values = self._sample_lists(num_values)

        # empty lists for cleaned up times and samples
        times = []
        values = []

        # number of active channels
        channel_count = len(self.enabled_channels)

        # loop over at least the first time and samples set (the first time can be zero,
        # next entries cannot be)
        for i in range(len(raw_times)):
            # break when first zero time after first is found
            if i > 0 and raw_times[i] == 0:
                break

            # add time to list
            times.append(raw_times[i])

            # start index
            i_start = i * channel_count

            # end index
            i_end = i_start + channel_count

            # add samples from each channel
            values.append(raw_values[i_start:i_end])

        # check last value of i - if it's near the buffer length, we need
        # to be very careful because wrapping might have occurred
        if i >= int(self.config['unit']['sample_buf_len']) - 1:
            # raise a warning
            logging.getLogger("adc").warning("The sample buffer length ({0}) "
                "has been reached for sample(s) received beginning at time "
                "{1}".format(int(self.config['unit']['sample_buf_len']), times[-1]))

        return times, values

    def _sample_lists(self, num_values):
        """Converts time and value C buffers into Python lists"""

        # convert to list and return
        # NOTE: the conversion from c_long elements to ints is done by the slice operation
        times = [int(i) for i in self.sample_times[:num_values]]
        values = [int(i) for i in self.sample_values[:num_values]]

        return times, values

    def get_enabled_channels_count(self):
        """Fetches the number of channels enabled in the unit

        :return: number of enabled channels
        """

        logging.getLogger("adc").debug("Fetching enabled channel count")

        # C short to store number of channels
        enabled_channels = ctypes.c_short()

        # get enabled channel count
        status = int( \
            self.library.HRDLGetNumberOfEnabledChannels( \
                self._c_handle, \
                ctypes.pointer(enabled_channels) \
            ))

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # return enabled channels
        return int(enabled_channels.value)

    def _get_channel_max_voltage(self, channel):
        """Returns the maximum voltage input for the specified channel

        :param channel: the channel to get the maximum voltage for
        :return: voltage range of specified channel
        :raises Exception: if the specified channel is not enabled or invalid
        """

        channel = int(channel)

        # return voltage
        return VoltageRange.get_max_voltage(self.channel_voltages[channel])

    def _get_min_max_adc_counts(self, channel):
        """Fetches the minimum and maximum ADC counts available for the \
        connected device.

        Note: the documentation from Pico is wrong regarding this function. The
        order in which the variables holding the  minimum and maximum ADC counts
        are referenced is swapped.

        :param channel: the channel number to fetch the counts for
        :return: minimum and maximum ADC counts for the specified channel
        """

        logging.getLogger("adc").debug("Fetching min/max ADC counts for "
            "channel {0}".format(channel))

        # C long for minimum ADC count
        minimum = ctypes.c_long()

        # C long for maximum ADC count
        maximum = ctypes.c_long()

        # get minimum and maximum counts
        status = int(
            self.library.HRDLGetMinMaxAdcCounts( \
                self._c_handle, ctypes.pointer(minimum), \
                ctypes.pointer(maximum), \
                ctypes.c_short(channel) \
            ))

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # return channel ADC counts
        return (int(minimum.value), int(maximum.value))

class PicoLogAdcLibSim(PicoLogAdcLib):
    """Represents a simulated :class:`PicoLogAdcLib`."""

    # maximum string buffer (guess)
    MAX_BUF_LEN = 2 ** 32 / 2 - 1

    # maximum sample time in ms (guess)
    MAX_SAMPLE_TIME = 16000

    # count range
    MIN_COUNT = 0
    MAX_COUNT = 2 ** 24 - 1

    def __init__(self,  *args, **kwargs):
        # call parent
        super(PicoLogAdcLibSim, self).__init__(*args, **kwargs)

        # fake samples buffers
        self._fake_samples_time_buf = []
        self._fake_samples_value_buf = []

        # default settings error
        self._settings_error_code = SettingsError.OK

        # default sample time
        self.sample_time = None

        logging.getLogger("adc").debug("Fake library loaded")

    def _load_library(self):
        # do nothing!
        logging.getLogger("adc").debug("Fake C library for unit loaded")

    def open(self):
        """Opens the PicoLog unit for communication"""

        if self._c_handle is not None:
            raise Exception("Only one PicoLog unit can be opened at a time")

        # open unit and store handle as C short
        self._c_handle = 999

        logging.getLogger("adc").info("Fake unit opened")

    def close(self):
        """Closes the currently open PicoLog unit"""

        if self._c_handle is None:
            raise Exception("No PicoLog unit is currently open")

        # reset handle
        self._c_handle = None

        logging.getLogger("adc").info("Unit closed")

    def configure(self):
        # set the sample rates
        self.set_sample_time(int(self.config['unit']['sample_time']), \
            int(self.config['unit']['conversion_time']))

        # TODO: set up the channels properly
        self.set_analog_in_channel(
            1,
            True,
            VoltageRange.RANGE_2500_MV,
            InputType.SINGLE)

    def ready(self):
        """Checks if the unit has readings ready to be retrieved"""

        # generate fake samples
        self._generate_fake_samples()

        return len(self._fake_samples_time_buf) > 0

    def _generate_fake_samples(self):
        """Generates fake samples to cover the time since the last data \
        retrieval"""

        # last retrieved sample time
        last_request_time = self._last_fake_request_time

        # time between start and first sample in this payload
        start_offset = last_request_time - self.stream_start_timestamp

        # current time
        current_time = int(round(time.time() * 1000))

        # time since last call
        elapsed_time = current_time - last_request_time

        # number of sample times since then
        num_samples = elapsed_time // self.sample_time

        if num_samples == 0:
            return

        # generate fake samples
        self._fake_samples_time_buf.extend( \
            [start_offset + self.sample_time * t for t in range(num_samples)])
        self._fake_samples_value_buf.extend( \
            [[int(random.uniform(self.MIN_COUNT, self.MAX_COUNT)) for i in \
            range(self.get_enabled_channels_count())] for j in range(num_samples)])

        # reset stopwatch
        self._last_fake_request_time = last_request_time \
                                    + num_samples * self.sample_time

    def get_unit_info(self, info_type):
        """Fetches the specified information from the unit

        :param info_type: the :class:`~picolog.constants.Status` \
        constant to retrieve
        :return: specified information string
        """

        logging.getLogger("adc").debug("Getting fake unit info")

        # validate info type
        info_type = int(info_type)

        # check info type validity
        if not Info.is_valid_constant(info_type):
            raise Exception('Invalid info constant')

        # return info
        # examples from hardware manual
        if info_type == Info.DRIVER_VERSION:
            return "1.0.0.1"
        elif info_type == Info.USB_VERSION:
            return "1.1"
        elif info_type == Info.HARDWARE_VERSION:
            return "1"
        elif info_type == Info.VARIANT_INFO:
            return "24"
        elif info_type == Info.BATCH_AND_SERIAL:
            return "CMY02/116"
        elif info_type == Info.CAL_DATE:
            return "09Sep05"
        elif info_type == Info.KERNEL_DRIVER_VERSION:
            # weirdly, there is no example given in manual, so just return a
            # made-up value
            return "1"
        elif info_type == Info.ERROR:
            # nothing relevant to return other than OK
            return Error.OK
        elif info_type == Info.SETTINGS_ERROR:
            return self._settings_error_code

    def set_analog_in_channel(self, channel, enabled, vrange, itype):
        """Sets the specified channel to be an analog input

        :param channel: channel number to set
        :param enabled: whether channel is enabled or not
        :param vrange: voltage range to use for this channel
        :param itype: input type, single ended or differential
        :raises Exception: when channel is invalid, or voltage range is \
        invalid, or input type is invalid
        """

        channel = int(channel)
        vrange = int(vrange)
        itype = int(itype)

        # check validity of channel
        if not Channel.is_valid(channel):
            raise Exception("Invalid channel specified")

        # check validity of range
        if not VoltageRange.is_valid(vrange):
            raise Exception("Invalid voltage range specified")

        # check validity of input type
        if not InputType.is_valid(itype):
            raise Exception("Invalid input type")

        # print warning to user if differential input is specified on an even
        # channel
        if itype is InputType.DIFFERENTIAL and channel % 2 == 0:
            logging.getLogger("adc").warning("Setting a differential input on "
            "a secondary channel is not possible. Instead set the input on the"
            " primary channel number.")

        # set the channel
        if enabled:
            self.enabled_channels.update([channel])
            self.channel_voltages[channel] = vrange
            self.channel_types[channel] = itype

        logging.getLogger("adc").debug("Analog input channel {0} set to "
            "enabled={1}, vrange={2}, type={3}".format(channel, enabled,
            vrange, itype))

    def set_sample_time(self, sample_time, conversion_time):
        logging.getLogger("adc").debug("Setting fake sample and conversion times")

        sample_time = int(sample_time)

        # check validity of conversion time
        if not ConversionTime.is_valid(conversion_time):
            raise Exception("Invalid conversion time")

        # get conversion time in ms
        conversion_time_ms = ConversionTime.get_conversion_time(conversion_time)

        # samples must be able to be made within the total sample time
        if self.get_enabled_channels_count() * conversion_time_ms \
            > sample_time:
            # settings error
            self._settings_error_code = SettingsError.CONVERSION_TIME_TOO_SLOW
            status = 0
        # sample time must not be out of range
        elif sample_time > self.MAX_SAMPLE_TIME:
            self._settings_error_code = SettingsError.SAMPLE_INTERVAL_OUT_OF_RANGE
            status = 0
        else:
            # success
            self._settings_error_code = SettingsError.OK
            status = 1

        # check return status
        if not Status.is_valid_status(status):
            # setting failure
            self.raise_unit_settings_error()

        # save sample and conversion times
        self.sample_time = sample_time
        self.conversion_time = conversion_time_ms

        logging.getLogger("adc").debug("Fake sample time set to {0}, conversion "
            "time set to {1}".format(sample_time, conversion_time_ms))

    def stream(self):
        """Streams data from the unit"""

        if self.sample_time is None:
            raise Exception("Sample time not set")

        logging.getLogger("adc").info("Starting fake unit streaming")

        if int(self.config['unit']['sample_buf_len']) > self.MAX_BUF_LEN:
            # sample buffer length out of range
            self._settings_error_code = SettingsError.INVALID_PARAMETER
            self.raise_unit_error()

        # save timestamp
        self.stream_start_timestamp = int(round(time.time() * 1000))

        # time to use for readings
        self._last_fake_request_time = self.stream_start_timestamp

    def _get_payload(self):
        """Fetches uncollected sample payload from the unit"""

        # copy the fake samples and times
        times = list(self._fake_samples_time_buf)
        values = list(self._fake_samples_value_buf)

        # reset buffers
        self._fake_samples_time_buf = []
        self._fake_samples_value_buf = []

        return times, values

    def get_enabled_channels_count(self):
        return len(self.enabled_channels)

    def _get_min_max_adc_counts(self, channel):
        return self.MIN_COUNT, self.MAX_COUNT

    def _get_channel_max_voltage(self, channel):
        channel = int(channel)

        return VoltageRange.get_max_voltage(self.channel_voltages[channel])
