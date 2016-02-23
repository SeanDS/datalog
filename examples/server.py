import sys

from picolog.network import Server

"""
PicoLog data logging/communication server example.
"""

# get server instance
server = Server(*sys.argv[1:])

try:
    # start server
    server.start()
except:
    server._adc.close_unit()
    # close open sockets if necessary
    if server.socket_open():
        server.stop()

    # raise the original exception
    raise
