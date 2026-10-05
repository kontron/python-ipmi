# Copyright (c) 2015  Kontron Europe GmbH
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

import logging
import threading
import time
from array import array
from typing import TYPE_CHECKING
from collections.abc import Iterable

from .. import Routing, Target
from ..errors import IpmiTimeoutError
from ..msgs import (create_message, create_request_by_name,
                    encode_message, decode_message, constants)
from ..utils import check_completion_code
from ..utils import py3_array_tobytes, py3_array_frombytes
from .base import Interface

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .router import MessageRouter


def checksum(data: Iterable[int]) -> int:
    """Calculate the checksum."""
    csum = 0
    for b in data:
        csum += b
    return -csum % 256


class IpmbHeader:
    """Representation of the IPMI message header.

    Request:
    *-------*--------------*----------*-------*---------------*-------*
    | rs_sa | netfn/rs_lun | checksum | rq_sa | rq_seq/rq_lun | cmdid |
    *-------*--------------*----------*-------*---------------*-------*

    Response:
    *-------*--------------*----------*-------*---------------*-------*
    | rq_sa | netfn/rq_lun | checksum | rs_sa | rq_seq/rs_lun | cmdid |
    *-------*--------------*----------*-------*---------------*-------*
    """

    rs_sa = None
    rs_lun = None
    rq_sa = None
    rq_lun = None
    rq_seq = None
    netfn = None
    cmdid = None
    checksum = None

    def __init__(self, data: bytes | None = None) -> None:
        if data:
            self.decode(data)

    def __str__(self) -> str:
        return f'rs_sa=0x{self.rs_sa:02x}, rs_lun={self.rs_lun}, ' \
               f'rq_sa=0x{self.rq_sa:02x}, rq_lun={self.rq_lun}, ' \
               f'rq_seq={self.rq_seq}, ' \
               f'netfn=0x{self.netfn:02x}, ' \
               f'cmdid=0x{self.cmdid:02x}'


class IpmbHeaderReq(IpmbHeader):
    """Representation of the IPMI request message header."""

    def encode(self) -> bytes:
        """Encode the header."""
        data = array('B')
        data.append(self.rs_sa)
        data.append(self.netfn << 2 | self.rs_lun)
        data.append(checksum((self.rs_sa, data[1])))
        data.append(self.rq_sa)
        data.append(self.rq_seq << 2 | self.rq_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data: bytes) -> None:
        """Decode the header."""
        msg = array('B')
        py3_array_frombytes(msg, data)
        self.rs_sa = msg[0]
        self.netfn = msg[1] >> 2
        self.rs_lun = msg[1] & 3
        self.checksum = msg[2]
        self.rq_sa = msg[3]
        self.rq_seq = msg[4] >> 2
        self.rq_lun = msg[4] & 3
        self.cmdid = msg[5]


class IpmbHeaderRsp(IpmbHeader):
    """Representation of the IPMI response message header."""

    def encode(self) -> bytes:
        """Encode the header."""
        data = array('B')
        data.append(self.rq_sa)
        data.append(self.netfn << 2 | self.rq_lun)
        data.append(checksum((self.rq_sa, data[1])))
        data.append(self.rs_sa)
        data.append(self.rq_seq << 2 | self.rs_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data: bytes) -> None:
        """Decode the header."""
        data = array('B', data)
        self.rq_sa = data[0]
        self.netfn = data[1] >> 2
        self.rq_lun = data[1] & 3
        self.checksum = data[2]
        self.rs_sa = data[3]
        self.rq_seq = data[4] >> 2
        self.rs_lun = data[4] & 3
        self.cmdid = data[5]

    def from_req_header(self, req_header: IpmbHeaderReq) -> None:
        self.rs_lun = req_header.rq_lun
        self.rs_sa = req_header.rq_sa
        self.rq_seq = req_header.rq_seq
        self.rq_lun = req_header.rs_lun
        self.rq_sa = req_header.rs_sa
        self.netfn = req_header.netfn
        self.cmdid = req_header.cmdid


def encode_ipmb_msg(header: IpmbHeaderReq | IpmbHeaderRsp,
                    data: bytes | None) -> bytes:
    """Encode an IPMB message.

    header: IPMB header object
    data: IPMI message data as bytestring

    Returns the message as bytestring.
    """
    msg = array('B')
    py3_array_frombytes(msg, header.encode())
    if data is not None:
        a = array('B')
        py3_array_frombytes(a, data)
        msg.extend(a)
    msg.append(checksum(msg[3:]))
    return py3_array_tobytes(msg)


def encode_send_message(payload: bytes, rq_sa: int, rs_sa: int, channel: int,
                        seq: int, tracking: int = 1) -> bytes:
    """Encode a send message command and embed the message to be send.

    payload: the message to be send as bytestring
    rq_sa: the requester source address
    rs_sa: the responder source address
    channel: the channel
    seq: the sequence number
    tracking: tracking

    Returns an encode send message as bytestring
    """
    req = create_request_by_name('SendMessage')
    req.channel.number = channel
    req.channel.tracking = tracking
    data = encode_message(req)

    header = IpmbHeaderReq()
    header.netfn = req.__netfn__
    header.rs_lun = 0
    header.rs_sa = rs_sa
    header.rq_seq = seq
    header.rq_lun = 0
    header.rq_sa = rq_sa
    header.cmdid = req.__cmdid__

    return encode_ipmb_msg(header, data + payload)


def encode_bridged_message(routing: list[Routing], header: IpmbHeaderReq,
                           payload: bytes, seq: int) -> bytes:
    """Encode a (multi-)bridged command and embed the message to be send.

    routing:
    payload: the message to be send as bytestring
    header:
    seq: the sequence number

    Returns the encoded send message as bytestring
    """
    # change header requester addresses for bridging
    header.rq_sa = routing[-1].rq_sa
    header.rs_sa = routing[-1].rs_sa
    tx_data = encode_ipmb_msg(header, payload)

    for bridge in reversed(routing[:-1]):
        tx_data = encode_send_message(tx_data,
                                      rq_sa=bridge.rq_sa,
                                      rs_sa=bridge.rs_sa,
                                      channel=bridge.channel,
                                      seq=seq)

    return tx_data


def decode_bridged_message(rx_data: bytes) -> bytes:
    """Decode a (multi-)bridged command.

    rx_data: the received message as bytestring

    Returns the decoded message as bytestring
    """
    while array('B', rx_data)[5] == constants.CMDID_SEND_MESSAGE:
        rsp = create_message(constants.NETFN_APP + 1,
                             constants.CMDID_SEND_MESSAGE, None)
        decode_message(rsp, rx_data[6:])
        check_completion_code(rsp.completion_code)
        rx_data = rx_data[7:-1]

        if len(rx_data) < 6:
            break
    return rx_data


def rx_filter(header: IpmbHeaderReq, data: bytes | array, rq_sa: bool = False,
              rs_sa: bool = False, rq_lun: bool = False,
              rs_lun: bool = True, rq_seq: bool = True) -> bool:
    """Check if the message in rx_data matches to the information in header.

    The following checks are done:
      - Header checksum
      - Payload checksum
      - NetFn matching
      - LUN matching
      - Command Id matching

    header: the header to compare with
    data: the received message as bytestring
    """
    rsp_header = IpmbHeaderRsp(data=data)

    data = array('B', data)

    checks = [
        (checksum(data[0:3]), 0, 'Header checksum failed'),
        (checksum(data[3:]), 0, 'payload checksum failed'),
        (rsp_header.netfn, header.netfn | 1, 'NetFn mismatch'),
        (rsp_header.cmdid, header.cmdid, 'command id mismatch'),
    ]

    # optional checks
    if rq_sa:
        checks.append((rsp_header.rq_sa, header.rq_sa, 'slave address mismatch'))

    if rs_sa:
        checks.append((rsp_header.rs_sa, header.rs_sa, 'target address mismatch'))

    if rq_lun:
        checks.append((rsp_header.rq_lun, header.rq_lun, 'request LUN mismatch'))

    if rs_lun:
        checks.append((rsp_header.rs_lun, header.rs_lun, 'responder LUN mismatch'))

    if rq_seq:
        checks.append((rsp_header.rq_seq, header.rq_seq, 'sequence number mismatch'))

    match = True

    for left, right, msg in checks:
        if left != right:
            logger.debug(f'{msg:s}: {left:d} {right:d}')
            match = False

    return match


class IpmbInterface(Interface):
    """Base class of interfaces that are directly connected to an IPMB.

    The interface works as requester and responder at the same time. All
    received messages are passed to a `MessageRouter`: it matches responses
    to the pending requests and answers incoming requests with the registered
    handlers. Without a router given, incoming requests are ignored.

    A subclass implements `send_frame()` and passes each received message to
    `_receive_frame()`. Interfaces that have to poll the hardware implement
    `_read_frame()` and start the receive thread with `_start_receiver()`.
    """

    def __init__(self, slave_address: int = 0x20,
                 router: MessageRouter | None = None) -> None:
        # imported here, the router module depends on this module
        from .router import MessageRouter

        self.slave_address = slave_address
        self.timeout = 0.25
        self.max_retries = 3
        self.next_sequence_number = 0
        self._sequence_lock = threading.Lock()
        self._default_router = MessageRouter(unhandled_cc=None)
        self.router = router
        self._receiver: threading.Thread | None = None
        self._stop_receiver_event = threading.Event()

    @property
    def router(self) -> MessageRouter:
        return self._router

    @router.setter
    def router(self, router: MessageRouter | None) -> None:
        """Set the router, None sets the default router."""
        self._router = router if router is not None else self._default_router

    def send_frame(self, frame: bytes) -> None:
        """Send a complete IPMB message, starting with rsSA."""
        raise NotImplementedError()

    def _read_frame(self, timeout: float) -> bytes | None:
        """Read the next received IPMB message, starting with rqSA.

        Returns None if no message is received within the timeout.
        Only needed for interfaces that use the receive thread.
        """
        raise NotImplementedError()

    def _receive_frame(self, frame: bytes) -> None:
        """Pass a received IPMB message to the router."""
        logger.debug('IPMB RX [%s]', bytes(frame).hex(' '))
        self._router.handle_frame(self, bytes(frame))

    def _start_receiver(self) -> None:
        """Start the thread that reads messages with `_read_frame()`."""
        self._stop_receiver_event.clear()
        self._receiver = threading.Thread(target=self._receive_loop,
                                          name='%s-rx' % self.NAME,
                                          daemon=True)
        self._receiver.start()

    def _stop_receiver(self) -> None:
        self._stop_receiver_event.set()
        if self._receiver is not None:
            self._wakeup_receiver()
            self._receiver.join()
            self._receiver = None

    def _wakeup_receiver(self) -> None:
        """Interrupt a blocking `_read_frame()`, so that close is fast."""

    def _receive_loop(self) -> None:
        while not self._stop_receiver_event.is_set():
            try:
                frame = self._read_frame(0.05)
            except Exception as e:
                logger.error('%s receive failed: %s', self.NAME, e)
                return
            if frame:
                self._receive_frame(frame)

    def close(self) -> None:
        self._default_router.close()

    def _request(self, header: IpmbHeaderReq,
                 payload: bytes | None) -> bytes:
        """Send a request and return the complete response message."""
        return self._router.request(self, header, payload, self.timeout)

    def is_ipmc_accessible(self, target: Target) -> bool:
        header = IpmbHeaderReq()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = 1
        self._request(header, None)
        return True

    def _inc_sequence_number(self) -> int:
        with self._sequence_lock:
            self.next_sequence_number = (self.next_sequence_number + 1) % 64
            return self.next_sequence_number

    def _send_and_receive(self, target: Target, lun: int, netfn: int,
                          cmdid: int, payload: bytes) -> bytes:
        """Send a request and receive the response.

        target: IPMI target
        lun: logical unit number
        netfn: network function
        cmdid: command id
        payload: IPMI message payload as bytestring

        Returns the response data as bytestring, starting with the
        completion code.
        """
        # assemble IPMB header
        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self._inc_sequence_number()
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = cmdid

        retries = 0
        while retries < self.max_retries:
            try:
                rx_data = self._request(header, payload)
                break
            except IpmiTimeoutError:
                pass
            except OSError:
                pass

            retries += 1
            time.sleep(retries * 0.2)

        else:
            raise IpmiTimeoutError()

        return bytes(rx_data[6:-1])

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])
