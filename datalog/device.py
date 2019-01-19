"""Abstract data logging device classes"""

import abc
import logging
from . import __version__

# logger
logger = logging.getLogger("datalog")


class Device(object, metaclass=abc.ABCMeta):
    """Abstract DataLog device"""

    def __init__(self):
        logger.info("Init datalog %s" % __version__)

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
