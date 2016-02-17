from __future__ import print_function, division

import os
import sys
import socket
import select
import threading
import time
import re

from picolog.hrdl.adc import PicoLogAdc
from picolog.constants import Channel

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

    """Whether to print errors"""
    print_errors = None

    """Error prefix"""
    error_prefix = None

    """Socket object"""
    _socket = None

    """Command strings"""
    command = {"timestamp": "timestamp", "datasince": "datasince"}

    """Regular expressions"""
    regex = {"datasince": "datasince.*?(\\d{13,})"}
    regex_objects = None

    """Backlog time limit"""
    backlog_limit = None

    """Server running status, used by threads"""
    server_running = None

    """Connected clients"""
    _clients = None

    def __init__(self, host, port, max_connections=5, print_info=True, \
    print_errors=True, info_prefix="[info]", error_prefix="[error]"):
        """Initialises the server

        :param host: host to bind server to
        :param port: port to bind server to
        :param max_connections: maximum number of simultaneous connections to \
        accept
        :param print_errors: whether to print logger errors to stream
        :param error_prefix: the prefix to use for errors
        """

        # set settings
        self.host = host
        self.port = int(port)
        self.max_connections = int(max_connections)
        self.print_errors = bool(print_errors)
        self.error_prefix = error_prefix

        # compile regex
        self.compile_regex()

        # load environment configuration
        self.load_config()

    def load_config(self):
        """Loads environment configuration"""

        # socket buffer length
        self.socket_buffer_length = os.getenv(\
        "PICOLOG_SIMPLE_SERVER_SOCKET_BUFFER_LENGTH", 1000)

        # allowed time (in ms) backlog data can be requested
        self.backlog_limit = os.getenv("PICOLOG_SIMPLE_SERVER_BACKLOG_LIMIT", \
        1000 * 60 * 60 * 24)

    def compile_regex(self):
        """Compiles built-in regex strings into Python regular expression \
        objects"""

        # create dict if not yet created
        if self.regex_objects is None:
            self.regex_objects = {}

        # compile each regex string
        for name, regex in self.regex.items():
            self.regex_objects[name] = re.compile(regex)

    def start(self):
        """Opens a connection to the ADC and binds the server to the \
        preconfigured socket"""

        # start ADC
        self._start_adc()

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
        self.close_clients()

        # close socket
        self._socket.close()

        # close ADC
        #self._adc.close()

        print("Bye")

    def close_clients(self):
        """Closes client connections"""

        if self._clients is not None:
            for client in self._clients:
                client.stop()

    def get_timestamp(self):
        """Returns the current server timestamp in milliseconds"""
        return int(round(time.time() * 1000))

    def _start_adc(self):
        """Opens the ADC as many times as necessary"""
        pass

    def _bind(self):
        """Binds the server to the preconfigured socket"""

        # instantiate socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind the socket to the preconfigured host and port
        self._socket.bind((self.host, self.port))

        print("Server bound to {0} on port {1}".format(self.host, self.port))

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

        print("Connection {0} from {1}".format(connection, address))

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

        print("Received data: {0}".format(data))

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
        print("Sending timestamp")
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

        if (self.server.get_timestamp() - timestamp) \
         > self.server.backlog_limit:
            raise Exception("Cannot request data from that long ago")

        self.connection.send("data since {0}".format(timestamp))

if __name__ == "__main__":
    server = Server(*sys.argv[1:])

    try:
        server.start()
    except:
        if server.socket_open():
            server.stop()
        raise
