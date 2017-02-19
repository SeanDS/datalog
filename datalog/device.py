"""Abstract data logging device classes"""

import abc


class Device(object, metaclass=abc.ABCMeta):
    """Abstract DataLog device"""

    def __init__(self):
        pass

    @abc.abstractmethod
    def is_open(self):
        """Checks if the device is open"""
        raise NotImplemented()

    @abc.abstractmethod
    def close(self):
        """Close the device"""
        raise NotImplemented()

    @abc.abstractmethod
    def stream(self):
        """Stream from the device"""
        raise NotImplemented()

    @abc.abstractmethod
    def ready(self):
        """Check if readings are available to retrieve from the device"""
        raise NotImplemented()

    def get_readings(self):
        """Get readings from the device"""
        raise NotImplemented()
