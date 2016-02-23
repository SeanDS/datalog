from __future__ import print_function, division

import sys
import time

from picolog.network import ServerSocket

"""
PicoLog data printer example. Requires a running server.

Run with `python datastream.py <host> <port>`
"""

def print_usage():
    """Prints usage instructions"""

    # print instructions
    print("Usage: python stream-from-server.py <host> <port>")

    # exit program
    exit(0)

def convert_to_list(csv):
    """Converts a simple CSV-like string to a list"""

    # empty data
    data = []

    # loop over lines
    for line in csv.split("\n"):
        # append list containing columns
        data.append(line.split(","))

    return data

# get arguments
try:
    host = sys.argv[1]
    port = int(sys.argv[2])
except:
    print_usage()

# create a new server socket instance
server = ServerSocket(host, port)

# get sample time, in ms
sample_time = int(server.get_command_response("sampletime"))

# set sleep time
sleep_time = 10

# default timestamp
timestamp = 0

# now loop, printing the data received from the ADC
while True:
    # get data
    data = server.get_command_response("dataafter {0}".format(timestamp))

    # convert data to CSV
    csv = convert_to_list(data)

    # update timestamp with latest timestamp
    if len(csv) > 0:
        timestamp = csv[-1][0]
        print(data)

    # sleep for one reading
    time.sleep(sleep_time)
