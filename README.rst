Pure Python IPMI Library
========================

|BuildStatus| |PyPiVersion| |Coveralls| |CodeClimate|

Features
--------
* RMCP interface (using ipmitool)
* IPMB interface (The `Total Phase`_ Aardvark)

Requirements
------------

You need an either the `ipmitool`_ for accessing RCMP interface or a
`Total Phase`_ Aardvark for communication over the IPMB interface.

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

    connection.target = pyipmi.Target(0xb2)
    connection.target.set_routing_information([(0x20,0)])

    connection.session.set_session_type_rmcp('10.0.0.1', port=623)
    connection.session.set_auth_type_user('admin', 'admin')
    connection.session.establish()

    connection.get_device_id()

ipmitool command:

.. code:: shell

    ipmitool -I lan -H 10.0.0.1 -p 623 -b 0 -t 0xb2 -U "admin" -P "admin" -l 0 raw 0x06 0x01


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

Python 2.7 is currently  supported.
Python 3.x support is in beta

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
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this library; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

.. _Total Phase: http://www.totalphase.com
.. _ipmitool: http://sourceforge.net/projects/ipmitool/
.. |BuildStatus| image:: https://travis-ci.org/kontron/python-ipmi.png?branch=master
                 :target: https://travis-ci.org/kontron/python-ipmi
.. |PyPiVersion| image:: https://badge.fury.io/py/python-ipmi.svg
                 :target: http://badge.fury.io/py/python-ipmi
.. |CodeClimate| image:: https://codeclimate.com/github/kontron/python-ipmi/badges/gpa.svg
                 :target: http://codeclimate.com/github/kontron/python-ipmi
.. |Coveralls|   image:: https://coveralls.io/repos/github/kontron/python-ipmi/badge.svg?branch=master
                 :target: https://coveralls.io/github/kontron/python-ipmi?branch=master
