import logging

"""
Useful classes for logging.
"""

class LevelBasedHandler(logging.StreamHandler):
    """Handler for separate logging streams based on log levels.

    Logs errors (and above) to the specified error stream and anything else to
    the specified info stream.
    """

    """Info stream"""
    info_stream = None

    """Error stream"""
    error_stream = None

    def __init__(self, info_stream, error_stream):
        """Initialises the level based log handler

        :param info_stream: the stream to post info messages to
        :param error_stream: the stream to post error messages to
        """

        # inialise standard stream handler
        logging.StreamHandler.__init__(self)

        # turn of default stream
        self.stream = None

        # set parameters
        self.info_stream = info_stream
        self.error_stream = error_stream

    def emit(self, record):
        """Emit a log record to a particular stream based on log level

        :param record: log record
        """

        # check if log level is at least error
        if record.levelno >= logging.ERROR:
            # send to error stream
            self.__emit(record, self.error_stream)
        else:
            # send to info stream
            self.__emit(record, self.info_stream)

    def __emit(self, record, stream):
        """Private emit method to call parent's emit method

        :param record: log record
        :param stream: log stream to send record to
        """

        # set the specified stream
        self.stream = stream

        # emit the log
        logging.StreamHandler.emit(self, record)
