class Handle(object):
    UNIT_NOT_OPENED = -1
    UNIT_NOT_FOUND  = 0

    @classmethod
    def is_valid_handle(cls, handle):
        if isinstance(handle, int):
            if handle > cls.UNIT_NOT_FOUND:
                return True

        return False

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
    def get_error_string(cls, error):
        return cls.strings[error]

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
