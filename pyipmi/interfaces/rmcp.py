# Copyright (c) 2018  Kontron Europe GmbH
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

"""Native RMCP interface, IPMI v1.5 over LAN.

The :class:`Rmcp` interface sends IPMI messages in RMCP packets over UDP
to a BMC, like ``ipmitool -I lan``. Establishing the session starts with
an ASF presence ping, then the IPMI v1.5 session is activated with the
authentication type (none, straight password or MD5) that the BMC
supports. Requests to targets behind the BMC are bridged with Send
Message requests.

The packets are built by :class:`RmcpMsg` (the RMCP header),
:class:`AsfMsg` with :class:`AsfPing` and :class:`AsfPong` (the ASF
messages) and :class:`IpmiMsg` (the IPMI v1.5 session header).

Example:
    Get the device ID of a BMC::

        interface = pyipmi.interfaces.create_interface('rmcp')
        ipmi = pyipmi.create_connection(interface)
        ipmi.session.set_session_type_rmcp('10.0.0.1', port=623)
        ipmi.session.set_auth_type_user('admin', 'admin')
        ipmi.target = pyipmi.Target(ipmb_address=0x20)

        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import logging
import socket
import struct
import hashlib
import random
import threading
import time
from array import array
from typing import Any
from collections.abc import Callable

from .. import Target
from ..session import Session
from ..msgs import create_request_by_name, constants, Message
from ..messaging import ChannelAuthenticationCapabilities
from ..errors import (DecodingError, IpmiConnectionError, NotSupportedError,
                      RetryError)
from .base import Interface
from ..interfaces.ipmb import (IpmbHeaderReq, encode_ipmb_msg,
                               encode_bridged_message, decode_bridged_message,
                               rx_filter, target_ipmb_address)
from ..utils import (check_completion_code, check_rsp_completion_code,
                     py3_array_tobytes)

logger = logging.getLogger(__name__)


CLASS_NORMAL_MSG = 0x00
CLASS_ACK_MSG = 0x80

RMCP_CLASS_ASF = 0x06
RMCP_CLASS_IPMI = 0x07
RMCP_CLASS_OEM = 0x08


def call_repeatedly(interval: float, func: Callable[..., Any],
                    *args: Any) -> Callable[[], None]:
    """Call a function repeatedly in a background thread.

    The first call is after ``interval`` seconds. A TimeoutError raised by
    the function is ignored.

    Args:
        interval: The time between the calls in seconds.
        func: The function to call.
        *args: The arguments of the function.

    Returns:
        A function that stops the calls.
    """
    stopped = threading.Event()

    def loop() -> None:
        # the first call is in `interval` secs
        while not stopped.wait(interval):
            try:
                func(*args)
            except TimeoutError:
                pass

    t = threading.Thread(target=loop)
    t.daemon = True
    t.start()

    return stopped.set


class RmcpMsg:
    """The RMCP header of a packet.

    The header contains the version, the sequence number and the class of
    the message, e.g. ASF or IPMI.
    """

    RMCP_HEADER_FORMAT = '!BxBB'
    ASF_RMCP_V_1_0 = 6
    version: int | None = None
    seq_number: int | None = None
    class_of_msg: int | None = None

    def __init__(self, class_of_msg: int | None = None) -> None:
        """Initialize the RMCP header.

        Args:
            class_of_msg: The class of the message, e.g.
                ``RMCP_CLASS_IPMI``.
        """
        if class_of_msg is not None:
            self.class_of_msg = class_of_msg

    def pack(self, sdu: bytes | None, seq_number: int) -> bytes:
        """Build the packet with the RMCP header.

        Args:
            sdu: The data that follows the header, e.g. an IPMI message.
            seq_number: The RMCP sequence number, 0xff for messages that
                are not acknowledged.

        Returns:
            The packet.
        """
        pdu = struct.pack(self.RMCP_HEADER_FORMAT, self.ASF_RMCP_V_1_0,
                          seq_number, self.class_of_msg)
        if sdu is not None:
            pdu += sdu
        return pdu

    def unpack(self, pdu: bytes) -> bytes:
        """Decode the RMCP header of a packet.

        Args:
            pdu: The packet.

        Returns:
            The data that follows the header.

        Raises:
            DecodingError: The RMCP version is not 1.0.
        """
        header_len = struct.calcsize(self.RMCP_HEADER_FORMAT)
        header = pdu[:header_len]
        (self.version, self.seq_number, self.class_of_msg) = \
            struct.unpack(self.RMCP_HEADER_FORMAT, header)
        sdu = pdu[header_len:]

        if self.version != self.ASF_RMCP_V_1_0:
            raise DecodingError('invalid RMCP version field')

        return sdu


class AsfMsg:
    """An ASF message, the data of an RMCP packet of the ASF class.

    The header contains the IANA enterprise number (4542 for ASF), the
    message type, the message tag and the data length.
    """

    ASF_HEADER_FORMAT = '!IBBxB'

    ASF_TYPE_PRESENCE_PONG = 0x40
    ASF_TYPE_PRESENCE_PING = 0x80

    asf_type = 0

    def __init__(self) -> None:
        """Initialize the ASF message without data."""
        self.iana_enterprise_number = 4542
        self.tag = 0
        self.data: bytes | None = None
        self.sdu: bytes | None = None

    def pack(self) -> bytes:
        """Build the ASF message.

        Returns:
            The ASF header followed by the data.
        """
        if self.data:
            data_len = len(self.data)
        else:
            data_len = 0

        pdu = struct.pack(self.ASF_HEADER_FORMAT,
                          self.iana_enterprise_number,
                          self.asf_type,
                          self.tag,
                          data_len)
        if self.data:
            pdu += self.data

        return pdu

    def unpack(self, sdu: bytes) -> None:
        """Decode an ASF message.

        Args:
            sdu: The ASF message.

        Raises:
            DecodingError: The length of the message does not match the
                data length of the header, or the header is invalid for
                the message type.
        """
        self.sdu = sdu
        header_len = struct.calcsize(self.ASF_HEADER_FORMAT)

        header = sdu[:header_len]
        (self.iana_enterprise_number, self.asf_type, self.tag, data_len) = \
            struct.unpack(self.ASF_HEADER_FORMAT, header)

        if len(sdu) < header_len + data_len:
            raise DecodingError('short SDU')
        elif len(sdu) > header_len + data_len:
            raise DecodingError('SDU has extra bytes')

        if data_len != 0:
            self.data = sdu[header_len:header_len + data_len]
        else:
            self.data = None

        if hasattr(self, 'check_header'):
            self.check_header()

    def __str__(self) -> str:
        """Return the data, or the whole message, as hex bytes."""
        if self.data:
            return ' '.join('%02x' % b for b in array('B', self.data))
        if self.sdu:
            return ' '.join('%02x' % b for b in array('B', self.sdu))
        return ''

    @staticmethod
    def from_data(sdu: bytes) -> AsfMsg:
        """Decode an ASF message into the class for its type.

        Args:
            sdu: The ASF message.

        Returns:
            The :class:`AsfPing` or :class:`AsfPong` message.

        Raises:
            DecodingError: The message type is not supported or the
                message is invalid.
        """
        asf = AsfMsg()
        asf.unpack(sdu)

        try:
            cls = {
                AsfMsg().ASF_TYPE_PRESENCE_PING: AsfPing,
                AsfMsg().ASF_TYPE_PRESENCE_PONG: AsfPong,
            }[asf.asf_type]
        except KeyError:
            raise DecodingError('Unsupported ASF type(0x%02x)' % asf.asf_type) from None

        instance = cls()
        instance.unpack(sdu)
        return instance


class AsfPing(AsfMsg):
    """The ASF Presence Ping message, which has no data."""

    def __init__(self) -> None:
        """Initialize the ping message."""
        AsfMsg.__init__(self)
        self.asf_type = self.ASF_TYPE_PRESENCE_PING

    def check_header(self) -> None:
        """Check the header of a decoded ping message.

        Raises:
            DecodingError: The type is not Presence Ping or the message
                has data.
        """
        if self.asf_type != self.ASF_TYPE_PRESENCE_PING:
            raise DecodingError('type does not match')
        if self.data:
            raise DecodingError('Data length is not zero')

    def __str__(self) -> str:
        """Return the message as string."""
        return 'ping: ' + super(AsfMsg, self).__str__()


class AsfPong(AsfMsg):
    """The ASF Presence Pong message, the answer to a Presence Ping.

    The data contains the OEM IANA enterprise number, OEM defined data and
    the supported entities and interactions, e.g. if IPMI is supported.
    """

    DATA_FORMAT = '!IIBB6x'

    def __init__(self) -> None:
        """Initialize the pong message."""
        AsfMsg.__init__(self)
        self.asf_type = self.ASF_TYPE_PRESENCE_PONG
        self.oem_iana_enterprise_number = 4542
        self.oem_defined = 0
        self.supported_entities = 0
        self.supported_interactions = 0

    def pack(self) -> bytes:
        """Build the pong message.

        Returns:
            The ASF header followed by the pong data.
        """
        # the pong data follows the ASF header
        self.data = struct.pack(self.DATA_FORMAT,
                                self.oem_iana_enterprise_number,
                                self.oem_defined,
                                self.supported_entities,
                                self.supported_interactions)
        return AsfMsg.pack(self)

    def unpack(self, sdu: bytes) -> None:
        """Decode a pong message.

        Args:
            sdu: The ASF message.

        Raises:
            DecodingError: The message is not a valid pong message.
        """
        AsfMsg.unpack(self, sdu)
        # check_header() made sure that the data is present
        assert self.data is not None
        # header_len = struct.calcsize(self.ASF_HEADER_FORMAT)
        (self.oem_iana_enterprise_number, self.oem_defined,
            self.supported_entities, self.supported_interactions) =\
            struct.unpack(self.DATA_FORMAT, self.data)

        self.check_data()

    def check_data(self) -> None:
        """Check the data of a decoded pong message.

        Raises:
            DecodingError: The OEM defined data is set for the ASF IANA
                enterprise number, or the reserved supported interactions
                are set.
        """
        if self.oem_iana_enterprise_number == 4542 and self.oem_defined != 0:
            raise DecodingError('SDU malformed')
        if self.supported_interactions != 0:
            raise DecodingError('SDU malformed')

    def check_header(self) -> None:
        """Check the header of a decoded pong message.

        Raises:
            DecodingError: The type is not Presence Pong or the data
                length is wrong.
        """
        if self.asf_type != self.ASF_TYPE_PRESENCE_PONG:
            raise DecodingError('type does not match')
        if self.data is None \
                or len(self.data) != struct.calcsize(self.DATA_FORMAT):
            raise DecodingError('Data length mismatch')


class IpmiMsg:
    """The IPMI v1.5 session header of an IPMI message over LAN.

    The header contains the authentication type, the session sequence
    number, the session ID, the authentication code (if the
    authentication type is not none) and the length of the IPMI message.
    """

    HEADER_FORMAT_NO_AUTH = '!BIIB'
    HEADER_FORMAT_AUTH = '!BII16BB'

    def __init__(self, session: Session | None = None,
                 ignore_sdu_length: bool = False) -> None:
        """Initialize the session header.

        Args:
            session: The session, which provides the authentication type,
                the session ID, the sequence number and the password. None
                for a message outside of a session.
            ignore_sdu_length: Don't check the message length of the
                header when unpacking a message.
        """
        self.session = session
        self.ignore_sdu_length = ignore_sdu_length

    def _pack_session_id(self) -> int:
        if self.session is not None:
            session_id = self.session.sid
        else:
            session_id = 0
        return struct.unpack("<I", struct.pack(">I", session_id))[0]

    def _pack_sequence_number(self) -> int:
        if self.session is not None:
            seq = self.session.sequence_number
        else:
            seq = 0

        return struct.unpack("<I", struct.pack(">I", seq))[0]

    def _padd_password(self) -> bytes:
        """Pad the password.

        The password/key is 0 padded to 16-bytes for all specified
        authentication types.
        """
        password = b''
        if self.session is not None:
            password = self.session.auth_password_bytes
        return password.ljust(16, b'\x00')

    def _pack_auth_code_straight(self) -> bytes:
        """Return the auth code as bytestring."""
        return self._padd_password()

    def _pack_auth_code_md5(self, sdu: bytes) -> bytes:
        auth_code = struct.pack('>16s I %ds I 16s' % len(sdu),
                                self._pack_auth_code_straight(),
                                self._pack_session_id(),
                                sdu,
                                self._pack_sequence_number(),
                                self._pack_auth_code_straight())
        return hashlib.md5(auth_code).digest()

    def pack(self, sdu: bytes | None) -> bytes:
        """Build the IPMI message with the session header.

        The sequence number of an activated session is incremented.

        Args:
            sdu: The IPMI message.

        Returns:
            The session header followed by the IPMI message.

        Raises:
            NotSupportedError: The authentication type of the session is
                not supported.
        """
        if sdu is not None:
            data_len = len(sdu)
        else:
            data_len = 0

        if self.session is not None:
            auth_type = self.session.auth_type
            if self.session.activated:
                self.session.increment_sequence_number()
        else:
            auth_type = Session.AUTH_TYPE_NONE

        pdu = struct.pack('!BII',
                          auth_type,
                          self._pack_sequence_number(),
                          self._pack_session_id())

        if auth_type == Session.AUTH_TYPE_NONE:
            pass
        elif auth_type == Session.AUTH_TYPE_PASSWORD:
            pdu += self._pack_auth_code_straight()
        elif auth_type == Session.AUTH_TYPE_MD5:
            pdu += self._pack_auth_code_md5(sdu or b'')
        else:
            raise NotSupportedError('authentication type %s' % auth_type)

        pdu += py3_array_tobytes(array('B', [data_len]))

        if sdu is not None:
            pdu += sdu

        return pdu

    def unpack(self, pdu: bytes) -> bytes | None:
        """Decode the session header of an IPMI message.

        Args:
            pdu: The session header followed by the IPMI message.

        Returns:
            The IPMI message, None if it is empty.

        Raises:
            DecodingError: The length of the message does not match the
                header, unless ``ignore_sdu_length`` is set.
        """
        auth_type = array('B', pdu)[0]

        if auth_type != 0:
            header_len = struct.calcsize(self.HEADER_FORMAT_AUTH)
            header = pdu[:header_len]
            # TBD .. find a way to do this better
            self.auth_type = array('B', pdu)[0]
            (self.sequence_number,) = struct.unpack('!I', pdu[1:5])
            (self.session_id,) = struct.unpack('!I', pdu[5:9])
            self.auth_code = list(struct.unpack('!16B', pdu[9:25]))
            data_len = array('B', pdu)[25]
        else:
            header_len = struct.calcsize(self.HEADER_FORMAT_NO_AUTH)
            header = pdu[:header_len]
            (self.auth_type, self.sequence_number, self.session_id,
                data_len) = struct.unpack(self.HEADER_FORMAT_NO_AUTH, header)

        if not self.ignore_sdu_length:
            if len(pdu) < header_len + data_len:
                raise DecodingError('short SDU')
            elif len(pdu) > header_len + data_len:
                raise DecodingError(
                    f'SDU has extra bytes ({len(pdu):d},{header_len:d},{data_len:d} )')

        if hasattr(self, 'check_header'):
            self.check_header()

        if not self.ignore_sdu_length:
            if data_len != 0:
                sdu = pdu[header_len:header_len + data_len]
            else:
                sdu = None
        else:
            try:
                sdu = pdu[header_len:]
                sdu = None if sdu == b'' else sdu
            except IndexError:
                sdu = None

        return sdu

    def check_data(self) -> None:
        """Check the data of a decoded message, nothing to check."""

    def check_header(self) -> None:
        """Check the header of a decoded message, nothing to check."""


class Rmcp(Interface):
    """The native RMCP interface, IPMI v1.5 over LAN.

    The host and the port of the BMC and the user are taken from the
    session (see :meth:`pyipmi.session.Session.set_session_type_rmcp`),
    when it is established. While the session is open, a Get Device ID
    request is sent to keep it alive if no other request was sent in the
    keep-alive interval.
    """

    NAME = 'rmcp'
    # 45 bytes LAN message length minus 7 bytes message header and checksums
    MAX_REQUEST_DATA_SIZE = 38

    _session: Session | None = None

    def __init__(self, slave_address: int = 0x81,
                 host_target_address: int = 0x20,
                 keep_alive_interval: int = 1, max_retries: int = 0,
                 quirks_cfg: dict | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The IPMB address of this requester.
            host_target_address: The IPMB address of the BMC.
            keep_alive_interval: The interval in seconds of the requests
                that keep the session alive, 0 disables them.
            max_retries: The number of times a request is sent again after
                a timeout.
            quirks_cfg: Additional configuration parameters:

                - ``rmcp_ignore_sdu_length`` (bool): Don't verify the SDU
                  length of a received IPMI message. By default a
                  mismatch between the received SDU length and the
                  ``payload_length`` field of the PDU header raises an
                  exception. With True the header field is ignored and the
                  PDU is unpacked anyway.
                - ``rmcp_ignore_rq_seq`` (bool): Don't verify the sequence
                  number of a response. The default is False.

        Example:
            Create an interface that ignores the SDU length::

                interfaces.create_interface(
                    interface="rmcp",
                    quirks_cfg={'rmcp_ignore_sdu_length': True}
                )
        """
        self.host: str | None = None
        self.port: int | None = None
        self.seq_number = 0xff
        self.slave_address = slave_address
        self.host_target = Target(host_target_address)
        self.max_retries = max_retries
        self.next_sequence_number = 0
        self.keep_alive_interval = keep_alive_interval
        self._stop_keep_alive: Callable[[], None] | None = None
        self._last_request_time = 0.0
        self._timeout: float | None = None
        self.transaction_lock = threading.Lock()
        if quirks_cfg is None:
            quirks_cfg = {}
        self.quirks_cfg = quirks_cfg
        self.ignore_sdu_length = quirks_cfg.get('rmcp_ignore_sdu_length', False)
        self.ignore_rq_seq = quirks_cfg.get('rmcp_ignore_rq_seq', False)

    def open(self) -> None:
        """Create the UDP socket, with a timeout of 2 seconds."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_timeout(2.0)

    def close(self) -> None:
        """Close the interface, nothing to do."""

    def _send_rmcp_msg(self, sdu: bytes | None, class_of_msg: int) -> None:
        rmcp = RmcpMsg(class_of_msg)
        pdu = rmcp.pack(sdu, self.seq_number)
        self._sock.send(pdu)
        if self.seq_number != 255:
            self.seq_number = (self.seq_number + 1) % 254

    def _receive_rmcp_msg(self) -> tuple[int | None, int | None, bytes]:
        pdu = self._sock.recv(4096)
        rmcp = RmcpMsg()
        sdu = rmcp.unpack(pdu)
        return (rmcp.seq_number, rmcp.class_of_msg, sdu)

    def set_timeout(self, timeout: float) -> None:
        """Set the time to wait for a response.

        Args:
            timeout: The timeout in seconds.
        """
        self._timeout = timeout
        self._sock.settimeout(timeout)

    def _send_ipmi_msg(self, data: bytes) -> None:
        logger.debug('IPMI TX: {:s}'.format(
            ' '.join('%02x' % b for b in array('B', data))))
        ipmi = IpmiMsg(self._session)
        tx_data = ipmi.pack(data)
        self._send_rmcp_msg(tx_data, RMCP_CLASS_IPMI)

    def _receive_ipmi_msg(self, ignore_sdu_length: bool = False) -> bytes:
        (_, class_of_msg, pdu) = self._receive_rmcp_msg()
        if class_of_msg != RMCP_CLASS_IPMI:
            raise DecodingError('invalid class field in ASF message')
        msg = IpmiMsg(ignore_sdu_length=ignore_sdu_length)
        data = msg.unpack(pdu) or b''
        logger.debug('IPMI RX: {:s}'.format(
            ' '.join('%02x' % b for b in array('B', data))))
        return data

    def _send_asf_msg(self, msg: AsfMsg) -> None:
        logger.debug('ASF TX: msg')
        self._send_rmcp_msg(msg.pack(), RMCP_CLASS_ASF)

    def _receive_asf_msg(self, cls: type[AsfMsg]) -> AsfMsg:
        (_, class_of_msg, data) = self._receive_rmcp_msg()
        logger.debug('ASF RX: msg')
        if class_of_msg != RMCP_CLASS_ASF:
            raise DecodingError('invalid class field in ASF message')
        msg = cls()
        msg.unpack(data)
        return msg

    def ping(self) -> None:
        """Send an ASF Presence Ping and wait for the Presence Pong.

        Raises:
            IpmiConnectionError: The BMC does not answer or the connection
                is refused.
            DecodingError: The answer is not a valid Presence Pong.
        """
        ping = AsfPing()
        try:
            self._send_asf_msg(ping)
            self._receive_asf_msg(AsfPong)
        except TimeoutError:
            raise IpmiConnectionError(
                f'no response to RMCP ping from {self.host}:{self.port}, '
                'check host, port and network connectivity') from None
        except ConnectionRefusedError:
            raise IpmiConnectionError(
                f'connection to {self.host}:{self.port} refused, '
                'is the BMC listening on this port?') from None

    def _get_channel_auth_cap(
            self, session: Session) -> ChannelAuthenticationCapabilities:
        CHANNEL_NUMBER_FOR_THIS = 0xe
        # get channel auth cap
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.target = self.host_target
        req.channel.number = CHANNEL_NUMBER_FOR_THIS
        req.privilege_level.requested = session.priv_level
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        caps = ChannelAuthenticationCapabilities(rsp)
        return caps

    def _get_session_challenge(self, session: Session) -> Message:
        # get session challenge
        req = create_request_by_name('GetSessionChallenge')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        if session.auth_username:
            req.user_name = session.auth_username_bytes.ljust(16, b'\x00')
        rsp = self.send_and_receive(req)
        check_rsp_completion_code(rsp)
        return rsp

    def _activate_session(self, session: Session, challenge: bytes) -> Message:
        # activate session
        req = create_request_by_name('ActivateSession')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        req.privilege_level.maximum_requested = session.priv_level
        req.challenge_string = challenge
        req.session_id = session.sid
        req.initial_outbound_sequence_number = random.randrange(1, 0xffffffff)
        rsp = self.send_and_receive(req)
        check_rsp_completion_code(rsp)
        return rsp

    def _set_session_privilege_level(self, level: int) -> Message:
        req = create_request_by_name('SetSessionPrivilegeLevel')
        req.target = self.host_target
        req.privilege_level.requested = level
        rsp = self.send_and_receive(req)
        check_rsp_completion_code(rsp)
        return rsp

    def _get_device_id(self) -> None:
        req = create_request_by_name('GetDeviceId')
        req.target = self.host_target
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)

    def _keep_alive(self) -> None:
        # every request keeps the session alive, so only send a keep-alive
        # request if the session was idle for the whole interval
        idle = time.monotonic() - self._last_request_time
        if idle >= self.keep_alive_interval:
            self._get_device_id()

    def establish_session(self, session: Session) -> None:
        """Establish an IPMI v1.5 session with the BMC.

        Connect to the host and port of the session, ping the BMC, get the
        channel authentication capabilities, get the session challenge
        with the strongest supported authentication type, activate the
        session and set the privilege level. Then start the keep-alive
        requests, if enabled.

        Args:
            session: The session, which provides the host, the port, the
                user and the privilege level.

        Raises:
            IpmiConnectionError: The BMC does not answer the ping.
            CompletionCodeError: A request of the session setup failed.
        """
        self._session = None
        self.host = session.rmcp_host
        self.port = session.rmcp_port
        self._sock.connect((self.host, self.port))

        # 0 - Ping
        self.ping()

        # 1 - Get Channel Authentication Capabilities
        logger.debug('Get Channel Authentication Capabilities')
        caps = self._get_channel_auth_cap(session)
        logger.debug('%s' % caps)

        # 2 - Get Session Challenge
        logger.debug('Get Session Challenge')
        session.auth_type = caps.get_max_auth_type()
        rsp = self._get_session_challenge(session)
        session_challenge = rsp.challenge_string
        session.sid = rsp.temporary_session_id

        self._session = session

        # 3 - Activate Session
        logger.debug('Activate Session')
        rsp = self._activate_session(session, session_challenge)
        session.sid = rsp.session_id
        session.sequence_number = rsp.initial_inbound_sequence_number
        session.activated = True

        logger.debug('Set Session Privilege Level')
        # 4 - Set Session Privilege Level
        self._set_session_privilege_level(session.priv_level)

        logger.debug('Session opened')

        if self.keep_alive_interval:
            self._stop_keep_alive = call_repeatedly(
                    self.keep_alive_interval, self._keep_alive)

    def close_session(self) -> None:
        """Stop the keep-alive requests and close the session.

        Nothing is sent if the session was never established or is
        already closed.

        Raises:
            CompletionCodeError: The Close Session request failed.
        """
        if self._stop_keep_alive:
            self._stop_keep_alive()

        if self._session is None or self._session.activated is False:
            # never established or already closed
            logger.debug('Session already closed')
            return

        logger.debug('Close Session %s' % self._session)
        req = create_request_by_name('CloseSession')
        req.target = self.host_target
        req.session_id = self._session.sid
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        self._session.activated = False

    def _inc_sequence_number(self) -> None:
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _receive_response(self, header: IpmbHeaderReq) -> bytes:
        """Receive the response that matches the request `header`.

        Requests are serialized by the transaction lock, so a message that
        does not match is the late response of an earlier request (e.g. one
        that timed out) and is discarded.

        Raises:
            TimeoutError: The response is not received within the timeout.
        """
        deadline = None
        if self._timeout is not None:
            deadline = time.monotonic() + self._timeout

        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError()

            rx_data = self._receive_ipmi_msg(self.ignore_sdu_length)

            if (len(rx_data) > 5 and
                    array('B', rx_data)[5] == constants.CMDID_SEND_MESSAGE):
                rx_data = decode_bridged_message(rx_data)
                if not rx_data:
                    # the forwarded reply is expected in the next packet
                    continue

            if rx_filter(header, rx_data, rq_seq=not self.ignore_rq_seq):
                return rx_data

            logger.debug('discarding message that does not match the request')

    def _send_and_receive(self, target: Target, lun: int, netfn: int,
                          cmdid: int, payload: bytes) -> bytes:
        """Send a request and receive the response.

        The request is bridged with Send Message requests if the target
        has a routing.

        Args:
            target: The target of the request.
            lun: The logical unit number.
            netfn: The network function.
            cmdid: The command ID.
            payload: The request data.

        Returns:
            The response data, starting with the completion code.

        Raises:
            RetryError: No response after ``max_retries`` retries.
        """
        self._inc_sequence_number()

        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target_ipmb_address(target)
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = cmdid

        # Bridge message
        if target.routing:
            tx_data = encode_bridged_message(target.routing, header, payload,
                                             self.next_sequence_number)
        else:
            tx_data = encode_ipmb_msg(header, payload)

        with self.transaction_lock:
            retry = 0
            while retry <= self.max_retries:
                try:
                    self._send_ipmi_msg(tx_data)
                    self._last_request_time = time.monotonic()
                    rx_data = self._receive_response(header)
                    break
                except TimeoutError:
                    retry += 1

        if retry > self.max_retries:
            raise RetryError("Max retry while sending and/or receiving ipmi"
                             f"message for rmcp host {self.host}")

        return rx_data[6:-1]

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Send a raw request and return the raw response.

        Args:
            target: The target of the request.
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code.

        Raises:
            RetryError: No response after ``max_retries`` retries.
        """
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])
