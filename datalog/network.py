import time
import logging
import json
from bottle import route, request, run, get, abort

import datalog
from datalog.adc.config import AdcConfig

# fetch configuration
config = AdcConfig()

# datastore object used for REST requests
datastore = None

# server start time
start_time = None

def run_server(ds):
    global datastore, start_time

    # save datastore
    datastore = ds

    # start it
    logging.getLogger("rest-server").info("Starting web server")

    # set start time
    start_time = int(round(time.time() * 1000))

    # create server
    run(host=config["server"]["host"], port=int(config["server"]["port"]))

    logging.getLogger("rest-server").info("Web server stopped")

@route('/earliest')
def earliest():
    return handle_fixed_list(desc=False, **data_query_args())

@route('/latest')
def latest():
    return handle_fixed_list(desc=True, **data_query_args())

@route('/before/<time:int>')
def before(time):
    try:
        return handle_fixed_list(pivot_time=time, pivot_after=False,
                                 **data_query_args())
    except TypeError as e:
        abort(400, "Invalid parameter")

@route('/after/<time:int>')
def after(time):
    try:
        return handle_fixed_list(pivot_time=time, pivot_after=True,
                                 **data_query_args())
    except TypeError as e:
        abort(400, "Invalid parameter")

@route('/info')
def info():
    global start_time

    fmt = request.query.get("fmt", default=DEFAULT_FORMAT)

    # uptime
    up_time = int(round(time.time() * 1000)) - start_time

    data = {
        "server_version": datalog.__version__,
        "start_time": start_time,
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
    global datastore

    if fmt == "json":
        return datastore.json_repr(*args, **kwargs)
    elif fmt == "csv":
        return datastore.csv_repr(*args, **kwargs)
    else:
        abort(400, "Invalid format")

def data_query_args():
    fmt = request.query.get("fmt", default=config["server"]["default_format"])
    amount = request.query.get("amount",
                               default=config["server"]["default_readings_per_request"])

    return {
        "fmt": fmt,
        "amount": amount
    }
