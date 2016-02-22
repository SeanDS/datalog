Welcome to picolog-adc-python's documentation!
======================================

The `picolog` package contains tools to run and fetch data from PicoLog ADC 20/24 data acquisition hardware. It also contains a server which can run the PicoLog hardware and serve the data it produces to users on a network, and a basic client to connect to such a server and stream data from.

If you're interested in just running a PicoLog ADC 20/24 without any bells and whistles, have a look at the :class:`~picolog.hrdl.adc.PicoLogAdc` class. If you want to run a server which itself runs the ADC hardware, look at the :class:`~picolog.network.Server` class. If you want to connect to an already running server, look at the :class:`~picolog.network.ServerSocket` class.

If you want to contribute something, feel free! Open a pull request, raise an issue or send me an email!

`Sean Leavey <https://github.com/SeanDS>`_

Documentation
-------------

.. toctree::
   :maxdepth: 2

   picolog
   picolog.hrdl
   
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
