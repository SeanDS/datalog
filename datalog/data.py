import os
import json

"""Data representation classes."""

# maximum requested readings
MAX_AMOUNT = 1000

class Reading(object):
    """Class to represent a device reading for a particular time. This contains
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
            raise Exception("Specified channels is not the same length as "
                            "specified samples")

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

    @classmethod
    def instance_from_json(cls, json_str):
        """Returns a new instance of the reading using the specified \
        JSON-encoded string

        :param json_str: JSON-encoded data
        """

        return cls.instance_from_dict(json.loads(json_str))

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

        self.channel = int(channel)
        self.value = float(value)

    def __repr__(self):
        """String representation of this sample"""

        return "Channel {0} value: {1}".format(self.channel, self.value)

    def dict_repr(self):
        """Dict representation of this sample"""

        return {'channel': self.channel, 'value': self.value}

class DataStore(object):
    """Class to store and retrieve ADC readings."""

    # default number of readings to return
    DEFAULT_AMOUNT = 1000

    def __init__(self, max_size, conversion_callbacks=[]):
        """Initialises the datastore

        :param max_size: the maximum number of readings to hold in the datastore
        :param conversion_callbacks: list of methods to call on each reading's \
        data
        """

        self.max_size = int(max_size)
        self.conversion_callbacks = list(conversion_callbacks)

        # initialise readings as a queue
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

        # new object with the same max length
        obj = self.__class__(self.max_size)

        # add the existing readings
        obj.insert(readings)

        # return
        return obj

    def __repr__(self):
        """String representation of this datastore"""
        return self.csv_repr()

    def csv_repr(self, **options):
        """CSV representation of this datastore"""
        return "\n".join([reading.csv_repr() for reading in self._get_readings(**options)])

    def list_repr(self, **options):
        """List representation of this datastore"""
        return [reading.csv_repr() for reading in self._get_readings(**options)]

    def json_repr(self, **options):
        """JSON representation of this datastore"""
        return json.dumps([reading.dict_repr() for reading in self._get_readings(**options)])

    def _get_readings(self, amount=None, desc=False, pivot_time=0,
                      pivot_after=True):
        """Get readings from datastore given certain filters

        :param amount: maximum number of readings to return
        :param desc: descending order (false for ascending)
        :param pivot_time: time to return data from before or after
        :param pivot_after: return times after pivot (false for before)
        """

        if amount is None:
            amount = self.DEFAULT_AMOUNT

        amount = int(amount)
        desc = bool(desc)
        pivot_time = int(pivot_time)

        # amount cannot exceed MAX_AMOUNT
        if amount > MAX_AMOUNT:
            amount = MAX_AMOUNT

        # pivot must be a real timestamp
        if pivot_time < 0:
            pivot_time = 0

        # create pivot function
        if pivot_after:
            fnc_pivot = lambda r: r.reading_time > pivot_time
        else:
            fnc_pivot = lambda r: r.reading_time <= pivot_time

        # get ordered result set
        if desc:
            readings = self.readings[-amount:]
        else:
            readings = self.readings[:amount]

        # get results from pivot
        readings = [reading for reading in readings if fnc_pivot(reading)]

        return readings

    def sample_dict_gen(self):
        """List of dicts containing individual samples, across all channels

        Returns a generator.
        """

        # FIXME: can this instead use list comprehension?
        for reading in self.readings:
            yield reading.sample_dict_gen()

    def insert(self, readings):
        """Inserts the specified readings into the datastore

        :param readings: list of readings to insert
        :raises Exception: if a reading time is earlier than an existing reading
        """

        # add each reading, but check it is a later timestamp than the last
        for reading in readings:
            # check if reading is invalid: reading time is zero and samples are zero
            if reading.reading_time == 0 and not \
            any([sample for sample in reading.samples if sample.value != 0]):
                continue

            # check the reading time is latest
            if len(self.readings) > 0:
                if reading.reading_time <= self.readings[-1].reading_time:
                    raise Exception("A new reading time is earlier than or "
                                    "equal to an existing reading time")

            # everything's ok, so add it to the list
            self._insert_reading(reading)

    def _insert_reading(self, reading):
        """Inserts the specified reading, converting it if necessary

        :param reading: reading to insert
        """

        # call conversion functions
        map(reading.apply_function, self.conversion_callbacks)

        # add reading to storage
        self.readings.append(reading)

        # check max length
        if len(self.readings) >= self.max_size:
            # delete oldest entries
            self.readings = self.readings[-self.max_size:]

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
        readings = self.filtered_instance([reading for reading \
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
