Introduction
============

The :abbr:`IPMI (Intelligent Platform Management Interface)` is a set of computer interface specifications for an autonomous computer subsystem that provides management and monitoring capabilities independently of the host system's :abbr:`CPU (Central Processor Unit)`, firmware (:abbr:`BIOS (Basic Input/Output System)` or :abbr:`UEFI (Unified Extensible Firmware Interface)`) and operating system. The python-ipmi library provides :abbr:`API (Application Programming Interface)` for using IPMI protocol within the python environment. This library supports :abbr:`IPMI (Intelligent Platform Management Interface)` version 2.0 as described in the `IPMI standard`_.

There are two ways to communicate with a server using :abbr:`IPMI (Intelligent Platform Management Interface)` interface:

1. :abbr:`IPMI (Intelligent Platform Management Interface)` over :abbr:`LAN (Local Area Network)` using :abbr:`RMCP (Remote Management Control Protocol)` packet datagrams
2. :abbr:`IPMB (Intelligent Platform Management Bus)` is an |I2C| -based bus

Features
--------
* native :abbr:`RMCP (Remote Management Control Protocol)` interface (using python libraries only)
* legacy :abbr:`RMCP (Remote Management Control Protocol)` interface (requires `ipmitool`_ to be installed)
* :abbr:`IPMB (Intelligent Platform Management Bus)` interface (using the `Total Phase`_ Aardvark)

Tested Devices
--------------
* Kontron mTCA Carrier Manager
* Kontron CompactPCI boards
* Pigeon Point Shelf Manager
* HPE iLO3/iLO4 and T5224DN 2U24

Requirements
------------

For :abbr:`IPMB (Intelligent Platform Management Bus)` interface a `Total Phase`_ Aardvark is needed.

Installation
------------

Using ``pip``
'''''''''''''

The recommended installation method is using
`pip <http://pip-installer.org>`__::

    pip install python-ipmi

.. warning::

  If you are using Anaconda, still the above installation procedure shall be used as **conda install python-ipmi** will not find the installation package.

Manual installation
'''''''''''''''''''

Download the source distribution package for the library. Extract the package to
a temporary location and install::

    python setup.py install


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
.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
.. |I2C| replace:: I\ :sup:`2`\ C