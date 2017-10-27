DataLog documentation
=====================

The `datalog` package contains tools to run and fetch data from PicoLog ADC
20/24 data acquisition hardware. It also contains a server which can run the
PicoLog hardware and serve the data it produces to users on a network.

If you're interested in just running a PicoLog ADC 20/24 without any bells and
whistles, have a look at the :class:`~datalog.adc.hrdl.picolog.PicoLogAdc24`
class. If you want to run a server which itself runs the ADC hardware, look at
:meth:`~datalog.network.run_server`.

If you want to contribute something, feel free! Open a pull request, raise an
issue or send me an email!

`Sean Leavey <https://github.com/SeanDS>`_

Contents
--------

.. toctree::
   :maxdepth: 2

   datalog
   datalog.adc
   datalog.adc.hrdl

Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
