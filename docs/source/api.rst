API Reference
=============

This reference is generated from the docstrings and type annotations of
the source code.

Connection
----------

A connection to an IPMI device is an :class:`pyipmi.Ipmi` object. It is
created for an interface (see :ref:`api-interfaces`) and sends the
requests to its :class:`pyipmi.Target`.

.. autofunction:: pyipmi.create_connection

.. autoclass:: pyipmi.Ipmi
   :members:
   :inherited-members:
   :exclude-members: requester

.. autoclass:: pyipmi.Target
   :members:

.. autoclass:: pyipmi.Routing
   :members:

.. autoclass:: pyipmi.session.Session
   :members:

.. _api-interfaces:

Interfaces
----------

.. autofunction:: pyipmi.interfaces.create_interface

.. autoclass:: pyipmi.interfaces.base.Interface
   :members:

.. autoclass:: pyipmi.interfaces.Rmcp
   :no-members:

.. autoclass:: pyipmi.interfaces.RmcpPlus
   :no-members:

.. autoclass:: pyipmi.interfaces.Ipmitool
   :no-members:

.. autoclass:: pyipmi.interfaces.IpmiDev
   :no-members:

.. autoclass:: pyipmi.interfaces.IpmbDev
   :no-members:

.. autoclass:: pyipmi.interfaces.Aardvark
   :no-members:

.. autoclass:: pyipmi.interfaces.OpenIpmbLink
   :no-members:

Errors
------

.. automodule:: pyipmi.errors
   :members:

Data Types
----------

The classes of the values returned by the commands of
:class:`pyipmi.Ipmi`, grouped by the module of the command group.

pyipmi.bmc
^^^^^^^^^^

.. automodule:: pyipmi.bmc
   :exclude-members: Bmc

pyipmi.chassis
^^^^^^^^^^^^^^

.. automodule:: pyipmi.chassis
   :exclude-members: Chassis

pyipmi.dcmi
^^^^^^^^^^^

.. automodule:: pyipmi.dcmi
   :exclude-members: Dcmi

pyipmi.event
^^^^^^^^^^^^

.. automodule:: pyipmi.event
   :exclude-members: Event

pyipmi.fru
^^^^^^^^^^

.. automodule:: pyipmi.fru
   :exclude-members: Fru

pyipmi.hpm
^^^^^^^^^^

.. automodule:: pyipmi.hpm
   :exclude-members: Hpm

pyipmi.lan
^^^^^^^^^^

.. automodule:: pyipmi.lan
   :exclude-members: Lan

pyipmi.messaging
^^^^^^^^^^^^^^^^

.. automodule:: pyipmi.messaging
   :exclude-members: Messaging

pyipmi.picmg
^^^^^^^^^^^^

.. automodule:: pyipmi.picmg
   :exclude-members: Picmg

pyipmi.sdr
^^^^^^^^^^

.. automodule:: pyipmi.sdr
   :exclude-members: Sdr

pyipmi.sel
^^^^^^^^^^

.. automodule:: pyipmi.sel
   :exclude-members: Sel

pyipmi.sensor
^^^^^^^^^^^^^

.. automodule:: pyipmi.sensor
   :exclude-members: Sensor

pyipmi.vita
^^^^^^^^^^^

.. automodule:: pyipmi.vita
   :exclude-members: Vita
