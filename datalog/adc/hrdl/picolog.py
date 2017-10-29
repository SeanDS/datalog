"""PicoLog driver wrappers"""

import time
import logging
import ctypes
import random

from datalog.adc.adc import Adc
from datalog.data import Reading
from .constants import Handle, Channel, Status, Info, Error, SettingsError, \
                       VoltageRange, InputType, ConversionTime, SampleMethod

# logger
logger = logging.getLogger("datalog.picolog")


class PicoLogAdc24(Adc):
    """PicoLog ADC24 driver wrapper"""

    NUM_CHANNELS = 16
    DEFAULT_CHANNEL_VOLTAGE = VoltageRange.RANGE_MAX
    DEFAULT_CHANNEL_TYPE = InputType.SINGLE

    def __init__(self, config, *args, **kwargs):
        """Instantiate a PicoLogAdc24

        :param config: configuration object
        :type config: :class:`~datalog.adc.config`
        """

        # call parent
        super(PicoLogAdc24, self).__init__(config=config, *args, **kwargs)

        self.config = config

        # default handle
        self.handle = None

        # string, times and values buffers
        self._c_str_buf = ctypes.create_string_buffer( \
                        int(self.config['device']['str_buf_len']))
        self._c_sample_times = (ctypes.c_int32 \
                            * int(self.config['device']['sample_buf_len']))()
        self._c_sample_values = (ctypes.c_int32 \
                            * int(self.config['device']['sample_buf_len']))()

        # buffer length values
        self._c_str_buf_len = ctypes.c_int16(len(self._c_str_buf))
        self._c_sample_buf_len = ctypes.c_int32(len(self._c_sample_times))

        # info type
        self._c_info_type = ctypes.c_int16()

        # C short to store number of channels
        self._c_enabled_channels = ctypes.c_int16()

        # C long for min/max ADC counts
        self._c_minimum_count = ctypes.c_int32()
        self._c_maximum_count = ctypes.c_int32()

        # C shorts for channel info
        self._c_channel = ctypes.c_int16()
        self._c_channel_enabled = ctypes.c_int16()
        self._c_channel_vrange = ctypes.c_int16()
        self._c_channel_itype = ctypes.c_int16()

        # sample/conversion times
        self._c_sample_time = ctypes.c_int32()
        self._c_conversion_time = ctypes.c_int16()

        # number of samples to take
        self._c_num_samples = ctypes.c_int32()

        # sample method
        self._c_sample_method = ctypes.c_int16()

        # default channel voltages
        self.channel_voltages = {i: self.DEFAULT_CHANNEL_VOLTAGE \
                                for i in range(1, self.NUM_CHANNELS + 1)}
        self.channel_types = {i: self.DEFAULT_CHANNEL_VOLTAGE \
                                for i in range(1, self.NUM_CHANNELS + 1)}

        # stream start time
        self.stream_start_timestamp = None

        # default sample time
        self.sample_time = None

        # load library
        self._load_library()

    def _load_library(self):
        # load library
        self.lib = self._get_hrdl_lib()

        logger.debug("C library for unit loaded")

    def _get_hrdl_lib(self):
        return ctypes.CDLL(self.config['picolog']['lib_path_adc24'])

    def open(self):
        """Opens the PicoLog unit for communication"""

        if self.handle is not None:
            raise Exception("Only one PicoLog unit can be opened at a time")

        # open unit and store handle as C short
        self.handle = self._hrdl_open()

        if not Handle.is_valid_handle(self.handle):
            if self.handle.value == Handle.UNIT_NOT_FOUND:
                raise Exception('Unit not found')
            elif self.handle.value == Handle.UNIT_NOT_OPENED:
                raise Exception('Unit found but not opened')
            else:
                raise Exception('Unknown invalid handle status')

        logger.info("Unit opened with handle %i", self.handle)

    def close(self):
        """Closes the currently open PicoLog unit"""

        if self.handle is None:
            raise Exception("No PicoLog unit is currently open")

        # close, recording status
        status = self._hrdl_close(self.handle)

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # reset handle
        self.handle = None

        logger.info("Unit closed")

    def configure(self):
        # set the sample rates
        self.set_sample_time(int(self.config['device']['sample_time']), \
            int(self.config['device']['conversion_time']))

        # picolog configuration and keys
        cfg = self.config["picolog"]
        cfg_keys = cfg.keys()

        # set up channels
        for i in range(1, self.NUM_CHANNELS + 1):
            cfg_channel = "channel_{0:d}".format(i)
            if cfg_channel in cfg_keys:
                if not bool(cfg[cfg_channel]):
                    # channel disabled
                    continue

                channel = int(i)

                cfg_channel_range = "channel_{0:d}_range".format(i)
                if cfg_channel_range in cfg_keys:
                    vrange = int(cfg[cfg_channel_range])
                else:
                    vrange = self.DEFAULT_CHANNEL_VOLTAGE

                cfg_channel_type = "channel_{0:d}_type".format(i)
                if cfg_channel_type in cfg_keys:
                    itype = int(cfg[cfg_channel_type])
                else:
                    itype = self.DEFAULT_CHANNEL_TYPE

                self.set_analog_in_channel(channel, True, vrange, itype)

    def is_open(self):
        """Checks if the unit is open"""
        return self.handle is not None

    def ready(self):
        """Checks if the unit has readings ready to be retrieved

        Note: this function cannot distinguish between a "not ready" message and
        an invalid handle. They both return False.

        :return: ready status
        """

        return self._hrdl_ready(self.handle)

    def get_unit_info(self, info_type):
        """Fetches the specified information from the unit

        :param info_type: the :class:`~datalog.adc.hrdl.constants.Status` \
        constant to retrieve
        :return: specified information string
        """

        logger.debug("Getting unit info")

        # set info type
        self._c_info_type.value = int(info_type)

        # check info type validity
        if not Info.is_valid_constant(info_type):
            raise Exception('Invalid info constant')

        # get unit info, returning number of characters written to buffer
        length = self._hrdl_get_unit_info(self.handle,
                                          ctypes.pointer(self._c_str_buf),
                                          self._c_str_buf_len,
                                          self._c_info_type)

        # length is zero if one of the parameters specified in the function call
        # above is out of range, or a null message pointer is specified
        if length is 0:
            raise Exception('Info type out of range or null message pointer')

        # extract and return string from buffer
        return self._c_str_buf.value[:length].decode("utf-8")

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

        logger.debug("Checking for error")

        # check for errors
        error = self.get_last_error_code()

        if Error.is_error(error):
            raise Exception("Error: {0}".format(Error.get_error_string(error)))

    def raise_unit_settings_error(self):
        """Checks the unit for settings error

        :raises Exception: upon discovering a settings error
        """

        logger.debug("Checking for settings error")

        # check for settings errors
        settings_error = self.get_last_settings_error_code()

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

        logger.debug("Setting analog input channel")

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
            logger.warning("Setting a differential input on a secondary channel"
                           " is not possible. Instead set the input on the "
                           "primary channel number.")

        channel = int(channel)
        enabled = int(enabled)
        vrange = int(vrange)
        itype = int(itype)

        # set channel info
        self._c_channel.value = channel
        self._c_channel_enabled.value = enabled
        self._c_channel_vrange.value = vrange
        self._c_channel_itype.value = itype

        # set the channel
        status = self._hrdl_set_analog_in_channel(self.handle,
                                                  self._c_channel,
                                                  self._c_channel_enabled,
                                                  self._c_channel_vrange,
                                                  self._c_channel_itype)

        # check return status
        if not Status.is_valid_status(status):
            # channel setting failed
            self.raise_unit_settings_error()

        # add channel to enabled set
        self.enabled_channels.update([channel])

        # set the channel voltage dict
        self.channel_voltages[channel] = vrange
        self.channel_types[channel] = itype

        logger.debug("Analog input channel %i set to enabled=%i, vrange=%i, "
                     "type=%i", channel, enabled, vrange, itype)

    def set_sample_time(self, sample_time, conversion_time):
        """Sets the time the unit can take to sample all active inputs.

        The sample_time must be large enough to allow all active channels to
        convert sequentially, i.e.

            sample_time > conversion_time * active_channels

        where active_channels can be obtained from
        `~datalog.adc.get_enabled_channels_count`

        :param sample_time: the time in milliseconds the unit has to sample \
        all active inputs
        :param conversion_time: the time a single channel has to sample its \
        input
        """

        sample_time = int(sample_time)
        conversion_time = int(conversion_time)

        # check validity of conversion time
        if not ConversionTime.is_valid(conversion_time):
            raise Exception("Invalid conversion time")

        # set sample and conversion times
        self._c_sample_time.value = sample_time
        self._c_conversion_time.value = conversion_time

        # set sample time
        status = self._hrdl_set_interval(self.handle,
                                         self._c_sample_time,
                                         self._c_conversion_time)

        # check return status
        if not Status.is_valid_status(status):
            # setting failure
            self.raise_unit_settings_error()

        # save sample time
        self.sample_time = sample_time

        logger.debug("Sample time set to %i, conversion time set to %i",
                     sample_time, conversion_time)

    def _run(self, sample_method):
        """Runs the unit recording functionality

        :param sample_method: sampling method
        :raises Exception: if sample_method is invalid or if run failed
        """

        # check validity of sample method
        if not SampleMethod.is_valid(sample_method):
            raise Exception("Invalid sample method")

        # set sample method
        self._c_sample_method.value = int(sample_method)

        # run
        status = self._hrdl_run(self.handle,
                                self._c_sample_buf_len,
                                self._c_sample_method)

        # check return status
        if not Status.is_valid_status(status):
            # run failure
            self.raise_unit_error()

    def stream(self):
        """Streams data from the unit"""

        logger.info("Starting unit streaming")

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

        # order the channels set
        ordered_channels = sorted(self.enabled_channels)

        # loop over times, adding readings
        for reading_time, reading_data in zip(times, samples):
            reading_time = int(reading_time)
            reading_data = list(reading_data)

            if not reading_data:
                # empty data
                break

            # convert time from ms since stream start to UNIX timestamp (in ms)
            real_time = self.stream_start_timestamp + reading_time

            readings.append(Reading(real_time, ordered_channels, reading_data))

        return readings

    def _get_payload(self):
        """Fetches uncollected sample payload from the unit"""

        # calculate number of values to collect for each channel
        samples_per_channel = int(self.config['device']['sample_buf_len']) \
                            // len(self.enabled_channels)

        # get samples, without using the overflow short parameter (None == NULL)
        num_samples = self._hrdl_get_times_and_values(
            self.handle,
            ctypes.pointer(self._c_sample_times),
            ctypes.pointer(self._c_sample_values),
            None,
            ctypes.c_long(samples_per_channel))

        # check return status
        if num_samples is 0:
            raise Exception("Call failed or no values available")

        # convert times and values into Python lists
        raw_times, raw_values = self._sample_lists(num_samples)

        # empty lists for cleaned up times and samples
        times = []
        values = []

        # number of active channels
        channel_count = len(self.enabled_channels)

        # loop over at least the first time and samples set (the first time can be zero,
        # next entries cannot be)
        for i, raw_time in enumerate(raw_times):
            # break when first zero time after first is found
            if i > 0 and raw_time == 0:
                break

            # add time to list
            times.append(raw_time)

            # start index
            i_start = i * channel_count

            # end index
            i_end = i_start + channel_count

            # add samples from each channel
            values.append(raw_values[i_start:i_end])

        return times, values

    def _sample_lists(self, num_samples):
        """Converts time and value C buffers into Python lists"""

        num_samples = int(num_samples)

        # number of values in the time period, i.e. total samples times
        # number of channels
        num_values = num_samples * len(self.enabled_channels)

        # convert to list and return
        # NOTE: the conversion from c_long elements to ints is done by the slice operation
        times = [int(i) for i in self._c_sample_times[:num_samples]]
        values = [int(i) for i in self._c_sample_values[:num_values]]

        return times, values

    def get_enabled_channels_count(self):
        """Fetches the number of channels enabled in the unit

        :return: number of enabled channels
        """

        logger.debug("Fetching enabled channel count")

        # get enabled channel count
        status = self._hrdl_get_number_of_enabled_channels(
            self.handle,
            ctypes.pointer(self._c_enabled_channels))

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # return enabled channels
        return int(self._c_enabled_channels.value)

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

        logger.debug("Fetching min/max ADC counts for channel %i", channel)

        # set channel
        self._c_channel.value = int(channel)

        # get minimum and maximum counts
        status = self._hrdl_get_min_max_adc_counts(
            self.handle,
            ctypes.pointer(self._c_minimum_count),
            ctypes.pointer(self._c_maximum_count),
            self._c_channel)

        # check return status
        if not Status.is_valid_status(status):
            raise Exception('Invalid handle passed to unit')

        # return channel ADC counts
        return (int(self._c_minimum_count.value),
                int(self._c_maximum_count.value))

    def _hrdl_open(self):
        return int(self.lib.HRDLOpenUnit())

    def _hrdl_close(self, handle):
        return int(self.lib.HRDLCloseUnit(handle))

    def _hrdl_ready(self, handle):
        return int(self.lib.HRDLReady(handle))

    def _hrdl_get_unit_info(self, handle, pnt_str_buf, len_str_buf, info_type):
        return int(self.lib.HRDLGetUnitInfo(handle, pnt_str_buf, len_str_buf,
                                            info_type))

    def _hrdl_set_analog_in_channel(self, handle, channel, enabled, vrange,
                                    itype):
        return int(self.lib.HRDLSetAnalogInChannel(handle, channel, enabled,
                                                   vrange, itype))

    def _hrdl_set_interval(self, handle, sample_time, conversion_time):
        return int(self.lib.HRDLSetInterval(handle, sample_time,
                                            conversion_time))

    def _hrdl_run(self, handle, sample_buf_len, sample_method):
        return int(self.lib.HRDLRun(handle, sample_buf_len, sample_method))

    def _hrdl_get_times_and_values(self, handle, pnt_sample_times,
                                   pnt_sample_values, pnt_overflow,
                                   samples_per_channel):
        return int(self.lib.HRDLGetTimesAndValues(handle,
                                                  pnt_sample_times,
                                                  pnt_sample_values,
                                                  pnt_overflow,
                                                  samples_per_channel))

    def _hrdl_get_number_of_enabled_channels(self, handle,
                                             ptr_enabled_channels):
        return int(self.lib.HRDLGetNumberOfEnabledChannels(handle,
                                                           ptr_enabled_channels))

    def _hrdl_get_min_max_adc_counts(self, handle, ptr_min_count, ptr_max_count,
                                     channel):
        return int(self.lib.HRDLGetMinMaxAdcCounts(handle, ptr_min_count,
                                                   ptr_max_count, channel))


class PicoLogAdc24Sim(PicoLogAdc24):
    """Represents a simulated :class:`PicoLogAdc24` useful for testing"""

    # maximum string buffer (guess)
    MAX_BUF_LEN = 2 ** 32 / 2 - 1

    # maximum sample time in ms (guess)
    MAX_SAMPLE_TIME = 16000

    # count range
    MIN_COUNT = 0
    MAX_COUNT = 2 ** 24 - 1

    def __init__(self, *args, **kwargs):
        # call parent
        super(PicoLogAdc24Sim, self).__init__(*args, **kwargs)

        # fake enabled channels
        self._fake_enabled_channels = set([])

        # fake samples buffers
        self._fake_samples_time_buf = []
        self._fake_samples_value_buf = []

        # fake request time
        self._last_fake_request_time = None

        # default settings error
        self._settings_error_code = SettingsError.OK

        logger.warning("Fake PicoLog ADC24 in use")
        logger.debug("Fake library loaded")

    def _get_hrdl_lib(self):
        # no library to load
        return None

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
            range(len(self.enabled_channels))] for j in range(num_samples)])

        # reset stopwatch
        self._last_fake_request_time = last_request_time \
                                    + num_samples * self.sample_time

    def stream(self):
        # call parent
        super(PicoLogAdc24Sim, self).stream()

        # set the time to use for readings
        self._last_fake_request_time = self.stream_start_timestamp

    def _hrdl_open(self):
        return 1

    def _hrdl_close(self, handle):
        # success
        return 1

    def _hrdl_ready(self, handle):
        """Checks if the unit has readings ready to be retrieved"""
        # generate fake samples
        self._generate_fake_samples()

        if self._fake_samples_time_buf:
            return 1

        return 0

    def _hrdl_get_unit_info(self, handle, pnt_str_buf, len_str_buf, info_type):
        if pnt_str_buf is None:
            # null string buffer returned
            return 0

        # validate info type
        info_type = int(info_type.value)

        # check info type validity
        if not Info.is_valid_constant(info_type):
            # info type out of range
            return 0

        # return info
        # examples from hardware manual
        if info_type == Info.DRIVER_VERSION:
            info = "Fake HRDL Driver, 1.0.0.0"
        elif info_type == Info.USB_VERSION:
            info = "USB 1.1"
        elif info_type == Info.HARDWARE_VERSION:
            info = "1"
        elif info_type == Info.VARIANT_INFO:
            info = "24"
        elif info_type == Info.BATCH_AND_SERIAL:
            info = "CMY02/116"
        elif info_type == Info.CAL_DATE:
            info = "29Jul15"
        elif info_type == Info.KERNEL_DRIVER_VERSION:
            # weirdly, there is no example given in manual, so just return a
            # made-up value
            info = "PICOPP.SYS V1.0"
        elif info_type == Info.ERROR:
            # nothing relevant to return other than OK
            info = str(Error.OK)
        elif info_type == Info.SETTINGS_ERROR:
            info = str(self._settings_error_code)

        # clip info up to the specified length
        info = info[:int(len_str_buf.value)]

        # write info into buffer
        self._c_str_buf.value = info.encode("utf-8")

        return len(info)

    def _hrdl_set_analog_in_channel(self, handle, channel, enabled, vrange, itype):
        """Set fake analog input channel

        This does not care about the value of itype, since it doesn't matter
        for fake readings.
        """

        if not Channel.is_valid(int(channel.value)):
            # invalid channel
            self._settings_error_code = SettingsError.INVALID_CHANNEL
            return 0

        if not VoltageRange.is_valid(int(vrange.value)):
            # invalid channel
            self._settings_error_code = SettingsError.INVALID_VOLTAGE_RANGE
            return 0

        if int(enabled.value) == 1:
            self._fake_enabled_channels.add(int(channel.value))
        else:
            try:
                self._fake_enabled_channels.remove(int(channel.value))
            except KeyError:
                # don't care if channel already disabled
                pass

        # success
        self._settings_error_code = SettingsError.OK
        return 1

    def _hrdl_set_interval(self, handle, sample_time, conversion_time):
        conversion_time = int(conversion_time.value)

        if not ConversionTime.is_valid(conversion_time):
            # invalid conversion time
            self._settings_error_code = SettingsError.INVALID_PARAMETER
            return 0

        # get conversion time in ms
        conversion_time_ms = ConversionTime.get_conversion_time(conversion_time)

        sample_time = int(sample_time.value)

        # samples must be able to be made within the total sample time
        if len(self.enabled_channels) * conversion_time_ms \
            > sample_time:
            # settings error
            self._settings_error_code = SettingsError.CONVERSION_TIME_TOO_SLOW
            return 0
        # sample time must not be out of range
        elif sample_time > self.MAX_SAMPLE_TIME:
            self._settings_error_code = SettingsError.SAMPLE_INTERVAL_OUT_OF_RANGE
            return 0

        # success
        self._settings_error_code = SettingsError.OK
        return 1

    def _hrdl_run(self, handle, sample_buf_len, sample_method):
        sample_method = int(sample_method.value)

        if not SampleMethod.is_valid(sample_method):
            # invalid sample method
            self._settings_error_code = SettingsError.INVALID_PARAMETER
            return 0

        # temporary: only support stream
        if sample_method is not SampleMethod.STREAM:
            raise Exception("Only streaming sample method currently supported")

        sample_buf_len = int(sample_buf_len.value)

        if sample_buf_len > self.MAX_BUF_LEN:
            # sample buffer length out of range
            self._settings_error_code = SettingsError.INVALID_PARAMETER
            return 0

        # success
        self._settings_error_code = SettingsError.OK
        return 1

    def _hrdl_get_times_and_values(self, handle, pnt_sample_times,
                                   pnt_sample_values, pnt_overflow,
                                   samples_per_channel):
        # copy the fake samples and times
        times = list(self._fake_samples_time_buf)
        values = list(self._fake_samples_value_buf)

        samples_per_channel = int(samples_per_channel.value)

        # number of channels
        n_channels = len(self.enabled_channels)

        # number of samples, either the requested amount or the length of the
        # list
        n_times = len(times)
        if samples_per_channel > n_times:
            samples_per_channel = n_times

        sample_count = 0
        for i in range(samples_per_channel):
            # set sample time directly in the array
            self._c_sample_times[i] = ctypes.c_int32(times[i])
            for j in range(n_channels):
                idx = n_channels * i + j
                # set sample value directly in the array
                self._c_sample_values[idx] = values[i][j]

            # increment sample counter
            sample_count += 1

        # reset buffers
        self._fake_samples_time_buf = self._fake_samples_time_buf[samples_per_channel:]
        self._fake_samples_value_buf = self._fake_samples_value_buf[idx+1:]

        return sample_count

    def _hrdl_get_number_of_enabled_channels(self, handle, ptr_enabled_channels):
        # set variable directly
        self._c_enabled_channels = ctypes.c_int16(len(self.enabled_channels))

        return 1

    def _hrdl_get_min_max_adc_counts(self, handle, ptr_min_count, ptr_max_count, channel):
        self._c_minimum_count.value = self.MIN_COUNT
        self._c_maximum_count.value = self.MAX_COUNT

        return 1
