# Pure Python IPMI Library

[![Build Status](https://github.com/kontron/python-ipmi/actions/workflows/test.yml/badge.svg)](https://github.com/kontron/python-ipmi/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/python-ipmi.svg)](http://badge.fury.io/py/python-ipmi)
[![Documentation Status](https://readthedocs.org/projects/python-ipmi/badge/?version=latest)](https://python-ipmi.readthedocs.io/en/latest/?badge=latest)
[![Python versions](https://img.shields.io/pypi/pyversions/python-ipmi.svg)](http://badge.fury.io/py/python-ipmi)
[![Coverage Status](https://coveralls.io/repos/github/kontron/python-ipmi/badge.svg?branch=master)](https://coveralls.io/github/kontron/python-ipmi?branch=master)
[![Code Climate](https://codeclimate.com/github/kontron/python-ipmi/badges/gpa.svg)](http://codeclimate.com/github/kontron/python-ipmi)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/068eca4b1e784425aa46ae0b06aeaf37)](https://www.codacy.com/gh/kontron/python-ipmi/dashboard?utm_source=github.com&utm_medium=referral&utm_content=kontron/python-ipmi&utm_campaign=Badge_Grade)

## Features

* RMCP interface
  * native
  * legacy using [ipmitool] as backend
* RMCP+ interface
  * native
  * legacy using [ipmitool] as backend
* system interface (using ipmitool as backend)
  * native (KCS, SMIC, BT, SSIF) using the IPMI driver on Linux
  * legacy using [ipmitool] as backend
* IPMB interface
  * using the [Total Phase] Aardvark
  * using ipmb-dev driver on Linux

## Tested Devices

* Kontron
  * mTCA Carrier Manager
  * CompactPCI boards
  * VPX boards
* Pigeon Point Shelf Manager
* HPE iLO3/iLO4
* N.A.T. NAT-MCH
* DESY MMC STAMP & related AMCs (DAMC-FMC2ZUP, DAMC-FMC1Z7IO)
* Supermicro

## Requirements

For IPMB interface a [Total Phase] Aardvark is needed.
Another option is to use ipmb-dev driver on Linux with an I2C bus, driver of which supports slave mode:
https://www.kernel.org/doc/html/latest/driver-api/ipmb.html

For the native system interface the Linux IPMI driver is needed
(`ipmi_devintf` and e.g. `ipmi_si` or `ipmi_ssif`), which provides
`/dev/ipmi0`:
https://www.kernel.org/doc/html/latest/driver-api/ipmi.html

For legacy RMCP, RMCP+ and system interface (KCS) using ipmitool as backend
the installation of ipmitool is required.

The native RMCP+ interface needs the [cryptography] package for
encrypted sessions (AES-CBC-128, cipher suites 3 and 17):

```shell
pip install python-ipmi[rmcpplus]
```

## Installation

### Using `pip`

The recommended installation method is using [pip](https://pip.pypa.io):

```shell
pip install python-ipmi
```

### Manual installation

Download the source distribution package for the library. Extract the package to
a temporary location and install:

```shell
python setup.py install
```

## Documentation

You can find the most up to date documentation at:
http://python-ipmi.rtfd.org

## Example

Below is an example that shows how to setup the interface and the connection
using the [ipmitool] as backend with both network and serial interfaces.

Example with lan interface:

```python
import pyipmi
import pyipmi.interfaces

# Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='lan')

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x82)
connection.target.set_routing([(0x81,0x20,0),(0x20,0x82,7)])

connection.session.set_session_type_rmcp('10.0.0.1', port=623)
connection.session.set_auth_type_user('admin', 'admin')
connection.session.set_priv_level("ADMINISTRATOR")
connection.session.establish()

connection.get_device_id()
```

ipmitool command:

```shell
ipmitool -I lan -H 10.0.0.1 -p 623 -L "ADMINISTRATOR" -U "admin" -P "admin" -t 0x82 -b 0 -l 0 raw 0x06 0x01
```

Example with serial interface:

```python
import pyipmi
import pyipmi.interfaces

interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='serial-terminal')

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0xb2)

# set_session_type_serial(port, baudrate)
connection.session.set_session_type_serial('/dev/tty2', 115200)
connection.session.establish()

connection.get_device_id()
```

ipmitool command:

```shell
ipmitool -I serial-terminal -D /dev/tty2:115200 -t 0xb2 -l 0 raw 0x06 0x01
```

Example with the system interface using the Linux IPMI driver:

```python
import pyipmi
import pyipmi.interfaces

interface = pyipmi.interfaces.create_interface('ipmidev', port='/dev/ipmi0')

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x20)

connection.open()
connection.get_device_id()
connection.close()
```

ipmitool command:

```shell
ipmitool -I open -t 0x20 raw 0x06 0x01
```

Example with the native RMCP+ interface:

```python
import pyipmi
import pyipmi.interfaces

# without cipher_suite the cipher suites 17 and 3 are tried
interface = pyipmi.interfaces.create_interface('rmcpplus', cipher_suite=3)

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x20)
connection.session.set_session_type_rmcp('10.0.0.1', port=623)
connection.session.set_auth_type_user('admin', 'admin')
connection.session.set_priv_level('ADMINISTRATOR')

connection.open()
connection.get_device_id()
connection.close()
```

ipmitool command:

```shell
ipmitool -I lanplus -C 3 -H 10.0.0.1 -p 623 -U admin -P admin -L ADMINISTRATOR -t 0x20 raw 0x06 0x01
```

## Compatibility

Python >= 3.10 is currently supported. Python 2.x is deprecated.

## Contributing

Contributions are always welcome. You may send patches directly (eg. `git
send-email`), do a github pull request or just file an issue.

* respect the coding style (eg. PEP8),
* provide well-formed commit message (see [this blog post](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)),
* add a Signed-off-by line (eg. `git commit -s`)

## License

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

[Total Phase]: http://www.totalphase.com
[ipmitool]: https://codeberg.org/IPMITool/ipmitool
[cryptography]: https://pypi.org/project/cryptography/
