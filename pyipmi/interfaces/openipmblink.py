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
import time
from typing import Any

from ..errors import IpmiTimeoutError
from ..logger import log
from .ipmb import IpmbInterface, IpmbHeaderReq, rx_filter, encode_ipmb_msg

try:
    import serial
except ImportError:
    serial = None


class OpenIpmbLinkError(IOError):
    pass


class OpenIpmbLink(IpmbInterface):
    """This interface uses the openipmblink USB to IPMB bridge.

    The bridge is connected via its data USB serial port. The host protocol
    (version 3) uses one JSON object per line, IPMB messages are transferred
    as hex strings including both checksums.
    """

    NAME = 'openipmblink'
    PROTOCOL_VERSION = 3

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ttyACM1', bus: int = 0) -> None:
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        super().__init__(slave_address)
        self.port = port
        self.bus = bus
        self.cmd_timeout = 1.0
        self._ser = None
        self._rx_buf = bytearray()
        self._pending_rx = []

    def open(self) -> None:
        self._ser = serial.Serial(self.port, timeout=0.05)
        self._rx_buf = bytearray()
        self._pending_rx = []
        # terminate a partial line left over from an earlier session
        self._ser.write(b'\n')

        info = self._command('ping')
        if info.get('version') != self.PROTOCOL_VERSION:
            raise OpenIpmbLinkError(
                'bridge protocol version %s, interface needs %d'
                % (info.get('version'), self.PROTOCOL_VERSION))
        log().debug('openipmblink v%s on %s', info.get('version'),
                    info.get('board'))

        self._check_status(self._command('set_addr', bus=self.bus,
                                         addr=self.slave_address))

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def _write_packet(self, packet: dict) -> None:
        line = json.dumps(packet, separators=(',', ':')).encode()
        log().debug('openipmblink TX %s', line)
        self._ser.write(line + b'\n')

    def _read_packet(self, timeout: float) -> dict | None:
        """Return the next JSON packet or None on timeout."""
        deadline = time.monotonic() + timeout
        while True:
            pos = self._rx_buf.find(b'\n')
            if pos >= 0:
                line = bytes(self._rx_buf[:pos]).rstrip(b'\r')
                del self._rx_buf[:pos + 1]
                log().debug('openipmblink RX %s', line)
                try:
                    packet = json.loads(line)
                except ValueError:
                    continue  # e.g. partial line after opening the port
                if isinstance(packet, dict):
                    return packet
                continue
            if time.monotonic() >= deadline:
                return None
            self._rx_buf += self._ser.read(self._ser.in_waiting or 1)

    def _command(self, cmd: str, **params: Any) -> dict:
        """Send a command to the bridge and return its reply."""
        self._write_packet(dict(cmd=cmd, **params))
        deadline = time.monotonic() + self.cmd_timeout
        while True:
            packet = self._read_packet(max(0.0, deadline - time.monotonic()))
            if packet is None:
                raise OpenIpmbLinkError('no reply from bridge')
            if packet.get('rsp') == cmd:
                return packet
            if packet.get('evt') == 'error':
                raise OpenIpmbLinkError('bridge reported error: %s'
                                        % packet.get('status'))
            if packet.get('evt') == 'rx':
                self._pending_rx.append(packet)

    @staticmethod
    def _check_status(reply: dict) -> None:
        status = reply.get('status')
        if status != 'ok':
            raise OpenIpmbLinkError('bridge status: %s' % status)

    def _receive_frame(self, timeout: float) -> bytes | None:
        """Return the next IPMB message received on our bus."""
        deadline = time.monotonic() + timeout
        while True:
            while self._pending_rx:
                packet = self._pending_rx.pop(0)
                if packet.get('bus') == self.bus:
                    return bytes.fromhex(packet['msg'])
            packet = self._read_packet(max(0.0, deadline - time.monotonic()))
            if packet is None:
                return None
            if packet.get('evt') == 'rx':
                self._pending_rx.append(packet)

    def _send_raw(self, header: IpmbHeaderReq,
                  raw_bytes: bytes | None) -> None:
        raw_bytes = encode_ipmb_msg(header, raw_bytes)

        log().debug('IPMB TX to %02Xh [%s]', header.rs_sa,
                    ' '.join(['%02x' % b for b in raw_bytes]))
        self._check_status(self._command('send', bus=self.bus,
                                         msg=raw_bytes.hex()))

    def _receive_raw(self, header: IpmbHeaderReq) -> bytes:
        start_time = time.monotonic()
        while True:
            timeout = self.timeout - (time.monotonic() - start_time)
            if timeout <= 0:
                raise IpmiTimeoutError()

            rx_data = self._receive_frame(timeout)
            if rx_data is None:
                raise IpmiTimeoutError()

            log().debug('IPMB RX [%s]',
                        ' '.join(['%02x' % c for c in rx_data]))

            if len(rx_data) < 7:
                log().debug('IPMB RX message too short')
                continue

            if rx_filter(header, rx_data):
                return rx_data
