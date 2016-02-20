from __future__ import print_function, division

import os
import sys
import socket
import select
import threading
import time
import re
import ConfigParser

from picolog.hrdl.adc import PicoLogAdc
from picolog.constants import Channel, VoltageRange, InputType

"""
Simple networking tools.
"""

class Server(object):
    """Server which binds to a port and accepts text commands on that port. \
    Connected clients can request data and other server information."""

    """Host to bind to"""
    host = None

    """Port to bind to"""
    port = None

    """Maximum number of simultaneous connections"""
    max_connections = None

    """Whether to print errors, warnings and info"""
    print_info = None
    print_warnings = None
    print_errors = None

    """Print prefixes"""
    info_prefix = None
    warning_prefix = None
    error_prefix = None

    """Socket object"""
    _socket = None

    """ADC object"""
    _adc = None

    """Command strings"""
    command = {"timestamp": "timestamp", "datasince": "datasince"}

    """Regular expressions"""
    regex = {"datasince": "datasince.*?(\\d{13,})"}
    regex_objects = None

    """Maximum ADC connection attempts"""
    max_adc_connection_attempts = None

    """Minimum delay, in s, between ADC connection attempts"""
    min_adc_reconnection_delay = None

    """Server running status, used by threads"""
    server_running = None

    """Connected clients"""
    _clients = None

    """ADC channel configuration"""
    channel_config = None

    """Default ADC channel configuration"""
    default_channel_config = {"channel": -1, "enabled": False, "range": \
    VoltageRange.RANGE_2500_MV, "type": InputType.SINGLE}

    def __init__(self, host="localhost", port=50000, channel_config_path=None, \
    max_connections=5, print_info=True, print_warnings=True, \
    print_errors=True, info_prefix="[info]", warning_prefix="[warning]", \
    error_prefix="[error]"):
        """Initialises the server

        :param host: host to bind server to
        :param port: port to bind server to
        :param channel_config_file: ADC channel configuration path
        :param max_connections: maximum number of simultaneous connections to \
        accept
        :param print_errors: whether to print logger errors to stream
        :param error_prefix: the prefix to use for errors
        """

        # arguments
        self.host = host
        self.port = int(port)
        self.max_connections = int(max_connections)
        self.print_info = bool(print_info)
        self.print_warnings = bool(print_warnings)
        self.print_errors = bool(print_errors)
        self.info_prefix = info_prefix
        self.warning_prefix = warning_prefix
        self.error_prefix = error_prefix

        # load environment configuration
        self.load_env_config()

        # compile regex
        self.compile_regex()

        # parse configuration
        self.parse_channel_config(channel_config_path)

        self.info("Server ready to be started")

    def load_env_config(self):
        """Loads environment configuration"""

        self.info("Loading environment configuration")

        # socket buffer length
        self.socket_buffer_length = os.getenv( \
        "PICOLOG_SERVER_SOCKET_BUFFER_LENGTH", 1000)

        # max ADC connection attempts
        self.max_adc_connection_attempts = os.getenv( \
        "PICOLOG_SERVER_MAX_ADC_CONNECTION_ATTEMPTS", 10)

        # minimum ADC reconnection delay
        self.min_adc_reconnection_delay = os.getenv( \
        "PICOLOG_SERVER_MIN_ADC_RECONNECTION_DELAY", 0.5)

    def error(self, message):
        """Prints the specified error message

        :param message: error message to print
        """

        # print only if allowed
        if self.print_errors:
            self._print_message(message, self.error_prefix)

    def warning(self, message):
        """Prints the specified warning message

        :param message: warning message to print
        """

        # print only if allowed
        if self.print_warnings:
            self._print_message(message, self.warning_prefix)

    def info(self, message):
        """Prints the specified info message

        :param message: info message to print
        """

        # print only if allowed
        if self.print_info:
            self._print_message(message, self.info_prefix)

    def _print_message(self, message, prefix=""):
        """Prints the specified message with an optional prefix to stdout

        :param message: message to print
        :param prefix: prefix for message
        """

        print("{0} {1}".format(prefix, message))

    def parse_channel_config(self, channel_config_path):
        """Parses the channel configuration found in the specified path

        :param channel_config_path: path to channel configuration file
        """

        self.info("Parsing channel config")

        # create channel config dict
        self.channel_config = {}

        # tell user if there are no active channels
        if channel_config_path is None:
            # no channels to parse
            self.warning("No channels are active. Cowardly carrying on.")

            return

        # instantiate parser
        parser = ConfigParser.RawConfigParser(self.default_channel_config)

        # parse
        parser.read(channel_config_path)

        # save config sections as channels
        self.channel_config = parser.sections()

    def compile_regex(self):
        """Compiles built-in regex strings into Python regular expression \
        objects"""

        self.info("Compiling regex handlers")

        # create dict if not yet created
        if self.regex_objects is None:
            self.regex_objects = {}

        # compile each regex string
        for name, regex in self.regex.items():
            self.regex_objects[name] = re.compile(regex)

    def start(self):
        """Opens a connection to the ADC and binds the server to the \
        preconfigured socket"""

        self.info("Starting server")

        # open ADC
        self._open_adc()

        # configure ADC
        self._configure_adc()

        # bind to socket
        self._bind()

        # listen for connections
        self._listen()

        # set running
        self.server_running = True

        # clients list
        self._clients = []

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

        self.stop()

    def stop(self):
        """Closes all open connections, including to the ADC"""

        # close clients
        self._close_clients()

        # close socket
        self._socket.close()

        # close ADC
        self._close_adc()

        self.info("Bye")

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
        adc = PicoLogAdc()

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
                if attempts >= self.max_adc_connection_attempts:
                    raise Exception("Could not open ADC after {0} attempt(s). \
Last error: {1}".format(attempts, e))

            # wait exponentially longer than last time
            delay = self.min_adc_reconnection_delay * attempts ** 2

            self.warning("Could not connect to ADC. Waiting {0}s before next \
attempt".format(delay))

            time.sleep(delay)

        # save ADC object
        self._adc = adc

    def _configure_adc(self):
        """Configures the ADC using preconfigured settings"""

        # activate channels
        for channel in self.channel_config:
            self._adc.set_analog_in_channel(channel["channel"], \
            channel["enabled"], channel["range"], channel["type"])

    def _bind(self):
        """Binds the server to the preconfigured socket"""

        # instantiate socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind the socket to the preconfigured host and port
        self._socket.bind((self.host, self.port))

        self.info("Server bound to {0} on port {1}".format(self.host, self.port))

    def _listen(self):
        """Starts listening to the socket for a connection"""

        # listen for connections up to the preconfigured maximum
        self._socket.listen(self.max_connections)

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
        # call thread init
        threading.Thread.__init__(self)

        self.server = server
        self.connection = connection
        self.address = address

        self.info("Connection {0} from {1}".format(connection, address))

    def run(self):
        """Runs the client thread"""

        # receive message
        data = self.connection.recv(self.server.socket_buffer_length)

        self._handle(data)

    def stop(self):
        self.connection.close()

    def _handle(self, data):
        """Handles a request made across the socket

        :param data: data sent by client
        """

        self.info("Received data: {0}".format(data))

        try:
            if data == self.server.command["timestamp"]:
                self._send_timestamp()
            elif data.startswith(self.server.command["datasince"]):
                self._handle_command_data_since(data)
        except Exception, e:
            self._send_error_message(e)

        print("Closing connection")
        self.connection.close()

    def _send_error_message(self, message):
        """Sends the client the specified error message

        :param message: error message
        """

        self.connection.send("{0} {1}".format(self.server.error_prefix, message))

    def _send_timestamp(self):
        """Sends the current timestamp to the connected client

        """
        self.info("Sending timestamp")
        self.connection.send(str(self.server.get_timestamp()))

    def _handle_command_data_since(self, data):
        """Handles a 'datasince' command

        The command should be "datasince <timestamp>" where <timestamp> is a
        valid UNIX timestamp in milliseconds. It must meet certain length
        criteria as defined in the regex expression the timestamp is checked
        against. If the specified timestamp is invalid, an exception is raised.

        :param data: data sent by client
        :raises Exception: if timestamp is invalid
        """

        # match timestamp in data
        search = self.server.regex_objects[\
        self.server.command["datasince"]].search(data)

        # if no matches, raise exception
        if search is None:
            raise Exception("Could not find valid timestamp in request")

        # otherwise get the timestamp
        timestamp = int(search.group(1))

        # send the data
        self._send_data_since(timestamp)

    def _send_data_since(self, timestamp):
        """Sends the data collected since the specified timestamp

        :param timestamp: timestamp to send data since
        :raises Exception: if timestamp is too far in the past
        """

        self.connection.send("data since {0}".format(timestamp))

if __name__ == "__main__":
    server = Server(*sys.argv[1:])

    try:
        server.start()
    except:
        if server.socket_open():
            server.stop()
        raise
