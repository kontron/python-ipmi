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

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any
from collections.abc import Callable

from ..logger import log
from .ipmb import IpmbInterface
from .router import MessageRouter

try:
    import serial
except ImportError:
    serial = None


class OpenIpmbLinkError(IOError):
    pass


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
        self.port = port
        self.cmd_timeout = cmd_timeout
        self.info: dict | None = None
        self._ser = None
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
        """Return the open device of the port, open it on first use."""
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
        log().debug('openipmblink v%s on %s', info.get('version'),
                    info.get('board'))

    def close(self) -> None:
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
        """
        with self._listeners_lock:
            if bus in self._listeners:
                raise OpenIpmbLinkError('bus %d is already in use' % bus)
            self._listeners[bus] = listener

    def remove_listener(self, bus: int) -> None:
        with self._listeners_lock:
            self._listeners.pop(bus, None)

    def has_listener(self, bus: int) -> bool:
        return bus in self._listeners

    def command(self, cmd: str, **params: Any) -> dict:
        """Send a command to the bridge and return its reply."""
        with self._command_lock:
            # drop late replies of commands that timed out
            while not self._replies.empty():
                self._replies.get_nowait()

            line = json.dumps(dict(cmd=cmd, **params),
                              separators=(',', ':')).encode()
            log().debug('openipmblink TX %s', line)
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
            log().debug('openipmblink RX %s', line)
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
                    log().error('openipmblink receive failed: %s', e)
                return

            if packet is None:
                continue
            if 'rsp' in packet or packet.get('evt') == 'error':
                self._replies.put(packet)
            elif packet.get('evt') == 'rx':
                self._dispatch(packet)

    def _dispatch(self, packet: dict) -> None:
        listener = self._listeners.get(packet.get('bus'))
        if listener is None:
            return
        try:
            frame = bytes.fromhex(packet['msg'])
        except (KeyError, TypeError, ValueError):
            log().debug('openipmblink bad rx event %s', packet)
            return
        try:
            listener(frame, packet.get('ts'))
        except Exception:
            log().exception('openipmblink rx listener failed')


class OpenIpmbLink(IpmbInterface):
    """This interface uses one IPMB bus of the openipmblink bridge.

    The bridge is connected via its data USB serial port. Interfaces for the
    other bus of the same bridge can be opened at the same time; they share
    the serial port.

    Incoming requests are ignored by default. To answer them, set a
    `MessageRouter` with registered handlers, e.g.:

        router = MessageRouter()
        router.register_handler(NETFN_APP, CMDID_GET_DEVICE_ID, handler)
        intf = OpenIpmbLink(port='/dev/ttyACM1', bus=0, router=router)
    """

    NAME = 'openipmblink'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ttyACM1', bus: int = 0,
                 router: MessageRouter | None = None) -> None:
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        super().__init__(slave_address, router)
        self.port = port
        self.bus = bus
        self._device: OpenIpmbLinkDevice | None = None

    def open(self) -> None:
        device = OpenIpmbLinkDevice.acquire(self.port)
        try:
            self._check_status(device.command('set_addr', bus=self.bus,
                                              addr=self.slave_address))
            device.add_listener(self.bus, self._on_rx)
        except Exception:
            device.release()
            raise
        self._device = device

    def close(self) -> None:
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
        if self._device is None:
            raise OpenIpmbLinkError('interface is not open')

        log().debug('IPMB TX bus %d [%s]', self.bus, bytes(frame).hex(' '))
        self._check_status(self._device.command('send', bus=self.bus,
                                                msg=bytes(frame).hex()))

    def _on_rx(self, frame: bytes, ts: int | None) -> None:
        self._receive_frame(frame)
