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
from array import array
from typing import Any

from .. import Target
from ..msgs import create_message, encode_message, decode_message, Message
from ..errors import IpmiTimeoutError
from ..logger import log
from ..interfaces.ipmb import IpmbHeaderReq, rx_filter, encode_ipmb_msg
from ..session import Session

try:
    import serial
except ImportError:
    serial = None


class OpenIpmbLinkError(IOError):
    pass


class OpenIpmbLink(object):
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

        self.slave_address = slave_address
        self.port = port
        self.bus = bus
        self.timeout = 0.25
        self.cmd_timeout = 1.0
        self.max_retries = 3
        self.next_sequence_number = 0
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

    def establish_session(self, session: Session) -> None:
        pass

    def close_session(self) -> None:
        pass

    def is_ipmc_accessible(self, target: Target) -> bool:
        header = IpmbHeaderReq()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = 1
        self._send_raw(header, None)
        self._receive_raw(header)
        return True

    def _inc_sequence_number(self) -> None:
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

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

    def _send_and_receive(self, target: Target, lun: int, netfn: int,
                          cmdid: int, payload: bytes) -> bytes:
        """Send and receive data using the openipmblink interface.

        target:
        lun:
        netfn:
        cmdid:
        payload: IPMI message payload as bytestring

        Returns the received data as bytestring
        """
        self._inc_sequence_number()

        # assemble IPMB header
        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = cmdid

        retries = 0
        while retries < self.max_retries:
            try:
                self._send_raw(header, payload)
                rx_data = self._receive_raw(header)
                break
            except IpmiTimeoutError:
                pass
            except IOError:
                pass

            retries += 1
            time.sleep(retries * 0.2)

        else:
            raise IpmiTimeoutError()

        return rx_data[6:-1]

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Interface function to send and receive raw message.

        target: IPMI target
        lun: logical unit number
        netfn: network function
        raw_bytes: RAW bytes as bytestring

        Returns the IPMI message response bytestring.
        """
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])

    def send_and_receive(self, req: Message) -> Message:
        """Interface function to send and receive an IPMI message.

        target: IPMI target
        req: IPMI message request

        Returns the IPMI message response.
        """
        log().debug('IPMI Request [%s]', req)

        rx_data = self._send_and_receive(target=req.target,
                                         lun=req.lun,
                                         netfn=req.netfn,
                                         cmdid=req.cmdid,
                                         payload=encode_message(req))
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)

        log().debug('IPMI Response [%s])', rsp)

        return rsp
