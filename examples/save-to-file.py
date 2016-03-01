from __future__ import print_function, division

import sys
import time

from picolog.network import ServerSocket
from picolog.constants import Channel

"""
PicoLog data printer example. Requires a running server.

Run with `python datastream.py <host> <port>`
"""

def print_usage():
    """Prints usage instructions"""

    # print instructions
    print("Usage: python save-to-file.py <host> <port>")

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

def convert_to_csv(data):
    """Converts a list to CSV"""
    
    # one-liner
    return "\n".join([",".join([str(column) for column in row]) for row in data])

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

# check buffer length is adequate
# number of channels in ADC * length of a long int in string form + commas and newline required
if server.buffer_length < Channel.MAX_ANALOG_CHANNEL * 11 + Channel.MAX_ANALOG_CHANNEL + 1:
    raise Exception("The socket buffer length must be long enough to receive at least one complete reading")

# get enabled channels
channels = server.get_command_response("enabledchannels").split(",")

# number of enabled channels
enabled_channels = len(channels)

# get channel conversion factors
conversion = []

for channel in channels:
    conversion.append(float(server.get_command_response("voltsconversion {0}".format(channel))))

# open file
with open(sys.argv[3], "a") as f:
    # the length of the last line of the data payload
    last_line_length = None
    
    # now loop, printing the data received from the ADC
    while True:
        # get data
        data = server.get_command_response("dataafter {0}".format(timestamp))
        
        # only do something if the data is useful
        if data is not None:
            # convert data to CSV
            datalist = convert_to_list(data)

            # check if we have data and it is valid
            if datalist is None or len(datalist) == 0:
                print("Data appears to be invalid: {0}".format(data))
                
                continue
            
            # check if buffer length has been reached
            if len(datalist) >= 2 and len(datalist[-1]) is not len(datalist[-2]):
                # last row doesn't have the same number of columns as second last
                # this indicates the buffer length was reached
                # discard last row (it will be fetched next time)
                del(datalist[-1])
            
            # loop over data, converting the counts to volts
            for i in xrange(len(datalist)):
                # check the length is consistent (enabled_channels + 1 to include time)
                if len(datalist[i]) is not enabled_channels + 1:
                    print("Number of samples in reading {0} is not consistent with enabled channels".format(i))
                    
                    continue
                
                # scale to volts
                readings = [int(sample) * factor for sample, factor in zip(datalist[i], conversion)]

                # save the readings
                datalist[i][1:] = readings
            
            # update timestamp
            timestamp = datalist[-1][0]
            
            # write data to file
            f.write(convert_to_csv(datalist) + "\n")
        else:
            print("Skipped empty data from server. Timestamp: {0}, received data: {1}".format(timestamp, data))

        # sleep for one reading
        time.sleep(sleep_time)
