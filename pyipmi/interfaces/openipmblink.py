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

"""Interface for the IPMB buses of an openipmblink bridge.

The bridge is connected over a serial port, which needs the pyserial
package. :class:`OpenIpmbLink` is the interface for one bus of the bridge,
:class:`OpenIpmbLinkDevice` the serial connection shared by the buses.

Example:
    Get the device ID of the BMC on bus 0 of the bridge::

        interface = pyipmi.interfaces.create_interface(
            'openipmblink', slave_address=0x24, port='/dev/ttyACM1', bus=0)
        ipmi = pyipmi.create_connection(interface)
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from typing import Any
from collections.abc import Callable

from .ipmb import IpmbInterface
from .router import MessageRouter

logger = logging.getLogger(__name__)

try:
    import serial
except ImportError:
    serial = None


class OpenIpmbLinkError(IOError):
    """The bridge failed or did not reply."""


class OpenIpmbLinkDevice:
    """Connection to the data serial port of an openipmblink bridge.

    All buses of a bridge share one serial port, so the interfaces of the
    buses share one device (see `acquire()`). A receive thread reads all
    packets from the bridge: replies are passed to the waiting `command()`,
    received IPMB messages to the listener of their bus.

    The host protocol (version 3) uses one JSON object per line, IPMB
    messages are transferred as hex strings including both checksums.
    """

    PROTOCOL_VERSION = 3

    _devices: dict[str, OpenIpmbLinkDevice] = {}
    _devices_lock = threading.Lock()

    def __init__(self, port: str, cmd_timeout: float = 1.0) -> None:
        """Initialize the device, it is opened by :meth:`open`.

        Args:
            port: The serial port, a device path or a pyserial URL.
            cmd_timeout: The time to wait for the reply to a command in
                seconds.
        """
        self.port = port
        self.cmd_timeout = cmd_timeout
        self.info: dict | None = None
        self._ser: Any = None
        self._rx_buf = bytearray()
        self._replies: queue.Queue = queue.Queue()
        self._command_lock = threading.Lock()
        self._listeners: dict[int, Callable[[bytes, int | None], None]] = {}
        self._listeners_lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._users = 0

    @classmethod
    def acquire(cls, port: str) -> OpenIpmbLinkDevice:
        """Return the open device of the port, open it on first use.

        Args:
            port: The serial port, a device path or a pyserial URL.

        Returns:
            The device, release it with :meth:`release`.
        """
        with cls._devices_lock:
            device = cls._devices.get(port)
            if device is None:
                device = cls(port)
                device.open()
                cls._devices[port] = device
            device._users += 1
            return device

    def release(self) -> None:
        """Release a device returned by `acquire()`, close it on last use."""
        with self._devices_lock:
            self._users -= 1
            if self._users > 0:
                return
            if self._devices.get(self.port) is self:
                del self._devices[self.port]
        self.close()

    def open(self) -> None:
        """Open the serial port and start the receive thread.

        The bridge is pinged to check the protocol version, its reply is
        stored in :attr:`info`.

        Raises:
            RuntimeError: The pyserial package is not installed.
            OpenIpmbLinkError: The bridge did not reply or has another
                protocol version.
        """
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        # the port is a device path or a pyserial URL, e.g. a bridge shared
        # over TCP: socket://localhost:5555
        self._ser = serial.serial_for_url(self.port, timeout=0.05)
        self._rx_buf = bytearray()
        self._stop.clear()
        # terminate a partial line left over from an earlier session
        self._ser.write(b'\n')
        self._reader = threading.Thread(target=self._read_loop,
                                        name='openipmblink-rx', daemon=True)
        self._reader.start()

        try:
            try:
                info = self.command('ping')
            except OpenIpmbLinkError:
                # the bridge may report the partial line as error
                info = self.command('ping')
            if info.get('version') != self.PROTOCOL_VERSION:
                raise OpenIpmbLinkError(
                    'bridge protocol version %s, interface needs %d'
                    % (info.get('version'), self.PROTOCOL_VERSION))
        except Exception:
            self.close()
            raise

        self.info = info
        logger.debug('openipmblink v%s on %s', info.get('version'),
                     info.get('board'))

    def close(self) -> None:
        """Stop the receive thread and close the serial port."""
        self._stop.set()
        if self._reader is not None:
            self._cancel_read()
            self._reader.join()
            self._reader = None
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def _cancel_read(self) -> None:
        """Interrupt the blocking read of the receive thread."""
        cancel_read = getattr(self._ser, 'cancel_read', None)
        if cancel_read is not None:
            cancel_read()  # serial port
            return
        sock = getattr(self._ser, '_socket', None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)  # socket:// URL
            except OSError:
                pass

    def add_listener(self, bus: int,
                     listener: Callable[[bytes, int | None], None]) -> None:
        """Pass IPMB messages received on the bus to the listener.

        The listener is called with the message and the receive time stamp
        of the bridge. It is called in the receive thread and must not block.

        Args:
            bus: The bus number.
            listener: The listener.

        Raises:
            OpenIpmbLinkError: The bus already has a listener.
        """
        with self._listeners_lock:
            if bus in self._listeners:
                raise OpenIpmbLinkError('bus %d is already in use' % bus)
            self._listeners[bus] = listener

    def remove_listener(self, bus: int) -> None:
        """Remove the listener of the bus, if there is one.

        Args:
            bus: The bus number.
        """
        with self._listeners_lock:
            self._listeners.pop(bus, None)

    def has_listener(self, bus: int) -> bool:
        """Check if the bus has a listener.

        Args:
            bus: The bus number.

        Returns:
            True if the bus has a listener.
        """
        return bus in self._listeners

    def command(self, cmd: str, **params: Any) -> dict:
        """Send a command to the bridge and return its reply.

        Args:
            cmd: The command.
            **params: The parameters of the command.

        Returns:
            The reply packet.

        Raises:
            OpenIpmbLinkError: No reply within the command timeout, or the
                bridge reported an error.
        """
        with self._command_lock:
            # drop late replies of commands that timed out
            while not self._replies.empty():
                self._replies.get_nowait()

            line = json.dumps(dict(cmd=cmd, **params),
                              separators=(',', ':')).encode()
            logger.debug('openipmblink TX %s', line)
            self._ser.write(line + b'\n')

            deadline = time.monotonic() + self.cmd_timeout
            while True:
                timeout = max(0.0, deadline - time.monotonic())
                try:
                    packet = self._replies.get(timeout=timeout)
                except queue.Empty:
                    raise OpenIpmbLinkError('no reply from bridge') from None
                if packet.get('evt') == 'error':
                    raise OpenIpmbLinkError('bridge reported error: %s'
                                            % packet.get('status'))
                if packet.get('rsp') == cmd:
                    return packet

    def _read_packet(self) -> dict | None:
        """Return the next JSON packet or None if no complete line is read."""
        while True:
            pos = self._rx_buf.find(b'\n')
            if pos < 0:
                data = self._ser.read(self._ser.in_waiting or 1)
                if not data:
                    return None
                self._rx_buf += data
                continue

            line = bytes(self._rx_buf[:pos]).rstrip(b'\r')
            del self._rx_buf[:pos + 1]
            logger.debug('openipmblink RX %s', line)
            try:
                packet = json.loads(line)
            except ValueError:
                continue  # e.g. partial line after opening the port
            if isinstance(packet, dict):
                return packet

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                packet = self._read_packet()
            except Exception as e:
                if not self._stop.is_set():
                    logger.error('openipmblink receive failed: %s', e)
                return

            if packet is None:
                continue
            if 'rsp' in packet or packet.get('evt') == 'error':
                self._replies.put(packet)
            elif packet.get('evt') == 'rx':
                self._dispatch(packet)

    def _dispatch(self, packet: dict) -> None:
        bus = packet.get('bus')
        listener = self._listeners.get(bus) if isinstance(bus, int) else None
        if listener is None:
            return
        try:
            frame = bytes.fromhex(packet['msg'])
        except (KeyError, TypeError, ValueError):
            logger.debug('openipmblink bad rx event %s', packet)
            return
        try:
            listener(frame, packet.get('ts'))
        except Exception:
            logger.exception('openipmblink rx listener failed')


class OpenIpmbLink(IpmbInterface):
    """This interface uses one IPMB bus of the openipmblink bridge.

    The bridge is connected via its data USB serial port. Interfaces for the
    other bus of the same bridge can be opened at the same time; they share
    the serial port.

    Incoming requests are ignored by default. To answer them, set a
    `MessageRouter` with registered handlers, e.g.::

        router = MessageRouter()
        router.register_handler(NETFN_APP, CMDID_GET_DEVICE_ID, handler)
        intf = OpenIpmbLink(port='/dev/ttyACM1', bus=0, router=router)
    """

    NAME = 'openipmblink'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ttyACM1', bus: int = 0,
                 router: MessageRouter | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The own IPMB address, set on the bus of the
                bridge when the interface is opened.
            port: The data serial port of the bridge, a device path or a
                pyserial URL, e.g. ``socket://localhost:5555``.
            bus: The bus number of the bridge.
            router: The router of the received messages, see
                :class:`~pyipmi.interfaces.ipmb.IpmbInterface`.

        Raises:
            RuntimeError: The pyserial package is not installed.
        """
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        super().__init__(slave_address, router)
        self.port = port
        self.bus = bus
        self._device: OpenIpmbLinkDevice | None = None

    def open(self) -> None:
        """Open the bridge and set the own address on the bus.

        Raises:
            OpenIpmbLinkError: The bridge failed, or the bus is already
                used by another interface.
        """
        device = OpenIpmbLinkDevice.acquire(self.port)
        # claim the bus first, so the address of a bus used by another
        # interface is not changed
        try:
            device.add_listener(self.bus, self._on_rx)
        except Exception:
            device.release()
            raise
        try:
            self._check_status(device.command('set_addr', bus=self.bus,
                                              addr=self.slave_address))
        except Exception:
            device.remove_listener(self.bus)
            device.release()
            raise
        self._device = device

    def close(self) -> None:
        """Release the bridge, it is closed if no other bus uses it."""
        if self._device is not None:
            self._device.remove_listener(self.bus)
            self._device.release()
            self._device = None
        super().close()

    @staticmethod
    def _check_status(reply: dict) -> None:
        status = reply.get('status')
        if status != 'ok':
            raise OpenIpmbLinkError('bridge status: %s' % status)

    def send_frame(self, frame: bytes) -> None:
        """Send a complete IPMB message, starting with rsSA.

        Args:
            frame: The message.

        Raises:
            OpenIpmbLinkError: The interface is not open or the bridge
                failed to send the message.
        """
        if self._device is None:
            raise OpenIpmbLinkError('interface is not open')

        logger.debug('IPMB TX bus %d [%s]', self.bus, bytes(frame).hex(' '))
        self._check_status(self._device.command('send', bus=self.bus,
                                                msg=bytes(frame).hex()))

    def _on_rx(self, frame: bytes, ts: int | None) -> None:
        self._receive_frame(frame)
