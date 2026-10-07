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

"""Routing of the IPMB messages of the IPMB interfaces.

The IPMB interfaces (:class:`pyipmi.interfaces.ipmb.IpmbInterface`)
pass the received messages to a :class:`MessageRouter`. It matches the
responses to the pending requests and answers the incoming requests with
the registered handlers, so a program can also act as an IPMB device,
e.g. a BMC.

Example:
    Answer Get Device ID requests on bus 0 of an openipmblink bridge::

        def get_device_id(req):
            rsp = create_message(NETFN_APP + 1, CMDID_GET_DEVICE_ID, None)
            rsp.completion_code = 0
            ...
            return rsp

        router = MessageRouter()
        router.register_handler(NETFN_APP, CMDID_GET_DEVICE_ID,
                                get_device_id)
        intf = OpenIpmbLink(port='/dev/ttyACM1', bus=0, router=router)
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, TYPE_CHECKING
from collections.abc import Callable

from ..errors import IpmiTimeoutError
from ..msgs import create_message, encode_message, decode_message, Message
from ..msgs.constants import CC_INV_CMD, CC_UNSPECIFIED_ERROR
from .ipmb import (IPMB_MIN_MSG_LEN, IpmbHeaderReq, IpmbHeaderRsp, checksum,
                   encode_ipmb_msg)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .ipmb import IpmbInterface

RawHandler = Callable[['IpmbInterface', IpmbHeaderReq, bytes], 'bytes | None']
MessageHandler = Callable[[Message], 'Message | None']


def encode_ipmb_response(req_header: IpmbHeaderReq, data: bytes) -> bytes:
    """Encode the IPMB response to a request.

    Args:
        req_header: The header of the received request.
        data: The response data, starting with the completion code.

    Returns:
        The IPMB response message, starting with the rqSA.
    """
    header = IpmbHeaderRsp()
    header.rq_sa = req_header.rq_sa
    header.rq_lun = req_header.rq_lun
    header.rs_sa = req_header.rs_sa
    header.rs_lun = req_header.rs_lun
    header.rq_seq = req_header.rq_seq
    header.netfn = req_header.netfn | 1
    header.cmdid = req_header.cmdid
    return encode_ipmb_msg(header, data)


class _PendingRequest:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.frame: bytes | None = None


class MessageRouter:
    """Decides what happens with IPMB messages of one or more interfaces.

    Outgoing requests are sent with `request()`, which waits for the matching
    response. Incoming messages are passed to `handle_frame()` by the
    interface:

      - responses are matched to a pending request
      - requests are passed to the registered handler, its response is sent
        back on the interface the request was received on

    Request handlers run in a worker thread of the router, never in the
    receive thread of an interface. A handler may therefore send requests
    itself, e.g. to forward a request to another bus. The worker thread is
    started with the first incoming request.
    """

    def __init__(self, unhandled_cc: int | None = CC_INV_CMD) -> None:
        """Initialize the router.

        Args:
            unhandled_cc: The completion code of the response to requests
                without a handler. None ignores these requests.
        """
        self.unhandled_cc = unhandled_cc
        self._handlers: dict[tuple[int, int, int | None], RawHandler] = {}
        self._pending: dict[tuple, _PendingRequest] = {}
        self._lock = threading.Lock()
        self._requests: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

    def close(self) -> None:
        """Stop the worker thread for request handlers."""
        with self._lock:
            worker = self._worker
            self._worker = None
        if worker is not None:
            self._requests.put(None)
            if worker is not threading.current_thread():
                worker.join()

    def register_raw_handler(self, netfn: int, cmdid: int,
                             handler: RawHandler,
                             group_extension: int | None = None) -> None:
        """Register a handler for incoming requests.

        The handler is called with the interface, the request header and the
        request data (without the checksum). It returns the response data,
        starting with the completion code, or None to send no response. If
        the handler raises an exception, the response has the completion
        code 0xff (unspecified error).

        A handler registered with a group extension is used for the
        requests whose first data byte is the group extension, e.g. of
        PICMG or DCMI, before a handler registered without one.

        Args:
            netfn: The network function of the requests.
            cmdid: The command ID of the requests.
            handler: The handler.
            group_extension: The group extension of the requests, None
                for all requests of the command.
        """
        self._handlers[(netfn, cmdid, group_extension)] = handler

    def register_handler(self, netfn: int, cmdid: int,
                         handler: MessageHandler,
                         group_extension: int | None = None) -> None:
        """Register a handler for incoming requests as IPMI messages.

        The handler is called with the decoded request message and returns
        the response message, or None to send no response. If the
        completion code of the response is not 0, only the completion code
        is sent. See :meth:`register_raw_handler`.

        Args:
            netfn: The network function of the requests.
            cmdid: The command ID of the requests.
            handler: The handler.
            group_extension: The group extension of the requests, None
                for all requests of the command.
        """
        def raw_handler(interface: IpmbInterface, header: IpmbHeaderReq,
                        data: bytes) -> bytes | None:
            req = create_message(netfn, cmdid, group_extension)
            decode_message(req, data)
            rsp = handler(req)
            if rsp is None:
                return None
            if rsp.completion_code != 0:
                return bytes((rsp.completion_code,))
            return encode_message(rsp)

        self.register_raw_handler(netfn, cmdid, raw_handler, group_extension)

    def unregister_handler(self, netfn: int, cmdid: int,
                           group_extension: int | None = None) -> None:
        """Remove the handler of a command, if registered.

        Args:
            netfn: The network function of the requests.
            cmdid: The command ID of the requests.
            group_extension: The group extension the handler was
                registered with.
        """
        self._handlers.pop((netfn, cmdid, group_extension), None)

    @staticmethod
    def _pending_key(interface: IpmbInterface, rs_sa: int, netfn: int,
                     cmdid: int, seq: int, rs_lun: int) -> tuple:
        return (id(interface), rs_sa, netfn & ~1, cmdid, seq, rs_lun)

    def request(self, interface: IpmbInterface, header: IpmbHeaderReq,
                payload: bytes | None, timeout: float) -> bytes:
        """Send a request on the interface and wait for its response.

        Args:
            interface: The interface the request is sent on.
            header: The IPMB header of the request.
            payload: The request data, None for no data.
            timeout: The time to wait for the response in seconds.

        Returns:
            The complete IPMB response message, starting with the rqSA.

        Raises:
            IpmiTimeoutError: No response was received.
        """
        key = self._pending_key(interface, header.rs_sa, header.netfn,
                                header.cmdid, header.rq_seq, header.rs_lun)
        pending = _PendingRequest()
        with self._lock:
            self._pending[key] = pending
        try:
            interface.send_frame(encode_ipmb_msg(header, payload))
            if not pending.event.wait(timeout):
                raise IpmiTimeoutError()
            assert pending.frame is not None
            return pending.frame
        finally:
            with self._lock:
                if self._pending.get(key) is pending:
                    del self._pending[key]

    def handle_frame(self, interface: IpmbInterface, frame: bytes) -> None:
        """Handle a message received on the interface.

        Called from the receive thread of the interface; never blocks.
        Messages that are too short or have an invalid checksum are
        dropped. A response is passed to the matching pending request, a
        request is queued for the worker thread.

        Args:
            interface: The interface the message was received on.
            frame: The IPMB message, starting with the rsSA.
        """
        if len(frame) < IPMB_MIN_MSG_LEN:
            logger.debug('IPMB RX message too short [%s]', frame.hex(' '))
            return
        if checksum(frame[0:3]) or checksum(frame[3:]):
            logger.debug('IPMB RX checksum error [%s]', frame.hex(' '))
            return

        netfn = frame[1] >> 2
        if netfn & 1:
            self._handle_response(interface, netfn, frame)
        else:
            self._start_worker()
            self._requests.put((interface, frame))

    def _handle_response(self, interface: IpmbInterface, netfn: int,
                         frame: bytes) -> None:
        key = self._pending_key(interface, rs_sa=frame[3], netfn=netfn,
                                cmdid=frame[5], seq=frame[4] >> 2,
                                rs_lun=frame[4] & 3)
        with self._lock:
            pending = self._pending.pop(key, None)
        if pending is None:
            logger.debug('IPMB RX unexpected response [%s]', frame.hex(' '))
            return
        pending.frame = frame
        pending.event.set()

    def _find_handler(self, header: IpmbHeaderReq,
                      data: bytes) -> RawHandler | None:
        if data:
            handler = self._handlers.get((header.netfn, header.cmdid, data[0]))
            if handler is not None:
                return handler
        return self._handlers.get((header.netfn, header.cmdid, None))

    def _handle_request(self, interface: IpmbInterface, frame: bytes) -> None:
        header = IpmbHeaderReq(data=frame)
        data = frame[6:-1]
        logger.debug('IPMB RX request [%s]', header)

        handler = self._find_handler(header, data)
        rsp_data: bytes | None
        if handler is None:
            if self.unhandled_cc is None:
                return
            rsp_data = bytes((self.unhandled_cc,))
        else:
            try:
                rsp_data = handler(interface, header, data)
            except Exception:
                logger.exception('IPMB request handler failed')
                rsp_data = bytes((CC_UNSPECIFIED_ERROR,))
            if rsp_data is None:
                return

        try:
            interface.send_frame(encode_ipmb_response(header, rsp_data))
        except OSError as e:
            logger.warning('IPMB sending response failed: %s', e)

    def _start_worker(self) -> None:
        with self._lock:
            if self._worker is not None:
                return
            self._worker = threading.Thread(target=self._work,
                                            name='ipmb-router', daemon=True)
            self._worker.start()

    def _work(self) -> None:
        while True:
            item: Any = self._requests.get()
            if item is None:
                return
            self._handle_request(*item)
