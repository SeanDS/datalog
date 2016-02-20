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
        logging.StreamHandler.__init__(self)

        # turn of default stream
        self.stream = None

        # set parameters
        self.info_stream = info_stream
        self.error_stream = error_stream

    def emit(self, record):
        # check if log level is at least error
        if record.levelno >= logging.ERROR:
            # send to error stream
            self.__emit(record, self.error_stream)
        else:
            # send to info stream
            self.__emit(record, self.info_stream)

    def __emit(self, record, strm):
        # set the specified stream
        self.stream = strm

        # emit the log
        logging.StreamHandler.emit(self, record)
