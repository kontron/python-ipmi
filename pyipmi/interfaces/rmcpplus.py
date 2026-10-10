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

"""Native RMCP+ (IPMI v2.0 LAN) interface.

:class:`RmcpPlus` is the interface for IPMI v2.0 sessions over LAN, like
``ipmitool -I lanplus``. It extends the IPMI v1.5 interface
:class:`pyipmi.interfaces.Rmcp`.

The session is established with the Open Session Request and the RAKP
handshake (IPMI v2.0, sections 13.17 to 13.23, 13.31 and 13.32).
Afterwards all IPMI messages are sent as RMCP+ payloads, authenticated
and/or encrypted according to the negotiated cipher suite, see
:data:`CIPHER_SUITES`. The supported algorithms are:

- authentication: RAKP-HMAC-SHA1 and RAKP-HMAC-SHA256
- integrity: none, HMAC-SHA1-96 and HMAC-SHA256-128
- confidentiality: none and AES-CBC-128

AES-CBC-128 (confidentiality) needs the optional `cryptography` package.

Example:
    Open an RMCP+ session with cipher suite 3::

        interface = pyipmi.interfaces.create_interface('rmcpplus',
                                                       cipher_suite=3)
        ipmi = pyipmi.create_connection(interface)
        ipmi.session.set_session_type_rmcp('10.0.0.1', port=623)
        ipmi.session.set_auth_type_user('admin', 'admin')
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        ipmi.open()
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..errors import (AuthenticationError, DecodingError,
                      IpmiLongPasswordError, MessageStatusCodeError,
                      NotSupportedError)
from ..messaging import ChannelAuthenticationCapabilities
from ..msgs import constants, create_request_by_name
from ..session import Session
from ..utils import check_rsp_completion_code
from .rmcp import RMCP_CLASS_IPMI, Rmcp, call_repeatedly

logger = logging.getLogger(__name__)


AUTH_TYPE_RMCP_PLUS = 0x06

PAYLOAD_TYPE_IPMI = 0x00
PAYLOAD_TYPE_OPEN_SESSION_REQUEST = 0x10
PAYLOAD_TYPE_OPEN_SESSION_RESPONSE = 0x11
PAYLOAD_TYPE_RAKP_1 = 0x12
PAYLOAD_TYPE_RAKP_2 = 0x13
PAYLOAD_TYPE_RAKP_3 = 0x14
PAYLOAD_TYPE_RAKP_4 = 0x15

PAYLOAD_TYPE_MASK = 0x3f
PAYLOAD_ENCRYPTED = 0x80
PAYLOAD_AUTHENTICATED = 0x40

AUTH_ALGO_RAKP_NONE = 0x00
AUTH_ALGO_RAKP_HMAC_SHA1 = 0x01
AUTH_ALGO_RAKP_HMAC_MD5 = 0x02
AUTH_ALGO_RAKP_HMAC_SHA256 = 0x03

INTEGRITY_ALGO_NONE = 0x00
INTEGRITY_ALGO_HMAC_SHA1_96 = 0x01
INTEGRITY_ALGO_HMAC_MD5_128 = 0x02
INTEGRITY_ALGO_MD5_128 = 0x03
INTEGRITY_ALGO_HMAC_SHA256_128 = 0x04

CONFIDENTIALITY_ALGO_NONE = 0x00
CONFIDENTIALITY_ALGO_AES_CBC_128 = 0x01

CHANNEL_NUMBER_FOR_THIS = 0x0e

# name-only lookup of the user (IPMI v2.0, table 13-11)
RAKP_ROLE_NAME_ONLY_LOOKUP = 0x10

MAX_USER_NAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 20

AES_BLOCK_SIZE = 16

# authentication algorithm -> (hash used for RAKP HMACs and K1/K2,
#                              length of the RAKP4 integrity check value)
AUTH_ALGORITHMS: dict[int, tuple[Callable, int]] = {
    AUTH_ALGO_RAKP_HMAC_SHA1: (hashlib.sha1, 12),
    AUTH_ALGO_RAKP_HMAC_SHA256: (hashlib.sha256, 16),
}

# integrity algorithm -> (hash, length of the truncated auth code)
INTEGRITY_ALGORITHMS: dict[int, tuple[Callable, int]] = {
    INTEGRITY_ALGO_HMAC_SHA1_96: (hashlib.sha1, 12),
    INTEGRITY_ALGO_HMAC_SHA256_128: (hashlib.sha256, 16),
}


@dataclass(frozen=True)
class CipherSuite:
    """A cipher suite, the algorithms of a session (IPMI v2.0, table 22-20).

    Attributes:
        id: The cipher suite ID.
        authentication: The authentication algorithm of the RAKP
            handshake, one of the ``AUTH_ALGO_RAKP_*`` constants.
        integrity: The integrity algorithm, one of the
            ``INTEGRITY_ALGO_*`` constants.
        confidentiality: The confidentiality algorithm, one of the
            ``CONFIDENTIALITY_ALGO_*`` constants.
    """

    id: int
    authentication: int
    integrity: int
    confidentiality: int


# IPMI v2.0, table 22-20; cipher suite 0 (no authentication) is deliberately
# not supported.
CIPHER_SUITES = {
    1: CipherSuite(1, AUTH_ALGO_RAKP_HMAC_SHA1, INTEGRITY_ALGO_NONE,
                   CONFIDENTIALITY_ALGO_NONE),
    2: CipherSuite(2, AUTH_ALGO_RAKP_HMAC_SHA1, INTEGRITY_ALGO_HMAC_SHA1_96,
                   CONFIDENTIALITY_ALGO_NONE),
    3: CipherSuite(3, AUTH_ALGO_RAKP_HMAC_SHA1, INTEGRITY_ALGO_HMAC_SHA1_96,
                   CONFIDENTIALITY_ALGO_AES_CBC_128),
    15: CipherSuite(15, AUTH_ALGO_RAKP_HMAC_SHA256, INTEGRITY_ALGO_NONE,
                    CONFIDENTIALITY_ALGO_NONE),
    16: CipherSuite(16, AUTH_ALGO_RAKP_HMAC_SHA256,
                    INTEGRITY_ALGO_HMAC_SHA256_128, CONFIDENTIALITY_ALGO_NONE),
    17: CipherSuite(17, AUTH_ALGO_RAKP_HMAC_SHA256,
                    INTEGRITY_ALGO_HMAC_SHA256_128,
                    CONFIDENTIALITY_ALGO_AES_CBC_128),
}

# tried in this order if no cipher suite is given
DEFAULT_CIPHER_SUITES = (17, 3)

# status codes that mean the BMC does not accept the proposed algorithms,
# in this case the next cipher suite is tried
_MSC_ALGORITHM_REJECTED = (
    constants.MSC_INVALID_AUTHENTICATION_ALGORITHM,
    constants.MSC_INVALID_INTEGRITY_ALGORITHM,
    constants.MSC_NO_MATCHING_AUTHENTICATION_PAYLOAD,
    constants.MSC_NO_MATCHING_INTEGRITY_PAYLOAD,
    constants.MSC_INVALID_CONFIDENTIALITY_ALGORITHM,
    constants.MSC_NO_CIPHER_SUITE_MATCH,
)


AES_NOT_AVAILABLE = ('AES-CBC-128 confidentiality needs the "cryptography" '
                     'package (pip install python-ipmi[rmcpplus])')


def _aes_cipher(key: bytes, iv: bytes) -> Any:
    try:
        from cryptography.hazmat.primitives.ciphers import (Cipher,
                                                            algorithms, modes)
    except ImportError:
        raise NotSupportedError(AES_NOT_AVAILABLE) from None
    return Cipher(algorithms.AES(key), modes.CBC(iv))


def aes_available() -> bool:
    """Check if AES-CBC-128 is available.

    Returns:
        True if the `cryptography` package is installed.
    """
    try:
        _aes_cipher(bytes(AES_BLOCK_SIZE), bytes(AES_BLOCK_SIZE))
    except NotSupportedError:
        return False
    return True


class SessionKeys:
    """Keys of an established RMCP+ session (IPMI v2.0, section 13.32).

    K1 is the key of the integrity algorithm, K2 the key of the
    confidentiality algorithm (its first 16 bytes for AES-CBC-128). Both
    are generated from the session integrity key (SIK) with the hash of
    the authentication algorithm.
    """

    def __init__(self, suite: CipherSuite, sik: bytes) -> None:
        """Generate the keys K1 and K2.

        Args:
            suite: The negotiated cipher suite.
            sik: The session integrity key of the RAKP handshake.
        """
        self.suite = suite
        digest = AUTH_ALGORITHMS[suite.authentication][0]
        n = digest().digest_size
        self.k1 = hmac.new(sik, b'\x01' * n, digest).digest()
        self.k2 = hmac.new(sik, b'\x02' * n, digest).digest()

    @property
    def authenticated(self) -> bool:
        """True if the payloads are authenticated (an integrity code)."""
        return self.suite.integrity != INTEGRITY_ALGO_NONE

    @property
    def encrypted(self) -> bool:
        """True if the payloads are encrypted."""
        return self.suite.confidentiality != CONFIDENTIALITY_ALGO_NONE

    def auth_code(self, data: bytes) -> bytes:
        """Calculate the integrity code (AuthCode) of a message.

        Args:
            data: The message, from the AuthType up to the Next Header
                field of the session trailer.

        Returns:
            The HMAC with key K1, truncated to :attr:`auth_code_length`.
        """
        (digest, length) = INTEGRITY_ALGORITHMS[self.suite.integrity]
        return hmac.new(self.k1, data, digest).digest()[:length]

    @property
    def auth_code_length(self) -> int:
        """The length of the integrity code in bytes."""
        return INTEGRITY_ALGORITHMS[self.suite.integrity][1]

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt a payload with AES-CBC-128.

        The payload is padded with the confidentiality pad and encrypted
        with a random initialization vector.

        Args:
            data: The payload.

        Returns:
            The initialization vector followed by the encrypted payload.

        Raises:
            NotSupportedError: The `cryptography` package is not
                installed.
        """
        # confidentiality pad: 1, 2, 3, ... followed by the pad length
        pad_length = (-(len(data) + 1)) % AES_BLOCK_SIZE
        data += bytes(range(1, pad_length + 1)) + bytes([pad_length])
        iv = os.urandom(AES_BLOCK_SIZE)
        encryptor = _aes_cipher(self.k2[:AES_BLOCK_SIZE], iv).encryptor()
        return iv + encryptor.update(data) + encryptor.finalize()

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt a payload encrypted with AES-CBC-128.

        Args:
            data: The initialization vector followed by the encrypted
                payload.

        Returns:
            The payload without the confidentiality pad.

        Raises:
            DecodingError: The length or the confidentiality pad is
                invalid.
            NotSupportedError: The `cryptography` package is not
                installed.
        """
        if len(data) < 2 * AES_BLOCK_SIZE or len(data) % AES_BLOCK_SIZE:
            raise DecodingError('invalid encrypted payload length '
                                f'{len(data):d}')
        iv = data[:AES_BLOCK_SIZE]
        decryptor = _aes_cipher(self.k2[:AES_BLOCK_SIZE], iv).decryptor()
        data = decryptor.update(data[AES_BLOCK_SIZE:]) + decryptor.finalize()
        pad_length = data[-1]
        pad = bytes(range(1, pad_length + 1))
        if pad_length >= AES_BLOCK_SIZE or data[-1 - pad_length:-1] != pad:
            raise DecodingError('invalid confidentiality pad')
        return data[:-1 - pad_length]


RMCPPLUS_HEADER_FORMAT = '<BBIIH'
RMCPPLUS_HEADER_LENGTH = struct.calcsize(RMCPPLUS_HEADER_FORMAT)
RMCPPLUS_NEXT_HEADER = 0x07


def pack_rmcpplus(payload_type: int, payload: bytes, session_id: int = 0,
                  sequence_number: int = 0,
                  keys: SessionKeys | None = None) -> bytes:
    """Pack an RMCP+ session header, payload and session trailer.

    Without keys, or if the cipher suite of the keys uses neither
    integrity nor confidentiality, the message has no session trailer
    and the payload is sent in the clear.

    Args:
        payload_type: The payload type, one of the ``PAYLOAD_TYPE_*``
            constants.
        payload: The payload.
        session_id: The session ID of the managed system, 0 outside of a
            session.
        sequence_number: The session sequence number.
        keys: The keys of the session, None outside of a session.

    Returns:
        The RMCP+ message, without the RMCP header.
    """
    if keys is not None and keys.encrypted:
        payload = keys.encrypt(payload)
        payload_type |= PAYLOAD_ENCRYPTED
    if keys is not None and keys.authenticated:
        payload_type |= PAYLOAD_AUTHENTICATED

    pdu = struct.pack(RMCPPLUS_HEADER_FORMAT, AUTH_TYPE_RMCP_PLUS,
                      payload_type, session_id, sequence_number,
                      len(payload))
    pdu += payload

    if keys is not None and keys.authenticated:
        # integrity pad: AuthType up to Next Header is a multiple of 4
        pad_length = (-(len(pdu) + 2)) % 4
        pdu += b'\xff' * pad_length + bytes([pad_length, RMCPPLUS_NEXT_HEADER])
        pdu += keys.auth_code(pdu)

    return pdu


def unpack_rmcpplus(pdu: bytes, keys: SessionKeys | None = None
                    ) -> tuple[int, int, int, bytes]:
    """Unpack and verify an RMCP+ message.

    The integrity code is checked and the payload decrypted with the keys
    of the session.

    Args:
        pdu: The RMCP+ message, without the RMCP header.
        keys: The keys of the session, None outside of a session.

    Returns:
        A tuple ``(payload_type, session_id, sequence_number, payload)``,
        the payload type without the encrypted and authenticated bits.

    Raises:
        DecodingError: The message is invalid, or not authenticated or
            encrypted as expected by the keys.
        AuthenticationError: The integrity check failed, or the payload
            is not authenticated within an authenticated session.
    """
    if len(pdu) < RMCPPLUS_HEADER_LENGTH:
        raise DecodingError('short RMCP+ header')

    (auth_type, payload_type, session_id, sequence_number, length) = \
        struct.unpack(RMCPPLUS_HEADER_FORMAT, pdu[:RMCPPLUS_HEADER_LENGTH])

    if auth_type != AUTH_TYPE_RMCP_PLUS:
        raise DecodingError(f'invalid authentication type 0x{auth_type:02x}')

    end = RMCPPLUS_HEADER_LENGTH + length
    if len(pdu) < end:
        raise DecodingError('short SDU')
    payload = pdu[RMCPPLUS_HEADER_LENGTH:end]

    if payload_type & PAYLOAD_AUTHENTICATED:
        if keys is None or not keys.authenticated:
            raise DecodingError('unexpected authenticated payload')
        n = keys.auth_code_length
        if len(pdu) < end + 2 + n:
            raise DecodingError('short session trailer')
        if not hmac.compare_digest(keys.auth_code(pdu[:-n]), pdu[-n:]):
            raise AuthenticationError('RMCP+ integrity check failed')
        pad_length = pdu[-n - 2]
        if end + pad_length + 2 + n != len(pdu):
            raise DecodingError('invalid session trailer')
    elif keys is not None and keys.authenticated:
        raise AuthenticationError('unauthenticated payload within an '
                                  'authenticated session')
    elif len(pdu) > end:
        raise DecodingError('SDU has extra bytes')

    if payload_type & PAYLOAD_ENCRYPTED:
        if keys is None or not keys.encrypted:
            raise DecodingError('unexpected encrypted payload')
        payload = keys.decrypt(payload)
    elif keys is not None and keys.encrypted:
        raise DecodingError('unencrypted payload within an encrypted session')

    return (payload_type & PAYLOAD_TYPE_MASK, session_id, sequence_number,
            payload)


def _algorithm_payload(payload_type: int, algorithm: int) -> bytes:
    return struct.pack('<BxxBBxxx', payload_type, 8, algorithm)


class RmcpPlus(Rmcp):
    """Native RMCP+ (IPMI v2.0 LAN, a.k.a. "lanplus") interface.

    The session is established by :meth:`establish_session`, which is
    called by :meth:`pyipmi.Ipmi.open`. Before the session is established
    the messages are sent as IPMI v1.5 messages, see
    :class:`pyipmi.interfaces.Rmcp`.
    """

    NAME = 'rmcpplus'

    def __init__(self, slave_address: int = 0x81,
                 host_target_address: int = 0x20,
                 keep_alive_interval: int = 1, max_retries: int = 0,
                 quirks_cfg: dict | None = None,
                 cipher_suite: int | None = None,
                 kg: bytes | None = None) -> None:
        """Initialize the RMCP+ interface.

        Args:
            slave_address: See :class:`Rmcp`.
            host_target_address: See :class:`Rmcp`.
            keep_alive_interval: See :class:`Rmcp`.
            max_retries: See :class:`Rmcp`.
            quirks_cfg: See :class:`Rmcp`.
            cipher_suite: The cipher suite ID (1, 2, 3, 15, 16 or 17) to
                use. If None (default), cipher suite 17 and then 3 are
                tried.
            kg: The BMC key K_G. If None (default), the user password is
                used as specified for BMCs without a K_G.

        Raises:
            NotSupportedError: The cipher suite is not supported.
        """
        super().__init__(slave_address=slave_address,
                         host_target_address=host_target_address,
                         keep_alive_interval=keep_alive_interval,
                         max_retries=max_retries, quirks_cfg=quirks_cfg)

        self.cipher_suites: tuple[int, ...]
        if cipher_suite is None:
            self.cipher_suites = DEFAULT_CIPHER_SUITES
        elif cipher_suite in CIPHER_SUITES:
            self.cipher_suites = (cipher_suite,)
        else:
            raise NotSupportedError(f"cipher suite {cipher_suite} (supported: "
                                    f"{', '.join(map(str, CIPHER_SUITES))})")
        self.kg = kg
        self._keys: SessionKeys | None = None
        self._console_session_id = 0
        self._message_tag = 0

    def _next_message_tag(self) -> int:
        self._message_tag = (self._message_tag + 1) & 0xff
        return self._message_tag

    def _send_payload(self, payload_type: int, payload: bytes) -> None:
        if self._keys is not None:
            # the keys are set when the session is established
            assert self._session is not None
            self._session.increment_sequence_number()
            pdu = pack_rmcpplus(payload_type, payload, self._session.sid,
                                self._session.sequence_number, self._keys)
        else:
            pdu = pack_rmcpplus(payload_type, payload)
        self._send_rmcp_msg(pdu, RMCP_CLASS_IPMI)

    def _receive_payload(self) -> tuple[int, bytes]:
        (_, class_of_msg, pdu) = self._receive_rmcp_msg()
        if class_of_msg != RMCP_CLASS_IPMI:
            raise DecodingError('invalid class field in RMCP message')
        (payload_type, session_id, _, payload) = \
            unpack_rmcpplus(pdu, self._keys)
        if self._keys is not None and session_id != self._console_session_id:
            raise DecodingError(f'invalid session ID 0x{session_id:08x}')
        return (payload_type, payload)

    def _send_ipmi_msg(self, data: bytes) -> None:
        if self._keys is None:
            # before the session is established (Get Channel Authentication
            # Capabilities) IPMI v1.5 messages are used
            super()._send_ipmi_msg(data)
            return
        logger.debug('IPMI TX: %s', data.hex(' '))
        self._send_payload(PAYLOAD_TYPE_IPMI, data)

    def _receive_ipmi_msg(self, ignore_sdu_length: bool = False) -> bytes:
        if self._keys is None:
            return super()._receive_ipmi_msg(ignore_sdu_length)
        while True:
            (payload_type, data) = self._receive_payload()
            if payload_type == PAYLOAD_TYPE_IPMI:
                break
            logger.debug('ignoring payload type 0x%02x', payload_type)
        logger.debug('IPMI RX: %s', data.hex(' '))
        return data

    def _get_channel_auth_cap(
            self, session: Session) -> ChannelAuthenticationCapabilities:
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.target = self.host_target
        req.channel.number = CHANNEL_NUMBER_FOR_THIS
        # request the IPMI v2.0 extended capabilities
        req.channel.type = 1
        req.privilege_level.requested = session.priv_level
        rsp = self.send_and_receive(req)
        check_rsp_completion_code(rsp)
        return ChannelAuthenticationCapabilities(rsp)

    def _handshake(self, request_type: int, request: bytes,
                   response_type: int) -> bytes:
        """Send a session setup message and wait for the response."""
        tag = request[0]
        retry = 0
        while True:
            self._send_payload(request_type, request)
            try:
                while True:
                    try:
                        (payload_type, payload) = self._receive_payload()
                    except DecodingError as e:
                        logger.debug('ignoring invalid message: %s', e)
                        continue
                    if (payload_type == response_type
                            and payload[:1] == bytes([tag])):
                        break
                    logger.debug('ignoring payload type 0x%02x', payload_type)
            except TimeoutError:
                retry += 1
                if retry > self.max_retries:
                    raise
                continue

            # check the status first, some BMCs send truncated error
            # responses
            if len(payload) >= 2 and payload[1] != constants.MSC_OK:
                raise MessageStatusCodeError(payload[1])
            if len(payload) < 8:
                raise DecodingError('short session setup message')
            return payload

    def _open_session(self, session: Session, suite: CipherSuite) -> int:
        """Send the Open Session Request, returns the managed system SID."""
        self._console_session_id = \
            struct.unpack('<I', os.urandom(4))[0] or 1
        request = struct.pack('<BBxxI', self._next_message_tag(),
                              session.priv_level, self._console_session_id)
        request += _algorithm_payload(0, suite.authentication)
        request += _algorithm_payload(1, suite.integrity)
        request += _algorithm_payload(2, suite.confidentiality)

        rsp = self._handshake(PAYLOAD_TYPE_OPEN_SESSION_REQUEST, request,
                              PAYLOAD_TYPE_OPEN_SESSION_RESPONSE)
        if len(rsp) < 36:
            raise DecodingError('short Open Session Response')
        (console_session_id, managed_session_id) = \
            struct.unpack('<II', rsp[4:12])
        if console_session_id != self._console_session_id:
            raise DecodingError('Open Session Response: console session ID '
                                'mismatch')
        algorithms = (rsp[16] & 0x3f, rsp[24] & 0x3f, rsp[32] & 0x3f)
        if algorithms != (suite.authentication, suite.integrity,
                          suite.confidentiality):
            raise DecodingError('Open Session Response: BMC selected other '
                                f'algorithms {algorithms}')
        return managed_session_id

    def _rakp(self, session: Session, suite: CipherSuite,
              managed_session_id: int) -> bytes:
        """Do the RAKP handshake, returns the session integrity key."""
        username = session.auth_username_bytes
        password = session.auth_password_bytes
        if len(username) > MAX_USER_NAME_LENGTH:
            raise AuthenticationError('user name longer than '
                                      f'{MAX_USER_NAME_LENGTH:d} bytes')
        if len(password) > MAX_PASSWORD_LENGTH:
            raise IpmiLongPasswordError('password longer than '
                                        f'{MAX_PASSWORD_LENGTH:d} bytes')

        digest = AUTH_ALGORITHMS[suite.authentication][0]
        icv_length = AUTH_ALGORITHMS[suite.authentication][1]
        kuid = password
        kg = self.kg if self.kg else kuid
        sid_m = struct.pack('<I', self._console_session_id)
        sid_c = struct.pack('<I', managed_session_id)
        rm = os.urandom(16)
        role_m = session.priv_level | RAKP_ROLE_NAME_ONLY_LOOKUP
        # ROLEm, ULENGTHm and UNAMEm as used in the HMAC calculations
        role = bytes([role_m, len(username)]) + username

        # RAKP message 1 / 2
        request = struct.pack('<BxxxI16sBxxB', self._next_message_tag(),
                              managed_session_id, rm, role_m, len(username))
        request += username
        rsp = self._handshake(PAYLOAD_TYPE_RAKP_1, request,
                              PAYLOAD_TYPE_RAKP_2)
        if len(rsp) < 40:
            raise DecodingError('short RAKP message 2')
        if rsp[4:8] != sid_m:
            raise DecodingError('RAKP message 2: console session ID mismatch')
        rc = rsp[8:24]
        guid_c = rsp[24:40]
        expected = hmac.new(kuid, sid_m + sid_c + rm + rc + guid_c + role,
                            digest).digest()
        if not hmac.compare_digest(expected, rsp[40:]):
            # tell the BMC, so it can release the session
            self._send_payload(PAYLOAD_TYPE_RAKP_3, struct.pack(
                '<BBxxI', self._next_message_tag(),
                constants.MSC_INVALID_INTEGRITY_CHECK_VALUE,
                managed_session_id))
            raise AuthenticationError('RAKP message 2: invalid key exchange '
                                      'authentication code (wrong password?)')

        # RAKP message 3 / 4
        request = struct.pack('<BBxxI', self._next_message_tag(),
                              constants.MSC_OK, managed_session_id)
        request += hmac.new(kuid, rc + sid_m + role, digest).digest()
        rsp = self._handshake(PAYLOAD_TYPE_RAKP_3, request,
                              PAYLOAD_TYPE_RAKP_4)
        if rsp[4:8] != sid_m:
            raise DecodingError('RAKP message 4: console session ID mismatch')

        sik = hmac.new(kg, rm + rc + role, digest).digest()
        expected = hmac.new(sik, rm + sid_c + guid_c,
                            digest).digest()[:icv_length]
        if not hmac.compare_digest(expected, rsp[8:]):
            raise AuthenticationError('RAKP message 4: invalid integrity '
                                      'check value')
        return sik

    def establish_session(self, session: Session) -> None:
        """Establish an IPMI v2.0 session with the BMC.

        The BMC is pinged and asked for its authentication capabilities.
        Then the cipher suites are tried in order with the Open Session
        Request until the BMC accepts one, the cipher suites with
        AES-CBC-128 only if the `cryptography` package is installed. The
        RAKP handshake authenticates the user and generates the session
        keys. Finally, the privilege level of the session is set and, if
        configured, the keep alive thread is started.

        Args:
            session: The session with the host, the port, the user and
                the privilege level. Its session ID and sequence number
                are set.

        Raises:
            IpmiConnectionError: The BMC does not answer the RMCP ping.
            NotSupportedError: The BMC does not support IPMI v2.0, or
                only cipher suites with AES-CBC-128 are configured and
                the `cryptography` package is not installed.
            MessageStatusCodeError: The BMC rejected the Open Session
                Request or a RAKP message, e.g. none of the cipher
                suites is accepted.
            AuthenticationError: The user name is too long or the
                authentication failed, e.g. with a wrong password.
            IpmiLongPasswordError: The password is longer than 20 bytes.
            DecodingError: An invalid response was received.
        """
        self._session = None
        self._keys = None
        self.host = session.rmcp_host
        self.port = session.rmcp_port
        self._sock.connect((self.host, self.port))

        self.ping()

        logger.debug('Get Channel Authentication Capabilities')
        caps = self._get_channel_auth_cap(session)
        logger.debug('%s', caps)
        if not caps.ipmi_2_0:
            raise NotSupportedError('BMC does not support IPMI v2.0 (RMCP+)')

        suites = [CIPHER_SUITES[i] for i in self.cipher_suites]
        if not aes_available():
            suites = [s for s in suites
                      if s.confidentiality == CONFIDENTIALITY_ALGO_NONE]
            if not suites:
                raise NotSupportedError(AES_NOT_AVAILABLE)

        for suite in suites:
            logger.debug('Open Session with cipher suite %d', suite.id)
            try:
                managed_session_id = self._open_session(session, suite)
                break
            except MessageStatusCodeError as e:
                if (e.msc not in _MSC_ALGORITHM_REJECTED
                        or suite is suites[-1]):
                    raise
                logger.debug('cipher suite %d rejected: %s', suite.id, e)

        sik = self._rakp(session, suite, managed_session_id)

        session.sid = managed_session_id
        session.sequence_number = 0
        session.activated = True
        self._session = session
        self._keys = SessionKeys(suite, sik)
        logger.debug('Session opened (cipher suite %d)', suite.id)

        self._set_session_privilege_level(session.priv_level)

        if self.keep_alive_interval:
            self._stop_keep_alive = call_repeatedly(
                    self.keep_alive_interval, self._keep_alive)

    def close_session(self) -> None:
        """Stop the keep alive thread and close the session.

        The session keys are removed, also if closing the session fails.
        """
        if self._session is None:
            if self._stop_keep_alive:
                self._stop_keep_alive()
            return
        try:
            super().close_session()
        finally:
            self._keys = None
