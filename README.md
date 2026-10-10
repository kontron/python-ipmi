# Pure Python IPMI Library

[![Build Status](https://github.com/kontron/python-ipmi/actions/workflows/test.yml/badge.svg)](https://github.com/kontron/python-ipmi/actions/workflows/test.yml)
[![Lint](https://github.com/kontron/python-ipmi/actions/workflows/lint.yml/badge.svg)](https://github.com/kontron/python-ipmi/actions/workflows/lint.yml)
[![PyPI version](https://img.shields.io/pypi/v/python-ipmi.svg)](https://pypi.org/project/python-ipmi/)
[![Documentation Status](https://readthedocs.org/projects/python-ipmi/badge/?version=latest)](https://python-ipmi.readthedocs.io/en/latest/?badge=latest)
[![Python versions](https://img.shields.io/pypi/pyversions/python-ipmi.svg)](https://pypi.org/project/python-ipmi/)
[![License](https://img.shields.io/pypi/l/python-ipmi.svg)](https://github.com/kontron/python-ipmi/blob/master/COPYING)
[![Downloads](https://img.shields.io/pypi/dm/python-ipmi.svg)](https://pypistats.org/packages/python-ipmi)
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
* system interface
  * native (KCS, SMIC, BT, SSIF) using the IPMI driver on Linux
  * legacy using [ipmitool] as backend
* IPMB interface
  * using the [Total Phase] Aardvark
  * using ipmb-dev driver on Linux
  * using the openipmblink USB bridge
  * answering incoming requests, e.g. to act as a BMC or MMC
    ([IPMB message routing][doc-routing])
* bridged requests to controllers behind the BMC
* decoding of FRU data, SDRs and SEL entries, HPM.1 firmware upgrades
* the command line tool `pyipmi` (formerly `ipmitool.py`)

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

Python 3.10 or newer is required, PyPy is supported as well. The library
itself has no dependencies; some interfaces need additional packages,
drivers or programs, as described below.

For the IPMB interface one of these is needed:

* a [Total Phase] Aardvark adapter and the `pyaardvark` package
* the ipmb-dev driver on Linux with an I2C bus whose driver supports slave
  mode: https://www.kernel.org/doc/html/latest/driver-api/ipmb.html
* an openipmblink bridge and the `pyserial` package

For the native system interface the Linux IPMI driver is needed
(`ipmi_devintf` and e.g. `ipmi_si` or `ipmi_ssif`), which provides
`/dev/ipmi0`:
https://www.kernel.org/doc/html/latest/driver-api/ipmi.html

For legacy RMCP, RMCP+ and system interface (KCS) using ipmitool as backend
the installation of ipmitool is required. Any ipmitool 1.8.x works; the
serial interface (`serial-terminal`) needs at least version 1.8.13.

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

Download the source distribution package for the library or clone the git
repository, and install it from its top directory:

```shell
pip install .
```

### Running from the source tree

To work on the library or to use it directly from a git checkout, create a
virtual environment and install the checkout in editable mode. Changes to the
source are then active without reinstalling:

```shell
git clone https://github.com/kontron/python-ipmi.git
cd python-ipmi
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[rmcpplus]'
```

This also installs the `pyipmi` command line tool and generates
`pyipmi/version.py` with the version from `git describe`. Install the
optional packages for the interfaces you need: `pyserial` for the
openipmblink interface and `pyaardvark` for the Aardvark IPMB interface.

To run the tests:

```shell
pip install pytest
pytest
```

The CI also runs the linter [ruff], the type checker mypy and the spell
checker codespell. They are configured in `ruff.toml` and `setup.cfg`, so
they run without arguments. Use the versions pinned in
`.github/workflows/lint.yml` to get the same results as the CI:

```shell
pip install ruff==0.16.10 mypy==2.4.0 codespell
ruff check .
mypy
codespell
```

`ruff check --fix .` fixes many of the reported issues automatically.

Alternatively, the checkout can be used without installing by adding its top
directory to `PYTHONPATH`. Then `pyipmi` can be imported from any directory,
e.g. by your own scripts or the ones in `examples/`, and the tool is started
with `python3 -m pyipmi.cli`:

```shell
export PYTHONPATH=/path/to/python-ipmi
python3 -m pyipmi.cli -V
```

The optional packages have to be installed separately then, e.g.
`pip install cryptography` for encrypted RMCP+ sessions. The version is shown
as `dev` as long as `pyipmi/version.py` has not been generated, e.g. by
`python3 setup.py --version`.

### Package version

The version of the package is taken from, in this order:

1. `git describe --tags` in a git checkout, e.g. `0.5.8.dev77+g7c853b0`
   for the 77th commit after the tag `0.5.8`
2. `pyipmi/version.py`, which is generated by `setup.py` and is part of the
   source distribution on PyPI
3. `version_archive.txt`, which `git archive` fills in with the tag. This
   makes the tarballs of the GitHub releases build with the right version,
   e.g. for distribution packages.

If none of them is available, the version is `0+unknown`. The installed
version is available as `pyipmi.__version__` and with `pyipmi -V`.

## Documentation

You can find the most up to date documentation at:
https://python-ipmi.readthedocs.io

* [Quick start](https://python-ipmi.readthedocs.io/en/latest/quick_start.html)
* [Commands and interfaces][doc-interfaces]: how the commands reach a device
  through the interfaces, and how to implement an interface
* [IPMB message routing][doc-routing]: how to answer requests on the IPMB
* [API reference](https://python-ipmi.readthedocs.io/en/latest/api.html)

[doc-interfaces]: https://python-ipmi.readthedocs.io/en/latest/interfaces.html
[doc-routing]: https://python-ipmi.readthedocs.io/en/latest/message_routing.html

## Example

The examples below talk to the BMC of a server, which has the IPMB address
`0x20`. Set a routing only for targets behind the BMC, see
[Bridged targets](#bridged-targets).

Example with the native RMCP+ interface (IPMI v2.0, like `ipmitool -I lanplus`):

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

Example using the [ipmitool] as backend with the lan interface:

```python
import pyipmi
import pyipmi.interfaces

# Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='lan')

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x20)

connection.session.set_session_type_rmcp('10.0.0.1', port=623)
connection.session.set_auth_type_user('admin', 'admin')
connection.session.set_priv_level("ADMINISTRATOR")
connection.session.establish()

connection.get_device_id()
```

ipmitool command:

```shell
ipmitool -I lan -H 10.0.0.1 -p 623 -L "ADMINISTRATOR" -U "admin" -P "admin" raw 0x06 0x01
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

Example with the IPMB interface, using bus 0 of an openipmblink bridge with
the own IPMB address `0x24`:

```python
import pyipmi
import pyipmi.interfaces

interface = pyipmi.interfaces.create_interface('openipmblink',
                                               slave_address=0x24,
                                               port='/dev/ttyACM1', bus=0)

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x20)

connection.open()
connection.get_device_id()
connection.close()
```

`pyipmi` command:

```shell
pyipmi -I openipmblink -o port=/dev/ttyACM1,bus=0,address=0x24 -t 0x20 bmc info
```

### Bridged targets

In ATCA and MicroTCA systems the controllers of blades and AMCs are not
reachable directly but only through the shelf manager or MCH, which forwards
(bridges) the requests on IPMB. For these targets set the IPMB address of the
target and the routing to it. A routing is a list of
`(requester address, responder address, channel)` tuples, one per hop.

Example for an ATCA blade with IPMB address `0x82` behind the shelf manager:

```python
connection.target = pyipmi.Target(0x82)
connection.target.set_routing([(0x81, 0x20, 0), (0x20, 0x82, None)])
```

ipmitool command:

```shell
ipmitool -I lan -H 10.0.0.1 -p 623 -L "ADMINISTRATOR" -U "admin" -P "admin" -t 0x82 -b 0 raw 0x06 0x01
```

Do not set a routing to talk to the BMC of a server itself, the bridged
request fails then (e.g. with completion code `0x83`, NAK on write).

Some shelf managers and carrier managers do not return the sequence number
of a bridged request in their response. If requests time out although the
device answers (the debug log shows `discarding message that does not match
the request`), create the native interface with
`quirks_cfg={'rmcp_ignore_rq_seq': True}`. With the ipmitool backend the
routing needs the bridge channel of every hop except the last one.
See the [documentation](https://python-ipmi.readthedocs.io/en/latest/quick_start.html)
for more routing examples.

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
[ruff]: https://docs.astral.sh/ruff/
