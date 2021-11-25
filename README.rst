Pure Python IPMI Library
========================

|BuildStatus| |PyPiVersion| |Documentation| |PyPiPythonVersions| |Coveralls| |CodeClimate| |Codacy|

Features
--------
* native RMCP interface
* legacy RMCP interface (using ipmitool)
* IPMB interface using the `Total Phase`_ Aardvark
* IPMB interface using ipmb-dev driver on Linux

Tested Devices
--------------
* Kontron mTCA Carrier Manager
* Kontron CompactPCI boards
* Pigeon Point Shelf Manager
* HPE iLO3/iLO4
* N.A.T. NAT-MCH
* DESY MMC STAMP & related AMCs (DAMC-FMC2ZUP, DAMC-FMC1Z7IO)

Requirements
------------

For IPMB interface a `Total Phase`_ Aardvark is needed.
Another option is to use ipmb-dev driver on Linux with an I2C bus, driver of which supports slave mode:
https://www.kernel.org/doc/html/latest/driver-api/ipmb.html

Installation
------------

Using ``pip``
'''''''''''''

The recommended installation method is using
`pip <http://pip-installer.org>`__::

    pip install python-ipmi

Manual installation
'''''''''''''''''''

Download the source distribution package for the library. Extract the the package to
a temporary location and install::

    python setup.py install

Documentation
-------------

You can find the most up to date documentation at:
http://python-ipmi.rtfd.org

Example
-------

Below is an example that shows how to setup the interface and the connection
using the `ipmitool`_ as backend with both network and serial interfaces.

Example with lan interface:

.. code:: python

    import pyipmi
    import pyipmi.interfaces

    # Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
    interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='lan')

    connection = pyipmi.create_connection(interface)

    connection.target = pyipmi.Target(0x82)
    connection.target.set_routing([(0x81,0x20,0),(0x20,0x82,7)])

    connection.session.set_session_type_rmcp('10.0.0.1', port=623)
    connection.session.set_auth_type_user('admin', 'admin')
    connection.session.establish()

    connection.get_device_id()

ipmitool command:

.. code:: shell

    ipmitool -I lan -H 10.0.0.1 -p 623 -U "admin" -P "admin" -t 0x82 -b 0 -l 0 raw 0x06 0x01


Example with serial interface:

.. code:: python

    import pyipmi
    import pyipmi.interfaces

    interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='serial-terminal')

    connection = pyipmi.create_connection(interface)

    connection.target = pyipmi.Target(0xb2)

    # set_session_type_serial(port, baudrate)
    connection.session.set_session_type_serial('/dev/tty2', 115200)
    connection.session.establish()

    connection.get_device_id()

ipmitool command:

.. code:: shell

    ipmitool -I serial-terminal -D /dev/tty2:115200 -t 0xb2 -l 0 raw 0x06 0x01

Compatibility
-------------

Both Python 2.7 and Python 3.x are currently supported.

Contributing
------------

Contributions are always welcome. You may send patches directly (eg. ``git
send-email``), do a github pull request or just file an issue.

* respect the coding style (eg. PEP8),
* provide well-formed commit message (see `this blog post
  <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.)
* add a Signed-off-by line (eg. ``git commit -s``)

License
-------

This library is free software; you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation; either version 2.1 of the License, or (at
your option) any later version.

This library is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this library; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

.. _Total Phase: http://www.totalphase.com
.. _ipmitool: http://sourceforge.net/projects/ipmitool/
.. |BuildStatus| image:: https://github.com/kontron/python-ipmi/actions/workflows/test.yml/badge.svg
                 :target: https://github.com/kontron/python-ipmi/actions/workflows/test.yml
.. |PyPiVersion| image:: https://badge.fury.io/py/python-ipmi.svg
                 :target: http://badge.fury.io/py/python-ipmi
.. |Documentation| image:: https://readthedocs.org/projects/python-ipmi/badge/?version=latest
                   :target: https://python-ipmi.readthedocs.io/en/latest/?badge=latest
                   :alt: Documentation Status
.. |PyPiPythonVersions| image:: https://img.shields.io/pypi/pyversions/python-ipmi.svg
                        :alt: Python versions
                        :target: http://badge.fury.io/py/python-ipmi
.. |CodeClimate| image:: https://codeclimate.com/github/kontron/python-ipmi/badges/gpa.svg
                 :target: http://codeclimate.com/github/kontron/python-ipmi
.. |Coveralls|   image:: https://coveralls.io/repos/github/kontron/python-ipmi/badge.svg?branch=master
                 :target: https://coveralls.io/github/kontron/python-ipmi?branch=master
.. |Codacy|      image:: https://app.codacy.com/project/badge/Grade/068eca4b1e784425aa46ae0b06aeaf37
                 :alt: Codacy Badge
                 :target: https://www.codacy.com/gh/kontron/python-ipmi/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=kontron/python-ipmi&amp;utm_campaign=Badge_Grade
