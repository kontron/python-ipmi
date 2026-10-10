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

"""A simulated IPMB, without hardware.

The bus is a broker, :class:`IpmbSimBroker`, a server on a Unix domain
socket. The :class:`IpmbSim` interfaces connect to it and register with
their IPMB address. The broker forwards each IPMB message to the
interface registered with the responder address (rsSA) of the message,
like the I2C bus delivers it to the device with that slave address. A
message to an address without an interface is not delivered, the sender
gets a NAK, like on I2C, and its request fails without waiting for the
timeout.

The broker runs on its own, ``-v`` logs every message::

    pyipmi -v ipmbsim broker --socket /tmp/ipmb.sock

or in a program, e.g. an emulator of a BMC::

    broker = IpmbSimBroker('/tmp/ipmb.sock')
    broker.start()

Example:
    Get the device ID of the BMC on the simulated bus::

        interface = pyipmi.interfaces.create_interface(
            'ipmbsim', slave_address=0x81, path='/tmp/ipmb.sock')
        ipmi = pyipmi.create_connection(interface)
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        with ipmi:
            print(ipmi.get_device_id())

The protocol on the socket is a stream of messages: the type (1 byte),
the length of the payload (1 byte) and the payload.

==============  ====  ======================================================
Message         Type  Payload
==============  ====  ======================================================
``REGISTER``    0x01  client: the protocol version (1) and the IPMB address
``REGISTERED``  0x02  broker: ``STATUS_OK`` or the reason of the refusal
``FRAME``       0x03  both: an IPMB message, starting with the rsSA
``STATUS``      0x04  broker: ``STATUS_OK`` if the last ``FRAME`` of the
                      client is delivered, ``STATUS_NAK`` if not
==============  ====  ======================================================
"""

from __future__ import annotations

import logging
import os
import queue
import selectors
import socket
import tempfile
import threading

from ..errors import IpmiConnectionError
from .ipmb import IpmbInterface
from .router import MessageRouter

logger = logging.getLogger(__name__)

DEFAULT_PATH = os.path.join(tempfile.gettempdir(), 'pyipmi-ipmb.sock')

PROTOCOL_VERSION = 1

MSG_REGISTER = 0x01
MSG_REGISTERED = 0x02
MSG_FRAME = 0x03
MSG_STATUS = 0x04

STATUS_OK = 0
# REGISTERED: the address is registered by another interface
STATUS_ADDRESS_IN_USE = 1
# REGISTERED: the address is 0x00 or 0xff, or the interface is registered
STATUS_INVALID_ADDRESS = 2
# REGISTERED: the protocol version is not supported
STATUS_UNSUPPORTED_VERSION = 3
# STATUS: no interface has the responder address of the message, or the
# sender is not registered
STATUS_NAK = 1

# the seconds the broker waits for an interface to take a message
SEND_TIMEOUT = 1.0

REGISTER_ERRORS = {
    STATUS_ADDRESS_IN_USE: 'the address is used by another interface',
    STATUS_INVALID_ADDRESS: 'the address is invalid (0x01 to 0xfe)',
    STATUS_UNSUPPORTED_VERSION: 'the protocol version is not supported',
}


def encode_msg(msg_type: int, payload: bytes) -> bytes:
    """Return a message of the protocol."""
    if len(payload) > 0xff:
        raise ValueError(f'the payload of {len(payload)} bytes is too long')
    return bytes((msg_type, len(payload))) + payload


def take_msg(buffer: bytearray) -> tuple[int, bytes] | None:
    """Remove the first complete message from the buffer and return it.

    Returns:
        The type and the payload of the message, None if the buffer has no
        complete message.
    """
    if len(buffer) < 2 or len(buffer) < 2 + buffer[1]:
        return None
    msg = (buffer[0], bytes(buffer[2:2 + buffer[1]]))
    del buffer[:2 + buffer[1]]
    return msg


def decode_msgs(buffer: bytearray) -> list[tuple[int, bytes]]:
    """Remove the complete messages from the buffer and return them.

    Returns:
        The type and the payload of each message.
    """
    msgs = []
    while (msg := take_msg(buffer)) is not None:
        msgs.append(msg)
    return msgs


def is_valid_address(address: int) -> bool:
    """Return True for an address an interface can register.

    These are 0x01 to 0xfe: the slave addresses of the IPMB devices, and
    for requesters also the odd ones, e.g. 0x81, which tools use as their
    requester address. 0x00 is the broadcast address.
    """
    return 0 < address < 0xff


class _Client:
    """A connection of an interface to the broker."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = bytearray()
        self.address: int | None = None

    def send(self, msg_type: int, payload: bytes) -> None:
        self.sock.sendall(encode_msg(msg_type, payload))

    def __str__(self) -> str:
        if self.address is None:
            return f'client {self.sock.fileno()}'
        return f'0x{self.address:02x}'


class IpmbSimBroker:
    """The simulated IPMB: forwards the messages between the interfaces."""

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        """Initialize the broker.

        Args:
            path: The path of the Unix domain socket.
        """
        self.path = path
        self._server: socket.socket | None = None
        self._selector = selectors.DefaultSelector()
        self._clients: dict[socket.socket, _Client] = {}
        self._addresses: dict[int, _Client] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def addresses(self) -> list[int]:
        """The IPMB addresses of the registered interfaces."""
        with self._lock:
            return sorted(self._addresses)

    def listen(self) -> None:
        """Create the socket of the bus.

        A socket file left by a broker that is not running anymore is
        replaced.

        Raises:
            OSError: The socket cannot be created, e.g. a broker is
                running on the path already.
        """
        if os.path.exists(self.path):
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(self.path)
            except OSError:
                # no broker is listening there
                os.unlink(self.path)
            else:
                raise OSError(f'a broker is running on {self.path} already')
            finally:
                probe.close()
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.path)
        self._server.listen()
        self._server.setblocking(False)
        self._selector.register(self._server, selectors.EVENT_READ)
        logger.info('IPMB broker listening on %s', self.path)

    def start(self) -> None:
        """Create the socket and forward the messages in a thread."""
        self.listen()
        self._thread = threading.Thread(target=self.serve_forever,
                                        name='ipmbsim-broker', daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        """Forward the messages until the broker is closed.

        When it returns, also by an exception, e.g. ``KeyboardInterrupt``,
        the connections are closed and the socket is removed.
        """
        if self._server is None:
            self.listen()
        try:
            while not self._stop.is_set():
                for (key, _) in self._selector.select(timeout=0.1):
                    if key.fileobj is self._server:
                        self._accept()
                    else:
                        assert isinstance(key.fileobj, socket.socket)
                        self._read(key.fileobj)
        finally:
            self._shutdown()

    def close(self) -> None:
        """Stop the broker, close all connections and remove the socket."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _shutdown(self) -> None:
        for sock in list(self._clients):
            self._drop(sock)
        if self._server is not None:
            self._selector.unregister(self._server)
            self._server.close()
            self._server = None
            try:
                os.unlink(self.path)
            except OSError:
                pass
        self._selector.close()
        logger.info('IPMB broker closed')

    def _accept(self) -> None:
        assert self._server is not None
        (sock, _) = self._server.accept()
        # an interface that does not read its messages is dropped instead
        # of blocking the bus
        sock.settimeout(SEND_TIMEOUT)
        self._clients[sock] = _Client(sock)
        self._selector.register(sock, selectors.EVENT_READ)

    def _drop(self, sock: socket.socket) -> None:
        client = self._clients.pop(sock)
        with self._lock:
            if (client.address is not None
                    and self._addresses.get(client.address) is client):
                del self._addresses[client.address]
                logger.info('IPMB 0x%02x disconnected', client.address)
        self._selector.unregister(sock)
        sock.close()

    def _read(self, sock: socket.socket) -> None:
        client = self._clients[sock]
        try:
            data = sock.recv(4096)
        except OSError:
            data = b''
        if not data:
            self._drop(sock)
            return
        client.buffer += data
        for (msg_type, payload) in decode_msgs(client.buffer):
            try:
                self._handle(client, msg_type, payload)
            except OSError as e:
                logger.warning('IPMB %s: %s', client, e)
                self._drop(sock)
                return

    def _handle(self, client: _Client, msg_type: int,
                payload: bytes) -> None:
        if msg_type == MSG_REGISTER:
            client.send(MSG_REGISTERED, bytes((self._register(client,
                                                              payload),)))
        elif msg_type == MSG_FRAME:
            client.send(MSG_STATUS, bytes((self._forward(client, payload),)))
        else:
            logger.debug('IPMB %s: unknown message type 0x%02x', client,
                         msg_type)

    def _register(self, client: _Client, payload: bytes) -> int:
        if len(payload) != 2 or payload[0] != PROTOCOL_VERSION:
            return STATUS_UNSUPPORTED_VERSION
        address = payload[1]
        if client.address is not None or not is_valid_address(address):
            return STATUS_INVALID_ADDRESS
        with self._lock:
            if address in self._addresses:
                logger.info('IPMB 0x%02x refused, the address is in use',
                            address)
                return STATUS_ADDRESS_IN_USE
            self._addresses[address] = client
        client.address = address
        logger.info('IPMB 0x%02x connected', address)
        return STATUS_OK

    def _forward(self, client: _Client, frame: bytes) -> int:
        if client.address is None or not frame:
            return STATUS_NAK
        with self._lock:
            receiver = self._addresses.get(frame[0])
        if receiver is None or receiver is client:
            logger.debug('IPMB %s -> 0x%02x NAK [%s]', client, frame[0],
                         frame.hex(' '))
            return STATUS_NAK
        logger.debug('IPMB %s -> 0x%02x [%s]', client, frame[0],
                     frame.hex(' '))
        try:
            receiver.send(MSG_FRAME, frame)
        except OSError as e:
            logger.warning('IPMB %s: %s', receiver, e)
            self._drop(receiver.sock)
            return STATUS_NAK
        return STATUS_OK


class IpmbSim(IpmbInterface):
    """An interface on the simulated IPMB of an :class:`IpmbSimBroker`.

    The interface registers its slave address at the broker and receives
    the messages to that address in a receive thread, which passes them to
    the router, so the interface can also answer incoming requests (see
    `MessageRouter`).
    """

    NAME = 'ipmbsim'

    def __init__(self, slave_address: int = 0x20, path: str = DEFAULT_PATH,
                 router: MessageRouter | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The own IPMB address, registered at the broker.
            path: The path of the Unix domain socket of the broker.
            router: The router of the received messages, see
                :class:`~pyipmi.interfaces.ipmb.IpmbInterface`.
        """
        super().__init__(slave_address, router)
        self.path = path
        # the time to wait for an answer of the broker
        self.broker_timeout = 1.0
        self._sock: socket.socket | None = None
        self._buffer = bytearray()
        self._answers: queue.Queue[tuple[int, bytes]] = queue.Queue()
        self._send_lock = threading.Lock()

    def open(self) -> None:
        """Connect to the broker, register the address and start receiving.

        Raises:
            IpmiConnectionError: The broker is not running, or it refused
                the address.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.path)
        except OSError as e:
            sock.close()
            raise IpmiConnectionError(
                f'no IPMB broker on {self.path}: {e}') from e
        self._sock = sock
        self._buffer.clear()
        self._start_receiver()
        try:
            status = self._call(MSG_REGISTER, MSG_REGISTERED,
                                bytes((PROTOCOL_VERSION, self.slave_address)))
        except OSError as e:
            self.close()
            raise IpmiConnectionError(str(e)) from e
        if status != STATUS_OK:
            self.close()
            reason = REGISTER_ERRORS.get(status, f'status {status}')
            raise IpmiConnectionError(
                f'the IPMB broker refused 0x{self.slave_address:02x}: '
                f'{reason}')

    def close(self) -> None:
        """Stop the receive thread and close the connection."""
        if self._sock is not None:
            # the receive thread ends when the connection is shut down
            self._stop_receiver_event.set()
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._stop_receiver()
            self._sock.close()
            self._sock = None
        super().close()

    def _call(self, msg_type: int, answer_type: int, payload: bytes) -> int:
        """Send a message to the broker and return the status it answers."""
        if self._sock is None:
            raise OSError('the interface is not open')
        with self._send_lock:
            # a late answer to a call that timed out
            while not self._answers.empty():
                self._answers.get_nowait()
            self._sock.sendall(encode_msg(msg_type, payload))
            try:
                (received_type, answer) = self._answers.get(
                    timeout=self.broker_timeout)
            except queue.Empty:
                raise OSError('no answer of the IPMB broker') from None
        if received_type != answer_type or len(answer) != 1:
            raise OSError('invalid answer of the IPMB broker')
        return answer[0]

    def send_frame(self, frame: bytes) -> None:
        """Send a complete IPMB message, starting with rsSA.

        Args:
            frame: The message.

        Raises:
            OSError: No interface has the address rsSA (NAK), or the
                broker is not reachable.
        """
        logger.debug('IPMB TX [%s]', bytes(frame).hex(' '))
        if self._call(MSG_FRAME, MSG_STATUS, bytes(frame)) != STATUS_OK:
            raise OSError(f'no device at IPMB address 0x{frame[0]:02x} (NAK)')

    def _read_frame(self, timeout: float) -> bytes | None:
        # the answers of the broker are passed to _call(), the frames are
        # returned
        assert self._sock is not None
        while True:
            while (msg := take_msg(self._buffer)) is not None:
                if msg[0] == MSG_FRAME:
                    # the next messages stay in the buffer for the next call
                    return msg[1]
                self._answers.put(msg)
            self._sock.settimeout(timeout)
            try:
                data = self._sock.recv(4096)
            except TimeoutError:
                return None
            if not data:
                if self._stop_receiver_event.is_set():
                    return None
                raise OSError('the IPMB broker closed the connection')
            self._buffer += data
