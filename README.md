# Python bindings for PicoLog ADC 20/24 (+other goodies)
This is a Python library to interface with a [PicoLog ADC 20/24](https://www.picotech.com/data-logger/adc-20-adc-24/precision-data-acquisition). In addition to Python bindings for some of the features of the C library provided with the device, this package also contains data logging functionality and a client/server library in order to serve the data across a network.

## Prerequisites
Python 2.7+ (not tested with Python 3, but possibly works)

PicoLog ADC 20/24 hardware and driver (libpicohrdl). The driver is not, as of the time of writing, publicly available but can be obtained by [asking the support staff nicely](https://www.picotech.com/support/topic21751.html). You need to connect the hardware and install the driver before using this software, of course.

## Use
The main functionality is implemented in `picolog/hrdl/adc.py` and this class can be used on its own. The documentation should help to get you started. An example of the data server is provided in `examples/server.py`. Just run it in Python with your ADC 20/24 connected.

## Contributing
I welcome contributions to the codebase - just open a pull request!

Sean Leavey  
https://github.com/SeanDS/