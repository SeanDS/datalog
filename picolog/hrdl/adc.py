from __future__ import print_function, division

import sys
import os
import logging
import ctypes
import time

from picolog.constants import Handle, Channel, Status, Info, \
Error, SettingsError, Progress, VoltageRange, InputType, ConversionTime, \
SampleMethod
from picolog.data import Reading

class PicoLogAdc(object):
    """Represents an instance of the PicoLog ADC driver"""

    """Logger object"""
    logger = None

    """PicoLog library instance"""
    library = None

    """Path to PicoLog library"""
    library_path = None

    """C string buffer length"""
    string_buffer_length = None

    """C long array sample buffer length"""
    sample_buffer_length = None

    """Handle representing the PicoLog unit in communication"""
    handle = None

    """Total time required to collect samples of enabled channels"""
    sample_time = None

    """Enabled channels set"""
    enabled_channels = set()

    """Channel voltage settings (using VoltageRange constants)"""
    channel_voltages = {}

    def __init__(self, library_path, string_buffer_length, sample_buffer_length, \
    logger):
        """Initialises the PicoLog ADC interface
        """

        # set parameters
        self.library_path = library_path
        self.string_buffer_length = string_buffer_length
        self.sample_buffer_length = sample_buffer_length
        self.logger = logger

        # load ADC library
        self._load_library()

    def _load_library(self):
        """Loads the PicoLog library"""

        self.logger.info("Loading ADC driver")

        self.library = ctypes.cdll.LoadLibrary(self.library_path)

        self.logger.info("ADC driver loaded successfully")

    def open_unit(self):
        """Opens the PicoLog unit for communication"""

        self.logger.info("Opening unit")

        # create handle as C short
        self.handle = ctypes.c_short(self.library.HRDLOpenUnit())

        if not self.handle_is_valid():
            if self.handle.value is Handle.UNIT_NOT_FOUND:
                raise Exception('Unit not found')
            elif self.handle.value is Handle.UNIT_NOT_OPENED:
                raise Exception('Unit found but not opened')
            else:
                raise Exception('Unknown invalid handle status')

        self.logger.info("Opened unit successfully")

    def open_unit_with_progress(self, stream=sys.stdout):
        """Opens the PicoLog unit with a progress notice

        :raises Exception: if another open operation is already in progress
        """

        print("Opening unit", end="", file=stream)

        # start timer
        start_time = time.time()

        # initiate asynchronous open, recording status
        status = ctypes.c_short(self.library.HRDLOpenUnitAsync())

        # check return status
        if status.value is 0:
            raise Exception("Unit not found, or there is already an open \
operation in progress")

        while True:
            # get progress
            (status, progress) = self._get_open_unit_progress_status()

            if status is Progress.OPEN_PROGRESS_PENDING:
                print(".", end="", file=stream)

                # flush output buffer
                stream.flush()

                # sleep
                time.sleep(0.1)
            elif status is Progress.OPEN_PROGRESS_COMPLETE:
                # calculate time taken
                time_taken = time.time() - start_time

                # newline
                print(file=stream)

                self.logger.info("Opened unit in {0}s".format(time_taken))

                break
            else:
                raise Exception("Unit open failure")

    def _get_open_unit_progress_status(self):
        """Fetches the current unit open progress status

        :return: unit open status and percentage progress
        """

        # create handle C short if empty
        if self.handle is None:
            self.handle = ctypes.c_short()

        # default progress is -1% in case the return status is "complete" or "fail"
        progress = ctypes.c_short(-1)

        # get status and progress
        status = ctypes.c_short(self.library.HRDLOpenUnitProgress( \
        ctypes.pointer(self.handle), ctypes.pointer(progress)))

        return (status.value, progress.value)

    def close_unit(self):
        """Closes the currently open PicoLog unit"""

        self.logger.info("Closing unit")

        # check validity of unit handle
        if not self.handle_is_valid():
            raise Exception('Unit handle is not defined or not valid')

        # close, recording status
        status = ctypes.c_short(self.library.HRDLCloseUnit(self.handle))

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        self.logger.info("Closed successfully")

    def ready(self):
        """Checks if the unit has readings ready to be retrieved

        Note: this function cannot distinguish between a "not ready" message and
        an invalid handle. They both return False.

        :return: ready status
        """

        # get ready status
        ready = ctypes.c_short(self.library.HRDLReady(self.handle))

        return ready.value

    def get_unit_info(self, info_type):
        """Fetches the specified information from the unit

        :param info_type: the :class:`~picolog.constants.Status` \
        constant to retrieve
        :return: specified information string
        """

        self.logger.info("Getting unit info")

        # check info type validity
        if not Info.is_valid_constant(info_type):
            raise Exception('Invalid info constant')

        # create C char array to hold status
        message = ctypes.create_string_buffer(self.string_buffer_length)

        # get unit info, with pointer to status variable
        length = ctypes.c_short(self.library.HRDLGetUnitInfo(self.handle, \
        ctypes.pointer(message), ctypes.c_short(len(message)), info_type))

        # length is zero if one of the parameters specified in the function call
        # above is out of range, or a null message pointer is specified
        if length.value is 0:
            raise Exception('Info type out of range or null message pointer')

        self.logger.info("Unit info retrieved successfully")

        return message.value

    def get_formatted_unit_info(self, info_type):
        """Fetches the specified information from the unit, with context

        :return: formatted information string
        """

        # get unformatted info string
        info = self.get_unit_info(info_type)

        # return formatted version
        return Info.format(info, info_type)

    def get_full_unit_info(self):
        """Fetches formatted string of all available unit info

        :return: full unit information string
        """

        # get all unit info as a list
        info = map(self.get_formatted_unit_info, Info.get_info_constants())

        # reduce list to string
        return reduce(lambda x, y: "{0}\n{1}".format(x, y), info)

    def get_last_error(self):
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
        return Error.get_error_string(self.get_last_error())

    def get_last_settings_error(self):
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
        return SettingsError.get_error_string(self.get_last_settings_error())

    def raise_unit_error(self):
        """Checks the unit for errors and settings errors

        :raises Exception: upon discovering an error
        """

        self.logger.info("Checking for error")

        # check for errors
        error = self.get_last_error()

        if Error.is_error(error):
            raise Exception("Error: {0}".format(Error.get_error_string(error)))

        # error is expected but apparently not present...
        raise Exception("Despite being asked to find it, no error found")

    def raise_unit_settings_error(self):
        """Checks the unit for settings error

        :raises Exception: upon discovering a settings error
        """

        self.logger.info("Checking for settings error")

        # check for settings errors
        settings_error = self.get_last_settings_error()

        if SettingsError.is_error(settings_error):
            raise Exception("Settings error: {0}".format( \
            SettingsError.get_error_string(settings_error)))

        # error is expected but apparently not present...
        raise Exception("Despite being asked to find it, no settings error \
            found")

    def set_analog_in_channel(self, channel, enabled, vrange, itype):
        """Sets the specified channel to be an analog input

        :param channel: channel number to set
        :param enabled: whether channel is enabled or not
        :param vrange: voltage range to use for this channel
        :param itype: input type, single ended or differential
        :raises Exception: when channel is invalid, or voltage range is \
        invalid, or input type is invalid
        """

        self.logger.info("Setting analog input channel")

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
        if enabled:
            enabled = 1
        else:
            enabled = 0

        # print warning to user if differential input is specified on an even
        # channel
        if itype is InputType.DIFFERENTIAL and channel % 2 == 0:
            logging.warning("Setting a differential input on a secondary \
channel is not possible. Instead set the input on the primary channel number.")

        # set the channel
        status = ctypes.c_short( \
        self.library.HRDLSetAnalogInChannel(self.handle, \
        ctypes.c_short(channel), ctypes.c_short(enabled), \
        ctypes.c_short(vrange), ctypes.c_short(itype)))

        # check return status
        if not Status.is_valid_status(status.value):
            # channel setting failed
            self.raise_unit_settings_error()

        # add channel to enabled set
        self.enabled_channels.update([channel])

        # set the channel voltage dict
        self.channel_voltages[channel] = vrange

        self.logger.info("Analog input channel {0} set to enabled={1}, \
vrange={2}, type={3}".format(channel, enabled, vrange, itype))

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

        self.logger.info("Setting sample and conversion times")

        # check validity of conversion time
        if not ConversionTime.is_valid(conversion_time):
            raise Exception("Invalid conversion time")

        # set sample time
        status = ctypes.c_short(self.library.HRDLSetInterval(self.handle, \
        ctypes.c_long(sample_time), ctypes.c_short(conversion_time)))

        # check return status
        if not Status.is_valid_status(status.value):
            # setting failure
            self.raise_unit_settings_error()

        # save sample time
        self.sample_time = sample_time

        self.logger.info("Sample time set to {0}, conversion time set to \
{1}".format(sample_time, conversion_time))

    def stream(self):
        """Streams data from the unit"""

        self.logger.info("Starting unit streaming")

        self._run(SampleMethod.STREAM)

        self.logger.info("Unit streaming started successfully")

    def _run(self, sample_method):
        """Runs the unit recording functionality

        :param sample_method: sampling method
        :raises Exception: if sample_method is invalid or if run failed
        """

        # check validity of sample method
        if not SampleMethod.is_valid(sample_method):
            raise Exception("Invalid sample method")

        # run
        status = ctypes.c_short(self.library.HRDLRun(self.handle, \
        ctypes.c_long(self.sample_buffer_length), \
        ctypes.c_short(sample_method)))

        # check return status
        if not Status.is_valid_status(status.value):
            # run failure
            self.raise_unit_error()

    def get_readings(self):
        """Fetches uncollected ADC readings

        A reading is a full set of channel samples for a given time. This method
        returns a list of readings, in chronological order.
        """

        # get payload
        (times, samples) = self._get_payload()

        # empty list of readings
        readings = []
        
        if times and samples:
            readings.append(Reading(times[0], self.enabled_channels, samples))

        # iterate over individual readings
        #for (reading_time, reading_samples) in zip(times, samples):
        #    # add new reading to list
        #    readings.append(Reading(reading_time, self.enabled_channels, \
        #    reading_samples))

        return readings

    def _get_payload(self):
        """Fetches uncollected sample payload from the unit"""

        # create C long times array
        times = (ctypes.c_long * self.sample_buffer_length)()

        # create C long values array
        samples = (ctypes.c_long * self.sample_buffer_length)()

        # calculate number of values to collect for each channel
        samples_per_channel = self.sample_buffer_length // \
        len(self.enabled_channels)

        # get samples, without using the overflow short parameter (None == NULL)
        num_values = ctypes.c_long( \
        self.library.HRDLGetTimesAndValues(self.handle, ctypes.pointer(times), \
        ctypes.pointer(samples), None, ctypes.c_long(samples_per_channel)))

        # check return status
        if num_values is 0:
            raise Exception("Call failed or no values available")

        # convert times and values into Python lists
        times = self._sample_array_to_list(times)
        samples = self._sample_array_to_list(samples)

        # collect indices corresponding to non-zero times
        time_indices = [i for i, e in enumerate(times) if e is not 0]
        sample_indices = [i for i, e in enumerate(samples) if e is not 0]

        # return times and values
        return (map(times.__getitem__, time_indices), map(samples.__getitem__, sample_indices))

    def _sample_array_to_list(self, data_array):
        """Converts a C type samples array into a Python list

        :param data_array: C type long array to convert
        :return: list of data elements
        """

        # convert to list and return
        return [i for i in data_array]

    def counts_to_volts(self, counts, channel):
        """Converts the specified counts to volts

        :param counts: the counts to convert
        :param channel: the channel number this measurements corresponds to
        :return: voltage equivalent of counts
        """

        # get minimum and maximum counts for this channel
        (min_counts, max_counts) = self.get_min_max_adc_counts(channel)

        # get maximum voltage (on a single side of the input)
        v_max = self.get_channel_max_voltage(channel)

        # calculate conversion
        scale = v_max / max_counts

        # return voltages
        return [count * scale for count in counts]

    def get_channel_max_voltage(self, channel):
        """Returns the maximum voltage input for the specified channel

        :param channel: the channel to get the maximum voltage for
        :return: voltage range of specified channel
        :raises Exception: if the specified channel is not enabled or invalid
        """

        # validate specified channel
        if channel not in self.channel_voltages:
            raise Exception("The specified channel is not enabled or invalid")

        # return voltage
        return VoltageRange.get_max_voltage(self.channel_voltages[channel])

    def get_min_max_adc_counts(self, channel):
        """Fetches the minimum and maximum ADC counts available for the \
        connected device.

        Note: the documentation from Pico is wrong regarding this function. The
        order in which the variables holding the  minimum and maximum ADC counts
        are referenced is swapped.

        :param channel: the channel number to fetch the counts for
        :return: minimum and maximum ADC counts for the specified channel
        """

        self.logger.info("Fetching min/max ADC counts for channel {0}".format(channel))

        # C long for minimum ADC count
        minimum = ctypes.c_long()

        # C long for maximum ADC count
        maximum = ctypes.c_long()

        # get minimum and maximum counts
        status = ctypes.c_short(self.library.HRDLGetMinMaxAdcCounts( \
        self.handle, ctypes.pointer(minimum), ctypes.pointer(maximum), \
        ctypes.c_short(channel)))

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        self.logger.info("Fetched min/max ADC counts successfully")

        # return channel ADC counts
        return (minimum.value, maximum.value)

    def get_enabled_channels_count(self):
        """Fetches the number of channels enabled in the unit

        :return: number of enabled channels
        """

        self.logger.info("Fetching enabled channel count")

        # C short to store number of channels
        enabled_channels = ctypes.c_short()

        # get enabled channel count
        status = ctypes.c_short( \
        self.library.HRDLGetNumberOfEnabledChannels(self.handle, \
        ctypes.pointer(enabled_channels)))

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        self.logger.info("Fetched enabled channel count successfully")

        # return enabled channels
        return enabled_channels.value

    def handle_is_valid(self):
        """Returns validity of current handle"""

        return Handle.is_valid_handle(self.handle.value)
