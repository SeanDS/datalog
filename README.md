# DataLog: a library for interacting with PicoLog hardware
This is a Python library to interface with [PicoLog ADC hardware](https://www.picotech.com/data-logger/adc-20-adc-24/precision-data-acquisition).
It provides a Python class to interact with the `ADC24`, and data structures
to represent its outputs. The `ADC24` is implemented, but the library is
designed to be easily extended for other PicoLog (and potentially non-PicoLog)
hardware. It may work with the `ADC20` without modification, but this is not
tested.

## Prerequisites
The following requirements must be met before `DataLog` is installed:
  * Python 3.5+
  * PicoLog ADC 20/24 hardware and driver (`libpicohrdl`)

The PicoLog ADC driver can be obtained from
[PicoTech](https://www.picotech.com/downloads/) and must be installed and
working before using this library.

## Installation
Installation is handled by `setup.py`. This is most easily handled by `pip`:
```bash
pip3 install datalog
```
This installs the Python package dependencies automatically. If the above command doesn't make sense, try reading
[this introduction to pip](https://packaging.python.org/tutorials/installing-packages/).

## Use
The documentation should help to get you started. Compile it with:
```bash
cd doc
make html
```
The main functionality is implemented in `datalog/adc/hrdl/picolog.py` and this
class can be used on its own.

### Site-specific use
We use this library at the [University of Glasgow observatory](http://www.astro.gla.ac.uk/observatory/weather/Observatory_weather/Observatory_weather.htm)
for our magnetometer. We have to calibrate the raw counts coming from the
PicoLog unit, as well as upload this data to our FTP server. The set of scripts
we use can be found [here](https://github.com/acrerd/magnetometer).

## Contributing
I welcome contributions to the codebase - just open a pull request!

Sean Leavey  
https://github.com/SeanDS/
