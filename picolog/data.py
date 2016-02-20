import os

from picolog.constants import Channel

"""
Data representation classes.
"""

class Reading(object):
    """Class to represent an ADC reading for a particular time. This contains
    the samples for each active channel in the ADC for a particular time."""

    """Reading time"""
    reading_time = None

    """Channels"""
    channels = None

    """Samples"""
    samples = None

    def __init__(self, reading_time, channels, samples):
        """Initialises a reading

        :param reading_time: the time of this reading
        :param channels: enabled channels, in order
        :param samples: channel samples, in order
        :raises Exception: if channel list and samples list are not the same \
        length
        """

        # set parameters
        self.reading_time = reading_time

        # check channels and samples lists are same length
        if len(channels) is not len(samples):
            raise Exception("Specified channels is not the same length as\
specified samples")

        # store channels
        self.channels = channels

        # create samples list
        self.samples = []

        # store samples
        for (this_channel, this_sample) in zip(channels, samples):
            self.samples.append(Sample(this_channel, this_sample))

class Sample(object):
    """Class to represent a single sample of a single channel."""

    """Channel number"""
    channel = None

    """Value"""
    value = None

    def __init__(self, channel, value):
        """Initialise this sample

        :param channel: the channel number
        :param value: the value of the channel
        :raises ValueError: if channel is invalid
        """

        if Channel.is_valid(channel):
            self.channel = channel
        else:
            raise ValueError("Invalid channel")

        self.value = value

class DataStore(object):
    """Class to store and retrieve ADC readings."""

    """Maximum number of readings to store before overwriting oldest"""
    max_readings = None

    """Readings"""
    readings = None

    def __init__(self):
        """Initialises the datastore"""

        # load config from environment
        self.load_config()

        # initialise list of readings
        self.readings = []

    def load_config(self):
        """Loads configuration options from environment"""

        # maximum readings
        self.max_readings = os.getenv('PICOLOG_DATASTORE_MAX_READINGS', 1000)

    def insert(self, readings):
        """Inserts the specified readings into the datastore

        :param readings: list of readings to insert
        :raises Exception: if a reading time is earlier than an existing reading
        """

        # add each reading, but check it is a later timestamp than the last
        for reading in readings:
            # check the reading time is latest
            if len(self.readings) > 0:
                if reading.reading_time <= self.readings[-1].reading_time:
                    raise Exception("A new reading time is earlier than an existing \
reading time")

            # check length and remove a reading if necessary
            if len(self.readings) >= self.max_readings:
                # delete oldest reading
                del(self.readings[0])

            # everything's ok, so add it to the list
            self.readings.append(reading)

    def find_reading(self, timestamp):
        """Returns the reading matching the specified time

        :param timestamp: the timestamp to find the reading for
        """

        # find reading, or return None if not found
        return next((reading for reading in self.readings \
        if reading.reading_time == timestamp), None)

    def find_readings_after(self, timestamp):
        """Returns the readings after the specified time

        :param timestamp: the timestamp to find readings after
        """

        # return readings with timestamp >= specified timestamp
        return [reading for reading in self.readings if reading.reading_time \
        >= timestamp]

    def find_readings_before(self, timestamp):
        """Returns the readings before the specified time

        :param timestamp: the timestamp to find readings before
        """

        # return readings with timestamp < specified timestamp
        return [reading for reading in self.readings if reading.reading_time \
        < timestamp]
