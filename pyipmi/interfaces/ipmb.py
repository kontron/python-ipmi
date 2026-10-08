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

"""IPMB messages and the base class of the IPMB interfaces.

The Intelligent Platform Management Bus (IPMB) is the I2C bus between the
management controllers. :class:`IpmbInterface` is the base class of the
interfaces that are directly connected to an IPMB:
:class:`~pyipmi.interfaces.Aardvark`, :class:`~pyipmi.interfaces.IpmbDev`
and :class:`~pyipmi.interfaces.OpenIpmbLink`.

The functions encode and decode IPMB messages, including the bridged
messages embedded in Send Message requests. The RMCP interface uses them
too.
"""

from __future__ import annotations

import logging
import threading
import time
from array import array
from typing import TYPE_CHECKING
from collections.abc import Iterable, Sequence

from .. import Routing, Target
from ..errors import IpmiTimeoutError
from ..msgs import (create_message, create_request_by_name,
                    encode_message, decode_message, constants)
from ..utils import check_completion_code
from ..utils import py3_array_tobytes, py3_array_frombytes
from .base import Interface

logger = logging.getLogger(__name__)

# rqSA, netFn/rqLUN, checksum, rsSA, rqSeq/rsLUN, cmd, checksum
IPMB_MIN_MSG_LEN = 7

if TYPE_CHECKING:
    from .router import MessageRouter


def checksum(data: Iterable[int]) -> int:
    """Calculate the IPMB checksum.

    Args:
        data: The bytes to calculate the checksum of.

    Returns:
        The checksum, so that the sum of the bytes and the checksum is 0
        modulo 256.
    """
    csum = 0
    for b in data:
        csum += b
    return -csum % 256


class IpmbHeader:
    """Representation of the IPMB message header.

    The field names are the same for the request and the response, only the
    order on the bus differs.

    Request::

        *-------*--------------*----------*-------*---------------*-------*
        | rs_sa | netfn/rs_lun | checksum | rq_sa | rq_seq/rq_lun | cmdid |
        *-------*--------------*----------*-------*---------------*-------*

    Response::

        *-------*--------------*----------*-------*---------------*-------*
        | rq_sa | netfn/rq_lun | checksum | rs_sa | rq_seq/rs_lun | cmdid |
        *-------*--------------*----------*-------*---------------*-------*
    """

    rs_sa: int
    rs_lun: int
    rq_sa: int
    rq_lun: int
    rq_seq: int
    netfn: int
    cmdid: int
    checksum: int

    def __init__(self, data: Sequence[int] | None = None) -> None:
        """Initialize the header.

        Args:
            data: The message to decode the header from, the fields are not
                set if not given.
        """
        if data:
            self.decode(data)

    def decode(self, data: Sequence[int]) -> None:
        """Decode the header from the first 6 bytes of a message.

        Args:
            data: The message.
        """
        raise NotImplementedError()

    def __str__(self) -> str:
        """Return the fields of the header."""
        return f'rs_sa=0x{self.rs_sa:02x}, rs_lun={self.rs_lun}, ' \
               f'rq_sa=0x{self.rq_sa:02x}, rq_lun={self.rq_lun}, ' \
               f'rq_seq={self.rq_seq}, ' \
               f'netfn=0x{self.netfn:02x}, ' \
               f'cmdid=0x{self.cmdid:02x}'


class IpmbHeaderReq(IpmbHeader):
    """Representation of the IPMI request message header."""

    def encode(self) -> bytes:
        """Encode the header.

        Returns:
            The first 6 bytes of the message, including the header
            checksum.
        """
        data = array('B')
        data.append(self.rs_sa)
        data.append(self.netfn << 2 | self.rs_lun)
        data.append(checksum((self.rs_sa, data[1])))
        data.append(self.rq_sa)
        data.append(self.rq_seq << 2 | self.rq_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data: Sequence[int]) -> None:
        """Decode the header from the first 6 bytes of a message.

        Args:
            data: The message.
        """
        msg = array('B', data)
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
        """Encode the header.

        Returns:
            The first 6 bytes of the message, including the header
            checksum.
        """
        data = array('B')
        data.append(self.rq_sa)
        data.append(self.netfn << 2 | self.rq_lun)
        data.append(checksum((self.rq_sa, data[1])))
        data.append(self.rs_sa)
        data.append(self.rq_seq << 2 | self.rs_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data: Sequence[int]) -> None:
        """Decode the header from the first 6 bytes of a message.

        Args:
            data: The message.
        """
        msg = array('B', data)
        self.rq_sa = msg[0]
        self.netfn = msg[1] >> 2
        self.rq_lun = msg[1] & 3
        self.checksum = msg[2]
        self.rs_sa = msg[3]
        self.rq_seq = msg[4] >> 2
        self.rs_lun = msg[4] & 3
        self.cmdid = msg[5]

    def from_req_header(self, req_header: IpmbHeaderReq) -> None:
        """Set up the header of the response to the given request.

        The fields keep their meaning (rq_sa is the requester), encode()
        puts them in the response order. The network function is the one of
        the response.

        Args:
            req_header: The header of the request.
        """
        self.rs_lun = req_header.rs_lun
        self.rs_sa = req_header.rs_sa
        self.rq_seq = req_header.rq_seq
        self.rq_lun = req_header.rq_lun
        self.rq_sa = req_header.rq_sa
        self.netfn = req_header.netfn | 1
        self.cmdid = req_header.cmdid


def encode_ipmb_msg(header: IpmbHeaderReq | IpmbHeaderRsp,
                    data: bytes | None) -> bytes:
    """Encode an IPMB message.

    Args:
        header: The header of the message.
        data: The message data after the command ID, None for no data.

    Returns:
        The message, including both checksums.
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
    """Encode a Send Message request that embeds a message.

    Args:
        payload: The message to embed, a complete IPMB message.
        rq_sa: The requester slave address.
        rs_sa: The responder slave address, the bridge.
        channel: The channel the bridge sends the message on.
        seq: The sequence number.
        tracking: The tracking request of the Send Message request.

    Returns:
        The Send Message request as IPMB message.
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
    """Encode a (multi-)bridged request.

    The request is addressed with the last hop of the routing and embedded
    in a Send Message request for each of the other hops, from the last to
    the first.

    Args:
        routing: The hops to the target, see
            :meth:`pyipmi.Target.set_routing`.
        header: The header of the request, its rq_sa and rs_sa are set
            from the last hop.
        payload: The request data after the command ID.
        seq: The sequence number of the Send Message requests.

    Returns:
        The message to send to the first hop.

    Raises:
        ValueError: The channel of a hop, except the last, is missing.
    """
    # change header requester addresses for bridging
    header.rq_sa = routing[-1].rq_sa
    header.rs_sa = routing[-1].rs_sa
    tx_data = encode_ipmb_msg(header, payload)

    for bridge in reversed(routing[:-1]):
        if bridge.channel is None:
            raise ValueError('bridge channel of routing entry missing: '
                             f'{bridge}')
        tx_data = encode_send_message(tx_data,
                                      rq_sa=bridge.rq_sa,
                                      rs_sa=bridge.rs_sa,
                                      channel=bridge.channel,
                                      seq=seq)

    return tx_data


def decode_bridged_message(rx_data: bytes) -> bytes:
    """Decode a (multi-)bridged response.

    The Send Message responses around the response are removed, as long as
    the message is a Send Message response.

    Args:
        rx_data: The received IPMB message.

    Returns:
        The embedded response message.

    Raises:
        CompletionCodeError: A Send Message response failed.
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


def target_ipmb_address(target: Target) -> int:
    """Return the IPMB address of a target.

    Args:
        target: The target.

    Returns:
        The IPMB address.

    Raises:
        ValueError: The target has no IPMB address.
    """
    if target.ipmb_address is None:
        raise ValueError(f'IPMB address of the target missing: {target}')
    return target.ipmb_address


def rx_filter(header: IpmbHeaderReq, data: bytes | array, rq_sa: bool = False,
              rs_sa: bool = False, rq_lun: bool = False,
              rs_lun: bool = True, rq_seq: bool = True) -> bool:
    """Check if a received message is the response to a request.

    The checksums, the network function (of the response) and the command
    ID are always checked, the other fields as selected. Mismatches are
    logged.

    Args:
        header: The header of the request.
        data: The received message.
        rq_sa: Check the requester slave address.
        rs_sa: Check the responder slave address.
        rq_lun: Check the requester LUN.
        rs_lun: Check the responder LUN.
        rq_seq: Check the sequence number.

    Returns:
        True if the message matches.
    """
    if len(data) < IPMB_MIN_MSG_LEN:
        logger.debug(f'message too short: {len(data):d} bytes')
        return False

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

    A request is sent directly to the IPMB address of the target, the
    routing of the target is not used. It is tried up to ``max_retries``
    times, each try waits ``timeout`` seconds for the response.
    """

    def __init__(self, slave_address: int = 0x20,
                 router: MessageRouter | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The own IPMB address, the requester address of
                the requests.
            router: The router of the received messages, a router of the
                interface that ignores incoming requests if not given.
        """
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
        """The router of the received messages.

        Setting None sets the default router, which ignores incoming
        requests.
        """
        return self._router

    @router.setter
    def router(self, router: MessageRouter | None) -> None:
        self._router = router if router is not None else self._default_router

    @property
    def _logger(self) -> logging.Logger:
        """Logger of the module that implements the interface.

        Received frames are logged there, next to the sent frames.
        """
        return logging.getLogger(type(self).__module__)

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
        self._logger.debug('IPMB RX [%s]', bytes(frame).hex(' '))
        self._router.handle_frame(self, bytes(frame))

    def _start_receiver(self) -> None:
        """Start the thread that reads messages with `_read_frame()`."""
        self._stop_receiver_event.clear()
        self._receiver = threading.Thread(target=self._receive_loop,
                                          name=f'{self.NAME}-rx',
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
                self._logger.error('%s receive failed: %s', self.NAME, e)
                return
            if frame:
                self._receive_frame(frame)

    def close(self) -> None:
        """Stop the worker thread of the default router."""
        self._default_router.close()

    def _request(self, header: IpmbHeaderReq,
                 payload: bytes | None) -> bytes:
        """Send a request and return the complete response message."""
        return self._router.request(self, header, payload, self.timeout)

    def is_target_accessible(self, target: Target) -> bool:
        """Check if the target answers a Get Device ID request.

        Args:
            target: The target.

        Returns:
            True, the target answered.

        Raises:
            IpmiTimeoutError: The target did not answer.
        """
        header = IpmbHeaderReq()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target_ipmb_address(target)
        header.rq_seq = self._inc_sequence_number()
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

        Args:
            target: The target.
            lun: The logical unit number.
            netfn: The network function.
            cmdid: The command ID.
            payload: The request data after the command ID.

        Returns:
            The response data, starting with the completion code.

        Raises:
            IpmiTimeoutError: No response after ``max_retries`` tries.
        """
        # assemble IPMB header
        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target_ipmb_address(target)
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
        """Send a raw request and return the raw response.

        Args:
            target: The target.
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code.

        Raises:
            IpmiTimeoutError: No response after ``max_retries`` tries.
        """
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])
