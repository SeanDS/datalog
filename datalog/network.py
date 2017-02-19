import logging
import socket
import io
import selectors
import threading
import time
import re
from contextlib import contextmanager

"""ADC networking tools."""

"""Regular expressions"""
REGEX_OBJ = {
    "dataafter": re.compile("dataafter.*?(\\d{1,})"),
    "voltsconversion": re.compile("voltsconversion.*?(\\d{1,2})")
}

@contextmanager
def get_server(*args, **kwargs):
    # create server
    server = Server(*args, **kwargs)

    # listen for commands over the network
    server.start()

    # yield the server inside a try/finally block to handle any
    # unexpected events
    try:
        # return the server to the caller
        yield server
    finally:
        # stop the thread and wait until it finishes
        server.stop()
        logging.getLogger("network").debug("Waiting for server to stop")
        server.join()
        logging.getLogger("network").info("Server stopped")

class Server(threading.Thread):
    """Server to govern the ADC's data logging and storage, as well as to serve \
    connected clients.

    The server binds to a port and accepts text commands on that port. Clients
    can request data and other server information.
    """

    """EOF string used by Client._send_with_eof"""
    EOF_STRING = "\0"

    def __init__(self, config, retriever):
        """Initialises the server"""

        # initialise threading
        threading.Thread.__init__(self)

        self.config = config
        self.retriever = retriever

    @property
    def socket_buf_len(self):
        return int(self.config["server"]["socket_buf_len"])

    @property
    def max_readings_per_request(self):
        return int(self.config["server"]["max_readings_per_request"])

    def run(self):
        """Binds the server to the preconfigured socket"""

        # bind to socket
        try:
            self._bind()
        except socket.error as e:
            # convert socket error into an exception
            raise Exception(e)

        # listen for connections
        self._listen()

        # set running
        self.server_running = True

        logging.getLogger("network").info("Server started")

        # clients list
        self._clients = []

        # set server running flag (used by stop method)
        self.server_running = True

        # create selector to interface with OS
        with selectors.DefaultSelector() as sel:
            # register the connection handler for when a client connects
            sel.register(self._socket, selectors.EVENT_READ, self.handle_connection)

            while self.server_running:
                # select events, with a 1 second maximum wait
                events = sel.select(timeout=1)

                # loop over events, if any
                for key, _ in events:
                    # run the callback
                    key.data()

        # close clients
        self._close_clients()

        # close socket
        self._unbind()

    def stop(self):
        """Stops the server"""

        self.server_running = False

    def handle_connection(self):
        # handle a request on the socket
        client = Client(self, *self._socket.accept())

        # start client thread
        client.start()

        logging.getLogger("server").debug("New client from "
                                          "{0}".format(client.address))

        # add client to list
        self._clients.append(client)

    def _close_clients(self):
        """Closes client connections"""

        for client in self._clients:
            logging.getLogger("server").debug("Stopping client {0}".format(client))
            client.stop()

    def _bind(self):
        """Binds the server to the preconfigured socket"""

        # instantiate socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        host = self.config["server"]["host"]
        port = int(self.config["server"]["port"])

        # bind the socket to the preconfigured host and port
        self._socket.bind((host, port))

        logging.getLogger("server").info("Server bound to {0} on port "
                                         "{1}".format(host, port))

    def _unbind(self):
        """Unbinds the server from the socket"""
        self._socket.close()

    def is_socket_open(self):
        """Checks if socket is open"""
        return self._socket is True

    def _listen(self):
        """Starts listening to the socket for a connection"""

        # listen for connections up to the preconfigured maximum
        self._socket.listen(int(self.config["server"]["max_connections"]))

    def timestamp(self):
        """Returns the current server timestamp in milliseconds"""
        return int(round(time.time() * 1000))

    def device_stream_start_timestamp(self):
        return int(self.retriever.start_time)

class Client(threading.Thread):
    """Client able to handle simple commands"""

    def __init__(self, server, connection, address):
        """Initialises the client

        :param server: server associated with the client connection
        :param connection: the connection object to send/receive commands
        :param address: the address of the client
        """

        # call thread init
        threading.Thread.__init__(self)

        self.server = server
        self.connection = connection
        self.address = address

    def __str__(self):
        return "<{0}>".format(str(self.address))

    def __repr__(self):
        return str(self)

    def run(self):
        """Runs the client thread"""

        # receive and handle message
        self.handle(self.connection.recv(self.server.socket_buf_len).decode("utf-8"))

    def stop(self):
        # close client connection
        self.connection.close()

    def handle(self, data):
        """Handles a request made across the socket

        :param data: data sent by client
        """

        logging.getLogger("client").debug("Received message: "
                                          "\"{0}\"".format(data))

        try:
            if data == "timestamp":
                self.send_timestamp()
            elif data == "starttimestamp":
                self.send_stream_start_timestamp()
            elif data.startswith("dataafter"):
                self.handle_command_data_after(data)
            elif data.startswith("voltsconversion"):
                self.handle_command_volts_conversion(data)
        except Exception as e:
            logging.getLogger("client").error(str(e))
            self.send_error_message(str(e))

        # close connection
        self.stop()

        logging.getLogger("client").debug("Connection closed")

    def _send(self, message):
        """Sends the specified message to the client ending with the predefined \
        EOF string

        :param message: message to send
        """

        self.connection.send("{0}{1}".format(message, Server.EOF_STRING).encode("utf-8"))

    def send_error_message(self, message):
        """Sends the client the specified error message

        :param message: error message
        """

        self._send(message)

    def send_timestamp(self):
        """Sends the current timestamp to the connected client"""
        logging.getLogger("client").debug("Sending timestamp")
        self._send(str(self.server.timestamp()))

    def send_stream_start_timestamp(self):
        """Sends the stream start timestamp to the connected client"""
        logging.getLogger("client").debug("Sending stream start timestamp")
        self._send(str(self.server.device_stream_start_timestamp()))

    def handle_command_data_after(self, data):
        """Handles a 'dataafter' command

        The command should be "dataafter <time> <buffer length>" where <time> \
        is a valid time in milliseconds. If the specified timestamp is invalid, \
        an exception is raised.

        :param data: data sent by client
        :raises Exception: if timestamp is invalid
        """

        # match timestamp in data
        search = REGEX_OBJ["dataafter"].search(data)

        # if no matches, raise exception
        if search is None:
            raise Exception("Could not find valid timestamp in request")

        # get the timestamp
        timestamp = int(search.group(1))

        # send the data
        self.send_data_after(timestamp)

    def send_data_after(self, timestamp):
        """Sends the data collected since the specified timestamp

        :param timestamp: timestamp to send data since
        """

        # get readings
        datastore = self.server.retriever.datastore.find_readings_after( \
            timestamp,
            max_readings=self.server.max_readings_per_request)

        # send readings
        self._send(datastore.json_repr())

    def handle_command_volts_conversion(self, data):
        """Handles a 'voltsconversion' command

        The command should be "voltsconversion <channel>" where <channel> is a
        channel number. If the specified channel number is invalid, an \
        exception is raised.

        :param data: data sent by client
        :raises Exception: if channel is invalid
        """

        # match channel in data
        search = REGEX_OBJ["voltsconversion"].search(data)

        # if no matches, raise exception
        if search is None:
            raise Exception("Could not find valid channel in request")

        # otherwise get the channel
        channel = int(search.group(1))

        # send the data
        self.send_conversion_factor(channel)

    def send_conversion_factor(self, channel):
        """Sends the voltage conversion factor for the specified channel

        :param channel: the channel to fetch the conversion for
        """

        # FIXME: implement this!
        self._send("not implemented yet")

class ServerSocket(object):
    """Provides a socket interface to the ADC server."""

    def __init__(self, host, port, buffer_length=4096, timeout=5):
        """Initialises the socket server
        :param host: the host to connect to
        :param port: the port to connect to
        :param buffer: the buffer length to use to receive server responses
        :param timeout: the time to wait for the server to finish responding \
        before raising an exception
        """

        # set parameters
        self.host = host
        self.port = int(port)
        self.buffer_length = int(buffer_length)
        self.timeout = int(timeout)

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
        This function correctly handles the EOF character sent by the server.
        :param command: the command to send to the server
        :raises Exception: if server times out
        """

        # get connection
        connection = self.get_connection()

        # send command
        connection.sendall(command.encode("utf-8"))

        # empty client message
        message = ""

        # start time
        start_time = time.time()

        while True:
            # get next chunk
            message += connection.recv(self.buffer_length).decode("utf-8")

            # check for EOF
            if message[-1] is Server.EOF_STRING:
                # we've found the EOF, so break, after removing the EOF character
                message = message[:-1]

                break

            # check for timeout
            if time.time() - start_time > self.timeout:
                raise Exception("Server timed out")

        # close socket
        connection.close()

        return message
