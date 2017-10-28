DataLog Package
===============

This package contains modules to access, configure and retrieve data from
PicoLog ADC hardware.

The :mod:`~datalog.data` module provides a :class:`~datalog.data.DataStore`
object to store and query :class:`~datalog.data.Reading` objects.
:class:`~datalog.data.Reading` objects are themselves made up of
:class:`~datalog.data.Sample` objects, containing a single measurement from a
single channel. The :class:`~datalog.data.DataStore` class provides methods to
retrieve data, such as :meth:`~datalog.data.DataStore.json_repr`,
:meth:`~datalog.data.DataStore.csv_repr` and
:meth:`~datalog.data.DataStore.list_repr`, which all support the parameters of
:meth:`~datalog.data.DataStore.get_readings`.

Subpackages
-----------

.. toctree::

    datalog.adc

Submodules
----------

datalog.data module
-------------------

.. automodule:: datalog.data
    :members:
    :undoc-members:
    :show-inheritance:

datalog.device module
---------------------

.. automodule:: datalog.device
    :members:
    :undoc-members:
    :show-inheritance:
