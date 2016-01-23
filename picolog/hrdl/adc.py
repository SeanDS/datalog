from __future__ import print_function

import sys
import os
import ctypes
import time

from picolog.constants import Handle, Channel, Status, Info, \
Error, SettingsError, Progress

class PicoLogAdc(object):
    """Represents an instance of the PicoLog ADC driver"""

    """PicoLog library instance"""
    library = None

    """Path to PicoLog library"""
    library_path = None

    """C string buffer length"""
    string_buffer_length = None

    """Handle representing the PicoLog unit in communication"""
    handle = None

    def __init__(self):
        self.load_config()
        self.load_library()

    def load_config(self):
        """Loads configuration options from environment"""

        # path to PicoLog HRDL driver
        self.library_path = os.getenv('PICOLOG_HRDL_DRIVER_PATH', \
        '/opt/picoscope/lib/libpicohrdl.so')

        # buffer length
        self.string_buffer_length = \
        os.getenv('PICOLOG_HRDL_STRING_BUFFER_LENGTH', 1000)

    def load_library(self):
        """Loads the PicoLog library"""

        self.library = ctypes.cdll.LoadLibrary(self.library_path)

    def open_unit(self):
        """Opens the PicoLog unit for communication"""

        print("[PicoLogAdc] opening unit")

        # create handle as C short
        self.handle = ctypes.c_short(self.library.HRDLOpenUnit())

        if not self.handle_is_valid():
            if self.handle.value is Handle.UNIT_NOT_FOUND:
                raise Exception('Unit not found')
            elif self.handle.value is Handle.UNIT_NOT_OPENED:
                raise Exception('Unit found but not opened')
            else:
                raise Exception('Unknown invalid handle status')

        print("[PicoLogAdc] opened unit successfully")

    def open_unit_with_progress(self):
        """Opens the PicoLog unit with a progress notice

        :raises Exception: if another open operation is already in progress
        """

        print("[PicoLogAdc] opening unit", end="")

        # start timer
        start_time = time.time()

        # initiate asynchronous open, recording status
        status = ctypes.c_short(self.library.HRDLOpenUnitAsync())

        # check return status
        if status.value is 0:
            raise Exception("There is already an open operation in progress")

        while True:
            # get progress
            (status, progress) = self.get_open_unit_progress_status()

            if status is Progress.OPEN_PROGRESS_PENDING:
                print(".", end="")

                # flush output buffer
                sys.stdout.flush()

                # sleep
                time.sleep(0.1)
            elif status is Progress.OPEN_PROGRESS_COMPLETE:
                # calculate time taken
                time_taken = time.time() - start_time

                print()
                print("[PicoLogAdc] opened unit in {0}s".format(time_taken))
                break
            else:
                raise Exception("Unit open failure")

    def get_open_unit_progress_status(self):
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

        print("[PicoLogAdc] closing unit")

        # check validity of unit handle
        if not self.handle_is_valid():
            raise Exception('Unit handle is not defined or not valid')

        # close, recording status
        status = ctypes.c_short(self.library.HRDLCloseUnit(self.handle))

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        print("[PicoLogAdc] closed successfully")

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

        print("[PicoLogAdc] getting unit info")

        # check info type validity
        if not Info.is_valid_constant(info_type):
            raise Exception('Invalid info constant')

        # create C char array to hold status
        message = ctypes.create_string_buffer(self.string_buffer_length)

        # get unit info, with pointer to status variable
        length = ctypes.c_short(self.library.HRDLGetUnitInfo(self.handle, \
        ctypes.pointer(message), ctypes.c_short(len(message)), info_type))

        # Note: don't check_for_errors() here, since this uses get_unit_info().

        # length is zero if one of the parameters specified in the function call
        # above is out of range, or a null message pointer is specified
        if length.value is 0:
            raise Exception('Info type out of range or null message pointer')

        print("[PicoLogAdc] unit info retrieved successfully")

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

    def check_for_errors(self):
        """Checks the unit for errors and settings errors

        :raises Exception: upon discovering an error
        """

        print("[PicoLogAdc] checking for errors")

        # check for errors
        error = self.get_last_error()

        if Error.is_error(error):
            raise Exception("Error: {0}".format(Error.get_error_string(error)))

        # check for settings errors
        settings_error = self.get_last_settings_error()

        if SettingsError.is_error(settings_error):
            raise Exception("Settings error: {0}".format( \
            SettingsError.get_error_string(settings_error)))

        print("[PicoLogAdc] no errors")

    def get_min_max_adc_counts(self, channel):
        """Fetches the minimum and maximum ADC counts available for the \
        connected device.

        Note: the documentation from Pico is wrong regarding this function. The
        order in which the variables holding the  minimum and maximum ADC counts
        are referenced is swapped.

        :param channel: the channel number to fetch the counts for
        :return: minimum and maximum ADC counts for the specified channel
        """

        print("[PicoLogAdc] fetching min/max ADC counts for channel {0}".format(channel))

        # C long for minimum ADC count
        minimum = ctypes.c_long()

        # C long for maximum ADC count
        maximum = ctypes.c_long()

        # get minimum and maximum counts
        status = ctypes.c_short(self.library.HRDLGetMinMaxAdcCounts( \
        self.handle, ctypes.pointer(maximum), ctypes.pointer(minimum), \
        ctypes.c_short(channel)))

        # check for errors
        self.check_for_errors()

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        print("[PicoLogAdc] fetched min/max ADC counts successfully")

        # return channel ADC counts
        return (minimum.value, maximum.value)

    def get_enabled_channels_count(self):
        """Fetches the number of channels enabled in the unit

        :return: number of enabled channels
        """

        print("[PicoLogAdc] fetching enabled channel count")

        # C short to store number of channels
        enabled_channels = ctypes.c_short()

        # get enabled channel count
        status = ctypes.c_short( \
        self.library.HRDLGetNumberOfEnabledChannels(self.handle, \
        ctypes.pointer(enabled_channels)))

        # check for errors
        self.check_for_errors()

        # check return status
        if not Status.is_valid_status(status.value):
            raise Exception('Invalid handle passed to unit')

        print("[PicoLogAdc] fetched enabled channel count successfully")

        # return enabled channels
        return enabled_channels.value

    def handle_is_valid(self):
        """Returns validity of current handle"""

        return Handle.is_valid_handle(self.handle.value)

if __name__ == '__main__':
    adc = PicoLogAdc()

    adc.open_unit_with_progress()
    print(adc.get_full_unit_info())
    print("Enabled channels: {0}".format(adc.get_enabled_channels_count()))
    print("ADC counts: min: {0}, max: {1}".format(*adc.get_min_max_adc_counts(Channel.ANALOG_CHANNEL_1)))
    print("Ready to retrieve values? {0}".format(adc.ready()))
    adc.close_unit()

# handle = x.HRDLOpenUnit()
#
# channel = ctypes.c_short(1)
# enabled  = ctypes.c_short(1)
# crange = ctypes.c_short(1)
# single = ctypes.c_short(1)
# convint = ctypes.c_short(4)
# channels = ctypes.c_short()
# overflow = ctypes.c_short()
# value = ctypes.c_long()
# status = ctypes.create_string_buffer(1000)
#
# x.HRDLGetUnitInfo(handle, ctypes.pointer(status), ctypes.c_short(1000), ctypes.c_short(8))
#
# print "Status: {0}".format(status[:])
#
# x.HRDLSetAnalogInChannel(handle, channel, enabled, crange, single)
#
# x.HRDLGetNumberOfEnabledChannels(handle, ctypes.pointer(channels))
#
# print "Enabled channels: {0}".format(channels)
#
# x.HRDLGetSingleValue(handle, channel, crange, convint, single, ctypes.pointer(overflow), ctypes.pointer(value))
#
# print "Value: {0}".format(value)
#
# x.HRDLCloseUnit(handle)
