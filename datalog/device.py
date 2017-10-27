"""Abstract data logging device classes"""

import abc


class Device(object, metaclass=abc.ABCMeta):
    """Abstract DataLog device"""

    def __init__(self):
        pass

    @abc.abstractmethod
    def is_open(self):
        """Checks if the device is open"""
        return NotImplemented

    @abc.abstractmethod
    def close(self):
        """Close the device"""
        return NotImplemented

    @abc.abstractmethod
    def stream(self):
        """Stream from the device"""
        return NotImplemented

    @abc.abstractmethod
    def ready(self):
        """Check if readings are available to retrieve from the device"""
        return NotImplemented

    @abc.abstractmethod
    def get_readings(self):
        """Get readings from the device"""
        return NotImplemented
