# Copyright (c) 2026  Kontron Europe GmbH
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

"""Interface for the Linux IPMI driver.

:class:`IpmiDev` sends the requests through the character device of the
ipmi_devintf driver, e.g. ``/dev/ipmi0``, with the ioctls of
``include/uapi/linux/ipmi.h``. The ctypes structures of this module are
the structures of that header.

Example:
    Get the device ID of the local BMC::

        interface = pyipmi.interfaces.create_interface('ipmidev')
        ipmi = pyipmi.create_connection(interface)
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import select
import threading
import time

from .. import Target
from ..errors import IpmiTimeoutError
from ..msgs import constants
from .base import Interface

logger = logging.getLogger(__name__)

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]


# definitions of include/uapi/linux/ipmi.h

IPMI_MAX_MSG_LENGTH = 272

IPMI_SYSTEM_INTERFACE_ADDR_TYPE = 0x0c
IPMI_IPMB_ADDR_TYPE = 0x01
IPMI_BMC_CHANNEL = 0xf

IPMI_RESPONSE_RECV_TYPE = 1


class IpmiMsg(ctypes.Structure):
    """The message of a request or response, ``struct ipmi_msg``."""

    _fields_ = [
        ('netfn', ctypes.c_ubyte),
        ('cmd', ctypes.c_ubyte),
        ('data_len', ctypes.c_ushort),
        ('data', ctypes.c_void_p),
    ]


class IpmiReq(ctypes.Structure):
    """A request to send, ``struct ipmi_req``."""

    _fields_ = [
        ('addr', ctypes.c_void_p),
        ('addr_len', ctypes.c_uint),
        ('msgid', ctypes.c_long),
        ('msg', IpmiMsg),
    ]


class IpmiRecv(ctypes.Structure):
    """A received message, ``struct ipmi_recv``."""

    _fields_ = [
        ('recv_type', ctypes.c_int),
        ('addr', ctypes.c_void_p),
        ('addr_len', ctypes.c_uint),
        ('msgid', ctypes.c_long),
        ('msg', IpmiMsg),
    ]


class IpmiSystemInterfaceAddr(ctypes.Structure):
    """The address of the BMC, ``struct ipmi_system_interface_addr``."""

    _fields_ = [
        ('addr_type', ctypes.c_int),
        ('channel', ctypes.c_short),
        ('lun', ctypes.c_ubyte),
    ]


class IpmiIpmbAddr(ctypes.Structure):
    """The address of an IPMB target, ``struct ipmi_ipmb_addr``."""

    _fields_ = [
        ('addr_type', ctypes.c_int),
        ('channel', ctypes.c_short),
        ('slave_addr', ctypes.c_ubyte),
        ('lun', ctypes.c_ubyte),
    ]


def _ioc(direction: str, nr: int, size: int) -> int:
    """Return the ioctl request number like the _IOC() macro of Linux."""
    if platform.machine().startswith(('ppc', 'powerpc', 'mips', 'sparc')):
        dirs, dir_shift = {'r': 2, 'w': 4, 'rw': 6}, 29
    else:
        dirs, dir_shift = {'r': 2, 'w': 1, 'rw': 3}, 30
    return (dirs[direction] << dir_shift) | (size << 16) | (ord('i') << 8) | nr


IPMICTL_RECEIVE_MSG_TRUNC = _ioc('rw', 11, ctypes.sizeof(IpmiRecv))
# the kernel defines the send command with _IOR
IPMICTL_SEND_COMMAND = _ioc('r', 13, ctypes.sizeof(IpmiReq))


class IpmiDev(Interface):
    """This interface uses the Linux IPMI driver (ipmi_devintf).

    The driver provides access to the system interface (e.g. KCS, SMIC, BT
    or SSIF) of the BMC via /dev/ipmi0. Requests to the BMC are sent to the
    system interface, requests to other IPMB targets are bridged by the BMC.
    The driver bridges one hop; the target is addressed either by its IPMB
    address (on channel 0) or by a routing with one bridge, e.g.
    [(0x20, 0x20, 7), (0x20, 0x72, None)].
    """

    NAME = 'ipmidev'
    BMC_ADDRESS = 0x20

    def __init__(self, port: str = '/dev/ipmi0', timeout: float = 10.0) -> None:
        """Create the interface.

        Args:
            port: The character device of the driver.
            timeout: The time to wait for a response in seconds.

        Raises:
            RuntimeError: The fcntl module is not available, e.g. on
                Windows.
        """
        if fcntl is None:
            raise RuntimeError('No fcntl module found. You can not '
                               'use this interface.')
        self.port = port
        self.timeout = timeout
        self._dev: int | None = None
        self._msgid = 0
        self._lock = threading.Lock()

    def open(self) -> None:
        """Open the character device."""
        self._dev = os.open(self.port, os.O_RDWR)

    def close(self) -> None:
        """Close the character device, if it is open."""
        if self._dev is not None:
            os.close(self._dev)
            self._dev = None

    def _get_dev(self) -> int:
        if self._dev is None:
            raise RuntimeError(f'Device {self.port} is not open')
        return self._dev

    def is_target_accessible(self, target: Target) -> bool:
        """Check if the target answers a Get Device ID request.

        Args:
            target: The target.

        Returns:
            True if the target answers, False on a timeout.
        """
        try:
            self.send_and_receive_raw(target, 0, constants.NETFN_APP,
                                      bytes((constants.CMDID_GET_DEVICE_ID,)))
        except IpmiTimeoutError:
            return False
        return True

    def is_system_interface(self, target: Target) -> bool:
        """Check if requests to the target are sent to the system interface.

        Args:
            target: The target.

        Returns:
            True for the BMC itself, False for a target the BMC bridges the
            requests to.
        """
        return isinstance(self._encode_address(target, 0),
                          IpmiSystemInterfaceAddr)

    def _encode_address(self, target: Target, lun: int) -> ctypes.Structure:
        routing = target.routing or []
        if len(routing) > 2:
            raise RuntimeError("ipmidev supports only one bridge, routing: "
                               f"{', '.join(str(r) for r in routing)}")

        address: int | None
        if len(routing) == 2:
            channel = routing[0].channel
            address = routing[1].rs_sa
        else:
            channel = 0
            address = target.ipmb_address

        if address is None or (address == self.BMC_ADDRESS
                               and len(routing) < 2):
            return IpmiSystemInterfaceAddr(
                addr_type=IPMI_SYSTEM_INTERFACE_ADDR_TYPE,
                channel=IPMI_BMC_CHANNEL, lun=lun)

        return IpmiIpmbAddr(addr_type=IPMI_IPMB_ADDR_TYPE, channel=channel,
                            slave_addr=address, lun=lun)

    def _send(self, addr: ctypes.Structure, netfn: int, cmdid: int,
              data: bytes, msgid: int) -> None:
        data_buf = ctypes.create_string_buffer(data, len(data) or 1)
        req = IpmiReq()
        req.addr = ctypes.addressof(addr)
        req.addr_len = ctypes.sizeof(addr)
        req.msgid = msgid
        req.msg.netfn = netfn
        req.msg.cmd = cmdid
        req.msg.data_len = len(data)
        req.msg.data = ctypes.addressof(data_buf)
        fcntl.ioctl(self._get_dev(), IPMICTL_SEND_COMMAND, req)

    def _receive(self, msgid: int, netfn: int, cmdid: int) -> bytes:
        dev = self._get_dev()
        deadline = time.monotonic() + self.timeout
        while True:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise IpmiTimeoutError()
            r, _, _ = select.select([dev], [], [], timeout)
            if dev not in r:
                raise IpmiTimeoutError()

            addr_buf = ctypes.create_string_buffer(
                ctypes.sizeof(IpmiIpmbAddr) + 16)
            data_buf = ctypes.create_string_buffer(IPMI_MAX_MSG_LENGTH)
            recv = IpmiRecv()
            recv.addr = ctypes.addressof(addr_buf)
            recv.addr_len = ctypes.sizeof(addr_buf)
            recv.msg.data = ctypes.addressof(data_buf)
            recv.msg.data_len = IPMI_MAX_MSG_LENGTH
            fcntl.ioctl(dev, IPMICTL_RECEIVE_MSG_TRUNC, recv)

            rx_data = data_buf.raw[:recv.msg.data_len]
            if (recv.recv_type == IPMI_RESPONSE_RECV_TYPE
                    and recv.msgid == msgid
                    and recv.msg.netfn == netfn + 1
                    and recv.msg.cmd == cmdid):
                return rx_data

            logger.debug('ipmidev RX dropped type %d msgid %d netfn %02Xh '
                         'cmd %02Xh [%s]', recv.recv_type, recv.msgid,
                         recv.msg.netfn, recv.msg.cmd, rx_data.hex(' '))

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Send a raw request to the target and return the raw response.

        The request is sent to the BMC, or bridged by the BMC to the
        target, see :class:`IpmiDev`. Messages received from the driver
        which are not the response to the request are dropped.

        Args:
            target: The target of the request.
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code.

        Raises:
            RuntimeError: The interface is not open, or the routing of
                the target has more than one bridge.
            IpmiTimeoutError: No response within the timeout.
        """
        if self._dev is None:
            raise RuntimeError('interface is not open')

        addr = self._encode_address(target, lun)
        cmdid = raw_bytes[0]
        data = bytes(raw_bytes[1:])

        with self._lock:
            self._msgid = (self._msgid + 1) & 0x7fffffff
            msgid = self._msgid

            logger.debug('ipmidev TX netfn %02Xh cmd %02Xh [%s]', netfn, cmdid,
                         data.hex(' '))
            self._send(addr, netfn, cmdid, data, msgid)
            rx_data = self._receive(msgid, netfn, cmdid)
            logger.debug('ipmidev RX [%s]', rx_data.hex(' '))

        if not rx_data:
            raise IpmiTimeoutError()
        return rx_data
