"""RESTful network data server"""

import time
import logging
import json
from bottle import route, request, run, abort

import datalog
from datalog.adc.config import AdcConfig

# fetch configuration
CONFIG = AdcConfig()

# datastore object used for REST requests
DATASTORE = None

# server start time
START_TIME = None

def run_server(datastore):
    """Start server

    :param datastore: datastore to serve
    :type datastore: :class:`~datalog.data.DataStore`
    """

    global DATASTORE, START_TIME

    # save datastore
    DATASTORE = datastore

    # start it
    logging.getLogger("rest-server").info("Starting web server")

    # set start time
    START_TIME = int(round(time.time() * 1000))

    # create server
    run(host=CONFIG["server"]["host"], port=int(CONFIG["server"]["port"]))

    logging.getLogger("rest-server").info("Web server stopped")

@route('/earliest')
def earliest():
    """Get earliest readings in datastore

    :return: formatted data
    :rtype: string
    """

    return handle_fixed_list(desc=False, **data_query_args())

@route('/latest')
def latest():
    """Get latest readings in datastore

    :return: formatted data
    :rtype: string
    """

    return handle_fixed_list(desc=True, **data_query_args())

@route('/before/<pivot_time:int>')
def before(pivot_time):
    """Get readings before a certain time in datastore

    :param pivot_time: time to get readings before
    :type pivot_time: int
    :return: formatted data
    :rtype: string
    """

    try:
        return handle_fixed_list(pivot_time=pivot_time, pivot_after=False,
                                 **data_query_args())
    except TypeError:
        abort(400, "Invalid parameter")

@route('/after/<pivot_time:int>')
def after(pivot_time):
    """Get readings after a certain time in datastore

    :param pivot_time: time to get readings after
    :type pivot_time: int
    :return: formatted data
    :rtype: string
    """

    try:
        return handle_fixed_list(pivot_time=pivot_time, pivot_after=True,
                                 **data_query_args())
    except TypeError:
        abort(400, "Invalid parameter")

@route('/info')
def info():
    """Get server info

    :return: formatted server info
    :rtype: string
    """

    global START_TIME

    fmt = request.query.get("fmt", default=CONFIG["server"]["default_format"])

    # uptime
    up_time = int(round(time.time() * 1000)) - START_TIME

    data = {
        "server_version": datalog.__version__,
        "start_time": START_TIME,
        "up_time": up_time
    }

    if fmt == "json":
        return json.dumps(data)
    elif fmt == "csv":
        return "\n".join(["\"{}\",\"{}\"".format(key, val)
                          for key, val in data.items()])
    else:
        abort(400, "Invalid format")

def handle_fixed_list(fmt, *args, **kwargs):
    """Generate a string representation of the data given specified filters

    :param fmt: data format
    :type fmt: string
    :return: formatted data
    :rtype: string
    """

    global DATASTORE

    if fmt == "json":
        return DATASTORE.json_repr(*args, **kwargs)
    elif fmt == "csv":
        return DATASTORE.csv_repr(*args, **kwargs)
    else:
        abort(400, "Invalid format")

def data_query_args():
    """Extract query arguments

    :return: collection of query keys and values
    :rtype: dict
    """

    fmt = request.query.get("fmt", default=CONFIG["server"]["default_format"])
    amount = request.query.get("amount",
                               default=CONFIG["server"]["default_readings_per_request"])

    return {
        "fmt": fmt,
        "amount": amount
    }
