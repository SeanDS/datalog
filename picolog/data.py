from __future__ import print_function

import os
import json

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
        self.reading_time = int(reading_time)

        # check channels and samples lists are same length
        if len(channels) is not len(samples):
            raise Exception("Specified channels is not the same length as\
specified samples")

        # store channels
        self.channels = list(channels)

        # create samples list
        self.samples = []

        # store samples
        for this_channel, this_sample in zip(channels, samples):
            self.samples.append(Sample(this_channel, this_sample))

    def __repr__(self):
        """String representation of this reading"""
        return self.csv_repr()

    def list_repr(self):
        """List representation of this reading"""

        # reading time
        str = [self.reading_time]

        # samples
        str.extend([sample.value for sample in self.samples])

        return str

    def csv_repr(self):
        """CSV representation of this reading"""

        # convert ints to strings and join
        return ",".join([str(item) for item in self.list_repr()])

    def whitespace_repr(self):
        """Whitespace-separated representation of this reading"""

        # convert list to space-separated string
        return " ".join([str(item) for item in self.list_repr()])

    def dict_repr(self):
        """Dictionary representation of this reading"""

        return {"reading_time": self.reading_time, "channels": self.channels, \
        "samples": [sample.dict_repr() for sample in self.samples]}

    def json_repr(self):
        """JSON representation of this reading"""
        return json.dumps(self.dict_repr())

    def sample_dict_gen(self):
        """List of dicts containing individual samples

        Returns a generator.
        """

        for sample in self.samples:
            # get representation
            representation = sample.dict_repr()

            # add the timestamp
            representation['timestamp'] = self.reading_time

            # yield the new dict
            yield representation

    @classmethod
    def instance_from_dict(cls, ddict):
        """Returns a new instance of the reading using the specified dict

        :param ddict: dict of data
        """

        # generate sample values
        values = [sample["value"] for sample in ddict["samples"]]

        # return new object
        return cls(ddict["reading_time"], ddict["channels"], values)

    def apply_function(self, function):
        """Applies the specified function to the samples in this reading

        :param function: function to apply to samples
        """

        # call function
        output = function([sample.value for sample in self.samples])

        # save the function outputs back into the samples
        for sample, new_value in zip(self.samples, output):
            sample.value = new_value

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

        self.value = float(value)

    def __repr__(self):
        """String representation of this sample"""

        return "Channel {0} value: {1}".format(self.channel, self.value)

    def dict_repr(self):
        """Dict representation of this sample"""

        return {'channel': self.channel, 'value': self.value}

class DataStore(object):
    """Class to store and retrieve ADC readings."""

    """Number of readings to store"""
    reading_storage_length = None

    """Whether to increase buffer for new readings beyond storage limit, or \
    delete old ones"""
    increase_buffer = None

    """Conversion callback methods"""
    conversion_callbacks = None

    """Readings"""
    readings = None

    def __init__(self, reading_storage_length, increase_buffer=False, \
    conversion_callbacks=[]):
        """Initialises the datastore

        :param reading_storage_length: the maximum number of readings to hold \
        in the datastore
        :param increase_buffer: increase the buffer to fit the new data
        :param conversion_callbacks: list of methods to call on each reading's \
        data
        """

        # set parameters
        self.reading_storage_length = int(reading_storage_length)
        self.increase_buffer = increase_buffer
        self.conversion_callbacks = conversion_callbacks

        # initialise list of readings
        self.readings = []

    @classmethod
    def instance_from_json(cls, json_str, *args, **kwargs):
        """Returns a new instance of the datastore using the specified JSON \
        encoded data

        :param json_str: JSON-encoded data
        """

        # decode JSON readings
        data = json.loads(json_str)

        # create a new instance
        obj = cls(len(data), *args, **kwargs)

        # set readings
        obj.insert_from_json_list(data)

        # return
        return obj

    def instance_with_readings(self, readings):
        """Returns a new instance of datastore with the specified readings

        :param readings: list of readings
        """

        # new object
        obj = self.__class__(self.reading_storage_length)

        # set readings
        obj.insert(readings)

        # return
        return obj

    def __repr__(self):
        """String representation of this datastore"""
        return self.csv_repr()

    def csv_repr(self):
        """CSV representation of this datastore"""
        return "\n".join([reading.csv_repr() for reading in self.readings])

    def list_repr(self):
        """List representation of this datastore"""
        return [reading.csv_repr() for reading in self.readings]

    def json_repr(self):
        """JSON representation of this datastore"""
        return json.dumps([reading.dict_repr() for reading in self.readings])

    def sample_dict_gen(self):
        """List of dicts containing individual samples, across all channels

        Returns a generator.
        """

        for reading in self.readings:
            yield reading.sample_dict_gen()

    def insert(self, readings):
        """Inserts the specified readings into the datastore

        :param readings: list of readings to insert
        :raises Exception: if a reading time is earlier than an existing reading
        """

        # add each reading, but check it is a later timestamp than the last
        for reading in readings:
            # check if reading is not valid - reading is zero and samples are zero
            if reading.reading_time == 0 and not \
            any([sample for sample in reading.samples if sample.value != 0]):
                continue

            # check the reading time is latest
            if len(self.readings) > 0:
                if reading.reading_time <= self.readings[-1].reading_time:
                    raise Exception("A new reading time is earlier than an \
existing reading time")

            # check length and remove a reading if necessary
            if len(self.readings) >= self.reading_storage_length:
                if self.increase_buffer:
                    # increment buffer count
                    self.reading_storage_length += 1
                else:
                    # delete oldest reading
                    del(self.readings[0])

            # everything's ok, so add it to the list
            self._insert_reading(reading)

    def _insert_reading(self, reading):
        """Inserts the specified reading, converting it if necessary

        :param reading: reading to insert
        """

        # call conversion functions
        map(lambda func: reading.apply_function(func), self.conversion_callbacks)

        # add reading to storage
        self.readings.append(reading)

    def insert_from_json_list(self, data, *args, **kwargs):
        """Inserts readings from the specified dict

        :param data: list containing reading dicts
        """

        # create readings
        readings = [Reading.instance_from_dict(row) for row in data]

        # insert
        self.insert(readings, *args, **kwargs)

    def find_reading(self, timestamp):
        """Returns the reading matching the specified time

        :param timestamp: the timestamp to find the reading for
        """

        # find reading, or return None if not found
        return next((reading for reading in self.readings \
        if reading.reading_time == timestamp), None)

    def find_readings_after(self, timestamp, max_readings=None):
        """Returns a new datastore containing readings after the specified time

        :param timestamp: the timestamp to find readings after
        :param max_readings: maximum number of readings to return
        """

        # sanitise max readings
        if max_readings is not None:
            max_readings = int(max_readings)

        # create new datastore containing readings with timestamp >= specified timestamp
        readings = self.instance_with_readings([reading for reading \
        in self.readings if reading.reading_time > timestamp])

        # remove readings up to max
        readings.readings = readings.readings[:max_readings]

        # return datastore
        return readings

    def find_readings_before(self, timestamp, max_readings=None):
        """Returns a new datastore containing readings before the specified time

        :param timestamp: the timestamp to find readings before
        :param max_readings: maximum number of readings to return
        """

        # sanitise max readings
        if max_readings is not None:
            max_readings = int(max_readings)

        # create new datastore containing readings with timestamp < specified timestamp
        readings = self.instance_with_readings([reading for reading in self.readings \
        if reading.reading_time <= timestamp])

        # remove readings up to max
        readings.readings = readings.readings[:max_readings]

        # return datastore
        return readings
