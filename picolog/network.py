from __future__ import print_function, division

import os
import sys
import logging
import socket
import select
import threading
import time
import re
import ConfigParser

from picolog.hrdl.adc import PicoLogAdc
from picolog.fetch import Retriever
from picolog.data import DataStore
from picolog.logstream import LevelBasedHandler
from picolog.constants import Channel, VoltageRange, InputType, ConversionTime

"""
ADC networking tools.
"""

class Server(object):
    """Server to govern the ADC's data logging and storage, as well as to serve \
    connected clients.

    The server binds to a port and accepts text commands on that port. Clients
    can request data and other server information.
    """

    """Configuration"""
    config = None

    """ADC channel configuration"""
    channel_config = None

    """Logger object"""
    logger = None

    """Socket object"""
    _socket = None

    """ADC object"""
    _adc = None

    """Retriever (to fetch stuff from ADC) object"""
    _retriever = None

    """Command strings"""
    command = {"timestamp": "timestamp", "dataafter": "dataafter", \
    "streamstarttimestamp": "streamstarttimestamp", "sampletime": "sampletime", \
    "enabledchannels": "enabledchannels", "voltsconversion": "voltsconversion"}

    """Regular expressions"""
    regex = {"dataafter": "dataafter.*?(\\d{1,})", \
        "voltsconversion": "voltsconversion.*?(\\d{1,2})"}
    regex_objects = None

    """Server running status, used by threads"""
    server_running = None

    """ADC datastore object"""
    datastore = None

    """Connected clients"""
    _clients = None

    def __init__(self, config_path=None, channel_config_path=None, \
    info_stream=sys.stdout, error_stream=sys.stderr):
        """Initialises the server

        :param config_path: configuration path
        :param channel_config_file: ADC channel configuration path
        :param info_stream: stream to write info to
        :param error_stream: stream to write errors to
        """

        # parse configuration
        self.parse_config(config_path)

        # create logger (now that we have the config)
        self._create_logger(info_stream, error_stream)

        # parse the channel config
        self.parse_channel_config(channel_config_path)

        # compile regex
        self.compile_regex()

        self.logger.info("Server ready to be started")

    def _create_logger(self, info_stream, error_stream):
        """Creates a logger using the specified streams

        :param info_stream: the stream to post information to
        :param error_stream: the stream to post errors to
        """

        # create logger instance
        self.logger = logging.getLogger('PicoLogServer')

        # set minimum level
        self.logger.setLevel(logging.INFO)

        # set OS-specific logging black holes if necessary
        if info_stream is None:
            info_stream = open(os.devnull, "w")
        if error_stream is None:
            error_stream = open(os.devnull, "w")

        # create log stream handler
        log_handler = LevelBasedHandler(info_stream, error_stream)
        log_handler.setLevel(logging.INFO)

        # set formatter
        formatter = logging.Formatter(self.config["server"]["log_format"])
        log_handler.setFormatter(formatter)

        # add stream handler to logger
        self.logger.addHandler(log_handler)

    def parse_config(self, config_path):
        """Parses the configuration found in the specified path

        :param config_path: the path to the configuration file
        """

        # create the config object
        parser = ConfigParser.RawConfigParser()

        # first of all, parse the default configuration
        parser.read(os.path.dirname(os.path.realpath(__file__)) + os.path.sep + \
        "config" + os.path.sep + "config.default")

        # next, parse the user-defined configuration if present
        if config_path:
            parser.read(config_path)

        # store only the dict produced by the config parser
        self.config = {section: dict(parser.items(section)) \
        for section in parser.sections()}

        # force some types
        self.config["server"]["port"] = int(self.config["server"]["port"])
        self.config["server"]["max_connections"] = \
        int(self.config["server"]["max_connections"])
        self.config["adc"]["conversion_time"] = \
        int(self.config["adc"]["conversion_time"])
        self.config["adc"]["sample_time"] = \
        float(self.config["adc"]["sample_time"])
        self.config["adc"]["socket_buffer_length"] = \
        int(self.config["adc"]["socket_buffer_length"])
        self.config["adc"]["fetch_delay"] = \
        float(self.config["adc"]["fetch_delay"])
        self.config["adc"]["max_adc_connection_attempts"] = \
        int(self.config["adc"]["max_adc_connection_attempts"])
        self.config["adc"]["min_adc_reconnection_delay"] = \
        float(self.config["adc"]["min_adc_reconnection_delay"])
        self.config["adc"]["hrdl_string_buffer_length"] = \
        int(self.config["adc"]["hrdl_string_buffer_length"])
        self.config["adc"]["hrdl_sample_buffer_length"] = \
        int(self.config["adc"]["hrdl_sample_buffer_length"])
        self.config["datastore"]["max_readings"] = \
        int(self.config["datastore"]["max_readings"])

    def parse_channel_config(self, channel_config_path):
        """Parses the channel configuration found in the specified path

        :param channel_config_path: path to channel configuration file
        """

        self.logger.info("Parsing channel config")

        # instantiate parser
        parser = ConfigParser.RawConfigParser()

        # first of all, parse the default configuration
        parser.read(os.path.dirname(os.path.realpath(__file__)) + os.path.sep + \
        "config" + os.path.sep + "channel_config.default")

        # next, parse the user-defined configuration if present
        if channel_config_path:
            parser.read(channel_config_path)
        else:
            # no user-defined channel settings
            self.logger.warning("No user-defined channel configuration found. \
Cowardly carrying on.")

        # store only the dict produced by the config parser
        self.channel_config = {section: dict(parser.items(section)) \
        for section in parser.sections()}

    def compile_regex(self):
        """Compiles built-in regex strings into Python regular expression \
        objects"""

        self.logger.info("Compiling regex handlers")

        # create dict if not yet created
        if self.regex_objects is None:
            self.regex_objects = {}

        # compile each regex string
        for name, regex in self.regex.items():
            self.regex_objects[name] = re.compile(regex)

    def start(self):
        """Opens a connection to the ADC and binds the server to the \
        preconfigured socket"""

        self.logger.info("Starting server")

        # open ADC
        self._open_adc()

        # configure ADC
        self._configure_adc()

        # start ADC recording
        self._stream_adc()

        # bind to socket
        try:
            self._bind()
        except socket.error, e:
            # convert socket error into an exception
            raise Exception(e)

        # listen for connections
        self._listen()

        # set running
        self.server_running = True

        # clients list
        self._clients = []

        # let user know how to stop server
        print("Press return to stop server", file=sys.stdout)

        # main run loop
        while self.server_running:
            # create queue of waitable objects
            inputready, _, _ = select.select(\
            [self._socket, sys.stdin], [], [])

            for i in inputready:
                if i is self._socket:
                    # handle a request on the socket
                    client = Client(self, *self._socket.accept())

                    # start thread
                    client.start()

                    # add client to list
                    self._clients.append(client)
                elif i is sys.stdin:
                    # handle input on stdin
                    sys.stdin.readline()

                    # an input has been detected on stdin, so stop server
                    self.server_running = False

        # stop server
        self.stop()

    def _stream_adc(self):
        """Starts the ADC in stream (continuous measurement) mode

        Also records the timestamp corresponding to the start of the stream.
        """

        # create a new datastore
        self.datastore = DataStore(self.config["datastore"]["max_readings"])

        # create a new data retriever
        self._retriever = Retriever(self._adc, self.datastore, \
        self.config["adc"]["fetch_delay"])

        # start retrieval thread
        self._retriever.start()

    def stop(self):
        """Closes all open connections, including to the ADC"""

        # stop ADC streaming
        self._retriever.stop()

        # close clients
        self._close_clients()

        # close socket
        self._socket.close()

        # close ADC
        self._close_adc()

        self.logger.info("Bye")

    def _close_clients(self):
        """Closes client connections"""

        if self._clients is not None:
            for client in self._clients:
                client.stop()

    def _close_adc(self):
        """Closes the ADC"""

        if self._adc is not None:
            self._adc.close_unit()

    def get_timestamp(self):
        """Returns the current server timestamp in milliseconds"""
        return int(round(time.time() * 1000))

    def _open_adc(self):
        """Opens the ADC as many times as necessary"""

        # ADC object
        adc = PicoLogAdc(self.config["adc"]["hrdl_library_path"], \
        self.config["adc"]["hrdl_string_buffer_length"], \
        self.config["adc"]["hrdl_sample_buffer_length"], logger=self.logger)

        # connection attempts
        attempts = 0

        while True:
            # attempt to open ADC
            try:
                # increment attempts
                attempts += 1

                # open ADC
                adc.open_unit()

                # exit loop
                break
            except Exception, e:
                # ADC reported issue

                # check if we're out of attempts
                if attempts >= self.config["adc"]["max_adc_connection_attempts"]:
                    raise Exception("Could not open ADC after {0} attempt(s). \
Last error: {1}".format(attempts, e))

            # wait exponentially longer than last time
            delay = self.config["adc"]["min_adc_reconnection_delay"] \
            * attempts ** 2

            self.logger.warning("Could not connect to ADC. Waiting {0}s before next \
attempt".format(delay))

            time.sleep(delay)

        # save ADC object
        self._adc = adc

    def _configure_adc(self):
        """Configures the ADC using preconfigured settings"""

        # activate channels
        for index in self.channel_config:
            # get channel dict
            channel = self.channel_config[index]

            self._adc.set_analog_in_channel(int(channel["channel"]), \
            bool(channel["enabled"]), int(channel["range"]), int(channel["type"]))

        # set sample time, converting from s to ms
        self._adc.set_sample_time(int(self.config["adc"]["sample_time"] * 1000), \
        self.config["adc"]["conversion_time"])

    def _bind(self):
        """Binds the server to the preconfigured socket"""

        # instantiate socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind the socket to the preconfigured host and port
        self._socket.bind((self.config["server"]["host"], \
        self.config["server"]["port"]))

        self.logger.info("Server bound to {0} on port {1}".format( \
        self.config["server"]["host"], self.config["server"]["port"]))

    def _listen(self):
        """Starts listening to the socket for a connection"""

        # listen for connections up to the preconfigured maximum
        self._socket.listen(self.config["server"]["max_connections"])

    def socket_open(self):
        """Checks if socket is open"""
        return self._socket is True

class Client(threading.Thread):
    """Client able to handle simple commands"""

    """Server object"""
    server = None

    """Connection object"""
    connection = None

    """Client address"""
    address = None

    def __init__(self, server, connection, address):
        """Initialises the client

        :param server: the server this client is connected to
        :param connection: the connection object to send/receive commands
        :param address: the address of the client
        """

        # call thread init
        threading.Thread.__init__(self)

        self.server = server
        self.connection = connection
        self.address = address

        self.server.logger.debug("Connection from {0}".format(address))

    def run(self):
        """Runs the client thread"""

        # receive message
        data = self.connection.recv( \
        self.server.config["adc"]["socket_buffer_length"])

        self._handle(data)

    def stop(self):
        self.connection.close()

    def _handle(self, data):
        """Handles a request made across the socket

        :param data: data sent by client
        """

        self.server.logger.debug("Received message: \"{0}\"".format(data))

        try:
            if data == self.server.command["timestamp"]:
                self._send_timestamp()
            elif data == self.server.command["sampletime"]:
                self._send_adc_sample_time()
            elif data == self.server.command["streamstarttimestamp"]:
                self._send_stream_start_timestamp()
            elif data == self.server.command["enabledchannels"]:
                self._send_enabled_channels()
            elif data.startswith(self.server.command["dataafter"]):
                self._handle_command_data_after(data)
            elif data.startswith(self.server.command["voltsconversion"]):
                self._handle_command_volts_conversion(data)
        except Exception, e:
            self.server.logger.error(str(e))
            self._send_error_message(str(e))

        self.connection.close()

        self.server.logger.debug("Connection closed")

    def _send_error_message(self, message):
        """Sends the client the specified error message

        :param message: error message
        """

        self.connection.send(message)

    def _send_timestamp(self):
        """Sends the current timestamp to the connected client"""
        self.server.logger.debug("Sending timestamp")
        self.connection.send(str(self.server.get_timestamp()))

    def _send_stream_start_timestamp(self):
        """Sends the stream start timestamp to the connected client"""
        self.server.logger.debug("Sending stream start timestamp")
        self.connection.send(str(self.server._adc.stream_start_timestamp))

    def _send_enabled_channels(self):
        """Sends a comma separated list of the enabled channels"""
        self.server.logger.debug("Sending list of enabled channels")
        self.connection.send(",".join([str(channel) for channel in self.server._adc.enabled_channels]))

    def _send_adc_sample_time(self):
        """Sends the ADC sample time"""
        self.server.logger.debug("Sending ADC sample time")
        self.connection.send(str(self.server._adc.sample_time))

    def _handle_command_data_after(self, data):
        """Handles a 'dataafter' command

        The command should be "dataafter <time>" where <time> is a
        valid time in milliseconds. If the specified timestamp is invalid, an \
        exception is raised.

        :param data: data sent by client
        :raises Exception: if timestamp is invalid
        """

        # match timestamp in data
        search = self.server.regex_objects[\
        self.server.command["dataafter"]].search(data)

        # if no matches, raise exception
        if search is None:
            raise Exception("Could not find valid timestamp in request")

        # otherwise get the timestamp
        timestamp = int(search.group(1))

        # send the data
        self._send_data_after(timestamp)

    def _send_data_after(self, timestamp):
        """Sends the data collected since the specified timestamp

        :param timestamp: timestamp to send data since
        """

        self.connection.send( \
        self.server.datastore.find_readings_after(timestamp).json_repr())

    def _handle_command_volts_conversion(self, data):
        """Handles a 'voltsconversion' command

        The command should be "voltsconversion <channel>" where <channel> is a
        channel number. If the specified channel number is invalid, an \
        exception is raised.

        :param data: data sent by client
        :raises Exception: if channel is invalid
        """

        # match channel in data
        search = self.server.regex_objects[\
        self.server.command["voltsconversion"]].search(data)

        # if no matches, raise exception
        if search is None:
            raise Exception("Could not find valid channel in request")

        # otherwise get the channel
        channel = int(search.group(1))

        # send the data
        self._send_conversion_factor(channel)

    def _send_conversion_factor(self, channel):
        """Sends the voltage conversion factor for the specified channel

        :param channel: the channel to fetch the conversion for
        """

        self.connection.send( \
        str(self.server._adc.get_volts_conversion(channel)))

class ServerSocket(object):
    """Provides a socket interface to the ADC server."""

    """Host"""
    host = None

    """Port"""
    port = None

    """Response receive buffer size"""
    buffer_length = None

    def __init__(self, host, port, buffer_length=65536):
        """Initialises the socket server

        :param host: the host to connect to
        :param port: the port to connect to
        :param buffer: the buffer length to use to receive server responses
        """

        # set parameters
        self.host = host
        self.port = port
        self.buffer_length = buffer_length

    def get_connection(self):
        """Returns a new connection to the server"""

        # get socket
        s = self.get_socket()

        # connect using preconfigured host and port
        s.connect((self.host, self.port))

        return s

    def get_socket(self):
        """Returns a new socket for internet communication"""

        return socket.socket()

    def get_command_response(self, command):
        """Connects to the server, sends it the specified command and returns \
        the response

        :param command: the command to send to the server
        """

        # get connection
        connection = self.get_connection()

        # send command
        connection.send(command)

        # return response
        return connection.recv(self.buffer_length)
