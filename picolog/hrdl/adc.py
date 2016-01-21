import os
import ctypes

from picolog.constants import Handle, Status, Info, Error

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
        self.library_path = os.getenv('PICOLOG_HRDL_DRIVER_PATH', '/opt/picoscope/lib/libpicohrdl.so')

        # buffer length
        self.string_buffer_length = os.getenv('PICOLOG_HRDL_STRING_BUFFER_LENGTH', 1000)

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

        # length is zero if one of the parameters specified in the function call
        # above is out of range, or a null message pointer is specified
        if length is 0:
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
        """Fetches the last error string from the unit

        :return: error status string
        """

        # cast error into int and look up and return its corresponding message
        return Error.get_error_string(int(self.get_unit_info(Info.ERROR)))

    def handle_is_valid(self):
        """Returns validity of current handle"""

        return Handle.is_valid_handle(self.handle.value)

if __name__ == '__main__':
    adc = PicoLogAdc()

    adc.open_unit()
    print adc.get_full_unit_info()
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
