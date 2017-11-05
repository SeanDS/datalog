"""Data representation classes."""

import json
import datetime

# maximum requested readings
MAX_AMOUNT = 1000


class Reading(object):
    """Class to represent a device reading for a particular time. This contains
    the samples for each active channel in the ADC for a particular time."""

    # reading time
    reading_time = None

    # channels
    channels = None

    # samples
    samples = None

    def __init__(self, reading_time, channels, samples):
        """Initialises a reading

        :param reading_time: the timestamp for this reading, in milliseconds
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

    @property
    def reading_date(self):
        """Python datetime object representing this reading's time

        :return: date of this reading's time
        :rtype: :class:`~datetime.datetime`
        """

        return datetime.datetime.utcfromtimestamp(self.reading_time / 1000)

    def __repr__(self):
        """String representation of this reading"""
        return self.csv_repr()

    def list_repr(self):
        """List representation of this reading"""

        # reading time
        message = [self.reading_time]

        # samples
        message.extend([sample.value for sample in self.samples])

        return message

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

        :return: sample generator
        :rtype: Generator[Dict]
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

    # channel number
    channel = None

    # value
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

    # default datastore size
    DEFAULT_SIZE = 1000

    # default number of readings to return
    DEFAULT_AMOUNT = 1000

    def __init__(self, max_size=None, conversion_callbacks=None):
        """Initialises the datastore

        :param max_size: the maximum number of readings to hold in the datastore
        :param conversion_callbacks: list of methods to call on each reading's \
        data
        """

        if max_size is None:
            max_size = self.DEFAULT_SIZE

        if conversion_callbacks is None:
            conversion_callbacks = []

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
        obj.insert_from_dict_list(data)

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
        return "\n".join([reading.csv_repr() for reading in self.get_readings(**options)])

    def list_repr(self, **options):
        """List representation of this datastore"""
        return [reading.csv_repr() for reading in self.get_readings(**options)]

    def json_repr(self, **options):
        """JSON representation of this datastore"""
        return json.dumps([reading.dict_repr() for reading in self.get_readings(**options)])

    def get_readings(self, amount=None, desc=False, pivot_time=None,
                      pivot_after=True):
        """Get readings from datastore given certain filters

        :param amount: maximum number of readings to return
        :type amount: int
        :param desc: descending order (false for ascending)
        :type desc: boolean
        :param pivot_time: time to return data from before or after
        :type pivot_time: int
        :param pivot_after: return times after pivot (false for before)
        :type pivot_after: boolean
        """

        if amount is None:
            amount = self.DEFAULT_AMOUNT

        if pivot_time is None:
            pivot_time = 0

        amount = int(amount)
        desc = bool(desc)
        pivot_time = int(pivot_time)

        # amount cannot exceed MAX_AMOUNT
        if amount > MAX_AMOUNT:
            amount = MAX_AMOUNT
        elif amount < 0:
            amount = 0

        # pivot must be a real timestamp
        if pivot_time < 0:
            pivot_time = 0

        # create pivot function
        if pivot_after:
            fnc_pivot = lambda r: r.reading_time > pivot_time
        else:
            fnc_pivot = lambda r: r.reading_time <= pivot_time

        # get results from pivot
        readings = [reading for reading in self.readings if fnc_pivot(reading)]

        # get ordered result set
        if desc:
            readings = readings[-amount:]
        else:
            readings = readings[:amount]

        return readings

    def get_datetime_grouped_readings(self, *args, **kwargs):
        """Get readings grouped by date

        :param group_date_format: date format to use when grouping readings
        :type group_date_format: str
        """

        # reading list
        readings = self.get_readings(*args, **kwargs)

        groups = {}

        for reading in readings:
            reading_date = reading.reading_date

            if reading_date not in groups:
                # create group
                groups[reading_date] = []

            groups[reading_date].append(reading)

        return groups

    @property
    def num_readings(self):
        return len(self.readings)

    def sample_dict_gen(self):
        """Get dicts containing individual samples, across all channels

        :return: sample generator
        :rtype: Generator[Dict]
        """

        for reading in self.readings:
            yield reading.sample_dict_gen()

    def insert(self, readings):
        """Inserts the specified readings into the datastore

        :param readings: list of readings to insert
        :type readings: List[:class:`~datalog.data.Reading`]
        :raises ValueError: if a reading time is earlier than an existing reading
        """

        # add each reading, but check it is a later timestamp than the last
        for reading in readings:
            # check if reading is invalid: reading time is zero and samples are zero
            if reading.reading_time == 0 and not \
            any([sample for sample in reading.samples if sample.value != 0]):
                continue

            # check the reading time is latest
            if self.readings:
                if reading.reading_time <= self.readings[-1].reading_time:
                    raise ValueError("A new reading time is earlier than or "
                                     "equal to an existing reading time")

            # everything's ok, so add it to the list
            self._insert_reading(reading)

    def _insert_reading(self, reading):
        """Inserts the specified reading, converting it if necessary

        :param reading: reading to insert
        :type reading: :class:`~datalog.data.Reading`
        """

        # call conversion functions
        for fcn in self.conversion_callbacks:
            reading.apply_function(fcn)

        # add reading to storage
        self.readings.append(reading)

        # truncate oversized lists
        while self.num_readings > self.max_size:
            self.readings.pop(0)

    def insert_from_dict_list(self, data, *args, **kwargs):
        """Inserts readings from the specified list of dict objects

        :param data: list containing reading dicts
        :type data: List[Dict]
        """

        # create readings
        readings = [Reading.instance_from_dict(row) for row in data]

        # insert
        self.insert(readings, *args, **kwargs)
