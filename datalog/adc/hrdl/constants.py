"""PicoLog ADC unit constants"""

class Handle(object):
    """Unit handle"""

    UNIT_NOT_OPENED = -1
    UNIT_NOT_FOUND = 0

    @classmethod
    def is_valid_handle(cls, handle):
        """Validates unit handle

        :param handle: unit handle to validate
        :type handle: int
        :return: True if handle is valid, False otherwise
        :rtype: boolean
        """

        if handle > cls.UNIT_NOT_FOUND:
            return True

        return False

class Status(object):
    """Unit status"""

    INVALID = 0
    VALID = 1

    @classmethod
    def is_valid_status(cls, status):
        """Validates unit status

        :param status: status to validate
        :type status: int
        :return: True if status is valid, False otherwise
        :rtype: boolean
        """

        if status is cls.VALID:
            return True

        return False

class Channel(object):
    """Unit channels"""

    ANALOG_CHANNEL_1 = 1
    ANALOG_CHANNEL_2 = 2
    ANALOG_CHANNEL_3 = 3
    ANALOG_CHANNEL_4 = 4
    ANALOG_CHANNEL_5 = 5
    ANALOG_CHANNEL_6 = 6
    ANALOG_CHANNEL_7 = 7
    ANALOG_CHANNEL_8 = 8
    ANALOG_CHANNEL_9 = 9
    ANALOG_CHANNEL_10 = 10
    ANALOG_CHANNEL_11 = 11
    ANALOG_CHANNEL_12 = 12
    ANALOG_CHANNEL_13 = 13
    ANALOG_CHANNEL_14 = 14
    ANALOG_CHANNEL_15 = 15
    ANALOG_CHANNEL_16 = 16
    MIN_ANALOG_CHANNEL = ANALOG_CHANNEL_1
    MAX_ANALOG_CHANNEL = ANALOG_CHANNEL_16

    @classmethod
    def is_valid(cls, channel):
        """Validates channel

        :param channel: channel to validate
        :type channel: int
        :return: True if channel is valid, False otherwise
        :rtype: boolean
        """

        return channel >= cls.MIN_ANALOG_CHANNEL and \
        channel <= cls.MAX_ANALOG_CHANNEL

class Info(object):
    """Unit info"""

    DRIVER_VERSION = 0
    USB_VERSION = 1
    HARDWARE_VERSION = 2
    VARIANT_INFO = 3
    BATCH_AND_SERIAL = 4
    CAL_DATE = 5
    KERNEL_DRIVER_VERSION = 6
    ERROR = 7
    SETTINGS_ERROR = 8

    """Info formats"""
    formats = {0: "Driver version: {0}", 1: "USB version: {0}",
               2: "Hardware version: {0}", 3: "Unit variant: {0}",
               4: "Batch and serial: {0}", 5: "Calibration date: {0}",
               6: "Kernel driver version: {0}", 7: "Error code: {0}",
               8: "Settings error: {0}"}

    @classmethod
    def is_valid_constant(cls, constant):
        """Validates constant

        :param constant: constant to validate
        :type constant: int
        :return: True if constant is valid, False otherwise
        :rtype: boolean
        """

        if constant >= cls.DRIVER_VERSION and constant <= cls.SETTINGS_ERROR:
            return True

        return False

    @classmethod
    def get_info_constants(cls):
        """Returns available info constants

        :return: collection of constants
        :rtype: iterable<int>
        """

        return range(cls.DRIVER_VERSION, cls.SETTINGS_ERROR + 1)

    @classmethod
    def format(cls, info, info_type):
        """Formats the specified info using the specified info type

        :param info: the unformatted info string
        :type info: string
        :param info_type: the info constant
        :type info_type: string
        :return: formatted info string
        :rtype: string
        """

        return cls.formats[info_type].format(info)

class Error(object):
    """Unit errors"""

    OK = 0
    KERNEL_DRIVER_TOO_OLD = 1
    UNIT_NOT_FOUND = 2
    FIRMWARE_CONFIG_FAIL = 3
    OS_NOT_SUPPORTED = 4
    MAX_DEVICES_ALREADY_OPEN = 5

    """Error strings"""
    strings = {0: "OK", 1: "Kernel driver too old", 2: "Unit not found",
               3: "Firmware config failure", 4: "OS not supported",
               5: "Maximum devices already open"}

    @classmethod
    def get_error_string(cls, error_code):
        """Returns the error message corresponding to the specified error code

        :param error_code: error code to fetch string for
        :type error_code: int
        :return: error message
        :rtype: string
        """

        return cls.strings[error_code]

    @classmethod
    def is_error(cls, error_code):
        """Validates error code

        :param error_code: error code to validate
        :type error_code: int
        :return: True if error code is valid, False otherwise
        :rtype: boolean
        """

        # HACK: override error "Kernel driver too old" - this appears to be a
        # bug with the driver
        if error_code is cls.KERNEL_DRIVER_TOO_OLD:
            return False

        # check if "OK" error code is given
        if error_code is cls.OK:
            return False

        # otherwise it's an error
        return True

class SettingsError(object):
    """Unit settings errors"""

    CONVERSION_TIME_OUT_OF_RANGE = 0
    SAMPLE_INTERVAL_OUT_OF_RANGE = 1
    CONVERSION_TIME_TOO_SLOW = 2
    CHANNEL_NOT_AVAILABLE = 3
    INVALID_CHANNEL = 4
    INVALID_VOLTAGE_RANGE = 5
    INVALID_PARAMETER = 6
    CONVERSION_IN_PROGRESS = 7
    COMMUNICATION_FAILED = 8
    OK = 9

    """Settings error strings"""
    strings = {0: "The conversion time parameter is out of range",
               1: "The sample time interval is out of range",
               2: "The conversion time chosen is not fast enough to convert all"
                  " channels within the sample interval",
               3: "The channel being set is valid but not currently available",
               4: "The channel being set is not valid for this device",
               5: "The voltage range being set for this device is not valid",
               6: "One or more parameters are invalid",
               7: "A conversion is in progress for a single asynchronous "
                  "operation",
               8: "Communication failed",
               9: "All settings have been completed successfully"}

    @classmethod
    def get_error_string(cls, error_code):
        """Returns the error message corresponding to the specified error code

        :param error_code: error code to fetch string for
        :type error_code: int
        :return: error message
        :rtype: string
        """

        return cls.strings[error_code]

    @classmethod
    def is_error(cls, error_code):
        """Validates error code

        :param error_code: error code to validate
        :type error_code: int
        :return: True if error code is valid, False otherwise
        :rtype: boolean
        """

        # check if "OK" error code is given
        if error_code is cls.OK:
            return False

        # otherwise it's an error
        return True

class Progress(object):
    """Unit open progress"""

    OPEN_PROGRESS_FAIL = -1
    OPEN_PROGRESS_PENDING = 0
    OPEN_PROGRESS_COMPLETE = 1

class VoltageRange(object):
    """Unit voltage ranges"""

    RANGE_2500_MV = 0
    RANGE_1250_MV = 1
    RANGE_625_MV = 2
    RANGE_313_MV = 3
    RANGE_156_MV = 4
    RANGE_78_MV = 5
    RANGE_39_MV = 6
    RANGE_MIN = RANGE_39_MV
    RANGE_MAX = RANGE_2500_MV

    """Voltage mapping, in [V]"""
    voltages = {RANGE_2500_MV: 2.5, RANGE_1250_MV: 1.25, RANGE_625_MV: 0.625,
                RANGE_313_MV: 0.313, RANGE_156_MV: 0.156, RANGE_78_MV: 0.078,
                RANGE_39_MV: 0.039}

    @classmethod
    def is_valid(cls, vrange):
        """Validates voltage range

        :param vrange: voltage range to validate
        :type vrange: int
        :return: True if voltage range is valid, False otherwise
        :rtype: boolean
        """

        return vrange >= cls.RANGE_MAX and vrange <= cls.RANGE_MIN

    @classmethod
    def get_max_voltage(cls, vrange):
        """Gets the maximum input voltage for the given constant

        :param vrange: constant to fetch voltage for
        :type vrange: int
        :return: voltage
        :rtype: float
        """

        return cls.voltages[vrange]

class InputType(object):
    """Unit input types"""

    DIFFERENTIAL = 0
    # single ended is actually represented by any non-zero C short
    SINGLE = 1

    @classmethod
    def is_valid(cls, itype):
        """Validates input type

        :param itype: input type to validate
        :type itype: int
        :return: True if input type is valid, False otherwise
        :rtype: boolean
        """

        # any integer value is valid, so in the spirit of duck-typing...
        return True

class ConversionTime(object):
    """Unit conversion times"""

    TIME_60MS = 0
    TIME_100MS = 1
    TIME_180MS = 2
    TIME_340MS = 3
    TIME_660MS = 4
    TIME_MIN = TIME_60MS
    TIME_MAX = TIME_660MS

    """Conversion times in ms"""
    times = {TIME_60MS: 60, TIME_100MS: 100, TIME_180MS: 180, TIME_340MS: 340,
             TIME_660MS: 660}

    @classmethod
    def is_valid(cls, conversion_time):
        """Validates conversion time

        :param conversion_time: conversion time to validate
        :type conversion_time: int
        :return: True if conversion time is valid, False otherwise
        :rtype: boolean
        """

        return (conversion_time >= cls.TIME_MIN
                and conversion_time <= cls.TIME_MAX)

    @classmethod
    def get_conversion_time(cls, conversion_time):
        """Gets the conversion time for the given constant

        :param conversion_time: constant to fetch time for
        :type conversion_time: int
        :return: conversion time
        :rtype: float
        """

        return cls.times[conversion_time]

class SampleMethod(object):
    """Unit sample methods"""

    BLOCK = 0
    WINDOW = 1
    STREAM = 2

    @classmethod
    def is_valid(cls, sample_method):
        """Validates sample method

        :param sample_method: sample method to validate
        :type sample_method: int
        :return: True if sample method is valid, False otherwise
        :rtype: boolean
        """

        return sample_method >= cls.BLOCK and sample_method <= cls.STREAM
