class Handle(object):
    UNIT_NOT_OPENED = -1
    UNIT_NOT_FOUND  = 0

    @classmethod
    def is_valid_handle(cls, handle):
        if isinstance(handle, int):
            if handle > cls.UNIT_NOT_FOUND:
                return True

        return False

class Channel(object):
    ANALOG_CHANNEL_1    = 1
    ANALOG_CHANNEL_2    = 2
    ANALOG_CHANNEL_3    = 3
    ANALOG_CHANNEL_4    = 4
    ANALOG_CHANNEL_5    = 5
    ANALOG_CHANNEL_6    = 6
    ANALOG_CHANNEL_7    = 7
    ANALOG_CHANNEL_8    = 8
    ANALOG_CHANNEL_9    = 9
    ANALOG_CHANNEL_10   = 10
    ANALOG_CHANNEL_11   = 11
    ANALOG_CHANNEL_12   = 12
    ANALOG_CHANNEL_13   = 13
    ANALOG_CHANNEL_14   = 14
    ANALOG_CHANNEL_15   = 15
    ANALOG_CHANNEL_16   = 16
    MIN_ANALOG_CHANNEL  = ANALOG_CHANNEL_1
    MAX_ANALOG_CHANNEL  = ANALOG_CHANNEL_16

    @classmethod
    def is_valid(cls, channel):
        """Checks whether the specified channel is valid"""
        return channel >= cls.MIN_ANALOG_CHANNEL and \
        channel <= cls.MAX_ANALOG_CHANNEL

class Info(object):
    DRIVER_VERSION        = 0
    USB_VERSION           = 1
    HARDWARE_VERSION      = 2
    VARIANT_INFO          = 3
    BATCH_AND_SERIAL      = 4
    CAL_DATE              = 5
    KERNEL_DRIVER_VERSION = 6
    ERROR                 = 7
    SETTINGS_ERROR        = 8

    """Info formats"""
    formats = {0: "Driver version: {0}", 1: "USB version: {0}", \
    2: "Hardware version: {0}", 3: "Unit variant: {0}", \
    4: "Batch and serial: {0}", 5: "Calibration date: {0}", \
    6: "Kernel driver version: {0}", 7: "Error code: {0}", \
    8: "Settings error: {0}"}

    @classmethod
    def is_valid_constant(cls, constant):
        """Checks if specified constant is valid

        :param constant: constant to validate
        :return: True if valid, False otherwise"""

        if constant >= cls.DRIVER_VERSION and constant <= cls.SETTINGS_ERROR:
            return True

        return False

    @classmethod
    def get_info_constants(cls):
        return range(cls.DRIVER_VERSION, cls.SETTINGS_ERROR + 1)

    @classmethod
    def format(cls, info, info_type):
        """Formats the specified info using the specified info type

        :param info: the unformatted info string
        :param info_type: the info constant
        :return: formatted info string
        """

        return cls.formats[info_type].format(info)

class Error(object):
    OK                       = 0
    KERNEL_DRIVER_TOO_OLD    = 1
    UNIT_NOT_FOUND           = 2
    FIRMWARE_CONFIG_FAIL     = 3
    OS_NOT_SUPPORTED         = 4
    MAX_DEVICES_ALREADY_OPEN = 5

    """Error strings"""
    strings = {0: "OK", 1: "Kernel driver too old", 2: "Unit not found", \
    3: "Firmware config failure", 4: "OS not supported", \
    5: "Maximum devices already open"}

    @classmethod
    def get_error_string(cls, error_code):
        return cls.strings[error_code]

    @classmethod
    def is_error(cls, error_code):
        """Checks if the given error code represents an error"""

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
    CONVERSION_TIME_OUT_OF_RANGE = 0
    SAMPLE_INTERVAL_OUT_OF_RANGE = 1
    CONVERSION_TIME_TOO_SLOW     = 2
    CHANNEL_NOT_AVAILABLE        = 3
    INVALID_CHANNEL              = 4
    INVALID_VOLTAGE_RANGE        = 5
    INVALID_PARAMETER            = 6
    CONVERSION_IN_PROGRESS       = 7
    COMMUNICATION_FAILED         = 8
    OK                           = 9

    """Settings error strings"""
    strings = {0: "The conversion time parameter is out of range", \
    1: "The sample time interval is out of range", \
    2: "The conversion time chosen is not fast enough to convert all channels \
within the sample interval", 3: "The channel being set is valid but not \
currently available", 4: "The channel being set is not valid for this \
device", 5: "The voltage range being set for this device is not valid", \
    6: "One or more parameters are invalid", 7: "A conversion is in progress \
for a single asynchronous operation", 8: "Communication failed", \
    9: "All settings have been completed successfully"}

    @classmethod
    def get_error_string(cls, error_code):
        return cls.strings[error_code]

    @classmethod
    def is_error(cls, error_code):
        """Checks if the given settings error code represents an error"""

        # check if "OK" error code is given
        if error_code is cls.OK:
            return False

        # otherwise it's an error
        return True

class Status(object):
    INVALID = 0
    VALID   = 1

    @classmethod
    def is_valid_status(cls, status):
        """Checks if specified status is valid

        :param status: status to validate
        :return: True if valid, False otherwise"""

        if status is cls.VALID:
            return True

        return False

class Progress(object):
    OPEN_PROGRESS_FAIL     = -1
    OPEN_PROGRESS_PENDING  = 0
    OPEN_PROGRESS_COMPLETE = 1

class VoltageRange(object):
    RANGE_2500_MV = 0
    RANGE_1250_MV = 1
    RANGE_625_MV  = 2
    RANGE_313_MV  = 3
    RANGE_156_MV  = 4
    RANGE_78_MV   = 5
    RANGE_39_MV   = 6
    RANGE_MIN = RANGE_39_MV
    RANGE_MAX = RANGE_2500_MV

    @classmethod
    def is_valid(cls, vrange):
        """Checks if the specified range is valid"""
        return vrange >= cls.RANGE_MAX and vrange <= cls.RANGE_MIN

class InputType(object):
    DIFFERENTIAL = 0
    # single ended is actually represented by any non-zero C short
    SINGLE       = 1

    @classmethod
    def is_valid(cls, itype):
        """Checks if the specified input range is valid"""
        # any integer value is valid, so in the spirit of duck-typing...
        return True

class ConversionTime(object):
    TIME_60MS  = 0
    TIME_100MS = 1
    TIME_180MS = 2
    TIME_340MS = 3
    TIME_660MS = 4
    TIME_MIN   = TIME_60MS
    TIME_MAX   = TIME_660MS

    @classmethod
    def is_valid(cls, conversion_time):
        """Checks if the specified conversion time is valid"""
        return conversion_time >= cls.TIME_MIN \
        and conversion_time <= cls.TIME_MAX
