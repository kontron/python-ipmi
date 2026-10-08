# Copyright (c) 2014  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

"""The interfaces over which the IPMI requests are sent.

An interface is created by :func:`create_interface` with its name and
passed to :func:`pyipmi.create_connection`. All interfaces are derived
from :class:`pyipmi.interfaces.base.Interface`. The available interfaces
are:

================  ==========================================================
Name              Class
================  ==========================================================
``rmcp``          :class:`Rmcp`, IPMI v1.5 over LAN (RMCP)
``rmcpplus``      :class:`RmcpPlus`, IPMI v2.0 over LAN (RMCP+)
``ipmitool``      :class:`Ipmitool`, the ``raw`` command of ipmitool
``ipmidev``       :class:`IpmiDev`, the Linux IPMI driver (``/dev/ipmi0``)
``ipmbdev``       :class:`IpmbDev`, the Linux IPMB device driver
``aardvark``      :class:`Aardvark`, the Total Phase Aardvark I2C adapter
``openipmblink``  :class:`OpenIpmbLink`, the openipmblink IPMB bridge
``mock``          :class:`Mock`, a dummy interface for tests
================  ==========================================================

Example:
    Create an RMCP+ interface::

        interface = pyipmi.interfaces.create_interface('rmcpplus')
        ipmi = pyipmi.create_connection(interface)
"""

from __future__ import annotations

from typing import Any

from .ipmitool import Ipmitool
from .aardvark import Aardvark
from .base import Interface
from .ipmbdev import IpmbDev
from .ipmidev import IpmiDev
from .mock import Mock
from .openipmblink import OpenIpmbLink
from .rmcp import Rmcp
from .rmcpplus import RmcpPlus

INTERFACES: list[type[Interface]] = [
    Ipmitool,
    Aardvark,
    IpmbDev,
    IpmiDev,
    Mock,
    Rmcp,
    RmcpPlus,
    OpenIpmbLink,
]


def create_interface(interface: str, *args: Any, **kwargs: Any) -> Any:
    """Create an interface by its name.

    The supported names are:

    * ``'rmcp'`` (:class:`Rmcp`): IPMI v1.5 over LAN (RMCP)
    * ``'rmcpplus'`` (:class:`RmcpPlus`): IPMI v2.0 over LAN (RMCP+)
    * ``'ipmitool'`` (:class:`Ipmitool`): the ``raw`` command of ipmitool
    * ``'ipmidev'`` (:class:`IpmiDev`): the Linux IPMI driver
      (``/dev/ipmi0``)
    * ``'ipmbdev'`` (:class:`IpmbDev`): the Linux IPMB device driver
    * ``'aardvark'`` (:class:`Aardvark`): the Total Phase Aardvark I2C
      adapter
    * ``'openipmblink'`` (:class:`OpenIpmbLink`): the openipmblink IPMB
      bridge
    * ``'mock'`` (:class:`Mock`): a dummy interface for tests

    The arguments are described at the interface classes.

    Example:
        Create an interface using ipmitool with ``-I lanplus``::

            interface = create_interface('ipmitool',
                                         interface_type='lanplus')

    Args:
        interface: The name of the interface, the ``NAME`` of its class,
            e.g. ``'rmcpplus'``.
        *args: Passed to the constructor of the interface class.
        **kwargs: Passed to the constructor of the interface class.

    Returns:
        The interface.

    Raises:
        RuntimeError: There is no interface with this name.
    """
    for intf in INTERFACES:
        if intf.NAME == interface:
            return intf(*args, **kwargs)

    raise RuntimeError(f'unknown interface with name {interface}')
