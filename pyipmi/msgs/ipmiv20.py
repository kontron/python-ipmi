# Copyright (c) 2014  Kontron Europe GmbH
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

import os

from . import constants
from . import register_ipmiv20_message_class
from . import Message
from . import UnsignedInt
from . import Bitfield
from . import MessageStatusCode
from . import String
from . import VariableByteArray

from .constants import (AUTH_ALGO_RAKP_NONE, AUTH_ALGO_RAKP_HMAC_SHA1,
                        AUTH_ALGO_RAKP_HMAC_MD5, AUTH_ALGO_RAKP_HMAC_SHA256)


@register_ipmiv20_message_class
class OpenSessionReq(Message):
    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        Bitfield('maximum_privilege', 1,
                 Bitfield.Bit('privilege_level', 4, 0),
                 Bitfield.ReservedBit(4, 0),
                 ),
        Bitfield('reserved', 2,
                 Bitfield.ReservedBit(16, 0)
                 ),
        String('console_session_id', 4, b"\xA1\xA2\xA3\xA4"),  # ipmitool uses 0xA4A3A2A0
        # Authentication payload
        Bitfield('authentication', 8,
                 Bitfield.Bit('type', 8, 0),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, constants.AUTH_ALGO_RAKP_HMAC_SHA1),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
        # Integrity payload
        Bitfield('integrity', 8,
                 Bitfield.Bit('type', 8, 0x01),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, constants.INTEGRITY_ALGO_HMAC_SHA1_96),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
        # Confidentiality payload
        Bitfield('confidentiality', 8,
                 Bitfield.Bit('type', 8, 0x02),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, constants.CONFIDENTIALITY_ALGO_AES_CBC_128),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
    )


@register_ipmiv20_message_class
class OpenSessionRsp(Message):
    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        MessageStatusCode(),
        Bitfield('maximum_privilege', 1,
                 Bitfield.Bit('privilege_level', 4, 0),
                 Bitfield.ReservedBit(4, 0),
                 ),
        Bitfield('reserved', 1,
                 Bitfield.ReservedBit(8, 0)
                 ),
        String('console_session_id', 4, "\x00" * 4),
        String('managed_system_session_id', 4, "\x00" * 4),
        # Authentication payload
        Bitfield('authentication', 8,
                 Bitfield.Bit('type', 8, 0),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, 0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
        # Integrity payload
        Bitfield('integrity', 8,
                 Bitfield.Bit('type', 8, 0x01),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, 0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
        # Confidentiality payload
        Bitfield('confidentiality', 8,
                 Bitfield.Bit('type', 8, 0x02),
                 Bitfield.ReservedBit(16, 0),
                 Bitfield.Bit('length', 8, 0x08),
                 Bitfield.Bit('algorithm', 6, 0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.ReservedBit(24, 0)
                 ),
    )


@register_ipmiv20_message_class
class RAKPMessage1Req(Message):
    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        Bitfield('reserved1', 3,
                 Bitfield.ReservedBit(24, 0)
                 ),
        String('managed_system_session_id', 4, "\x00" * 4),
        String('console_random_number', 16, os.urandom(16)),
        Bitfield('role', 1,
                 Bitfield.Bit('privilege_level', 4, 0x4),  # ADMINISTRATOR level
                 Bitfield.Bit('lookup', 1, 1),  # Name-only lookup
                 Bitfield.ReservedBit(3, 0),
                 ),
        Bitfield('reserved2', 2,
                 Bitfield.ReservedBit(16, 0),
                 ),
        UnsignedInt('user_name_length', 1, 0),
        String('user_name', 16, '\x00' * 16),
    )


@register_ipmiv20_message_class
class RAKPMessage2Req(Message):
    authentication_algorithm = None

    def _length_ke_auth_code(self):
        return {AUTH_ALGO_RAKP_NONE:        0,
                AUTH_ALGO_RAKP_HMAC_SHA1:   20,
                AUTH_ALGO_RAKP_HMAC_MD5:    16,
                AUTH_ALGO_RAKP_HMAC_SHA256: 32
                }[self.authentication_algorithm]

    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        MessageStatusCode(),
        Bitfield('reserved1', 2,
                 Bitfield.ReservedBit(16, 0)
                 ),
        String('console_session_id', 4, "\x00" * 4),
        String('managed_system_random_number', 16, "\x00" * 16),
        String('managed_system_guid', 16, "\x00" * 16),
        VariableByteArray('ke_auth_code', _length_ke_auth_code),
    )


@register_ipmiv20_message_class
class RAKPMessage3Req(Message):
    authentication_algorithm = None

    def _length_ke_auth_code(self):
        return {AUTH_ALGO_RAKP_NONE:        0,
                AUTH_ALGO_RAKP_HMAC_SHA1:   20,
                AUTH_ALGO_RAKP_HMAC_MD5:    16,
                AUTH_ALGO_RAKP_HMAC_SHA256: 32
                }[self.authentication_algorithm]

    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        MessageStatusCode(),
        Bitfield('reserved1', 2,
                 Bitfield.ReservedBit(16, 0)
                 ),
        String('managed_system_session_id', 4, '\x00' * 4),
        VariableByteArray('ke_auth_code', _length_ke_auth_code)
    )


@register_ipmiv20_message_class
class RAKPMessage4Req(Message):
    authentication_algorithm = None

    def _length_integrity_check_value(self):
        return {AUTH_ALGO_RAKP_NONE:        0,
                AUTH_ALGO_RAKP_HMAC_SHA1:   12,
                AUTH_ALGO_RAKP_HMAC_MD5:    16,
                AUTH_ALGO_RAKP_HMAC_SHA256: 16
                }[self.authentication_algorithm]

    __fields__ = (
        UnsignedInt('message_tag', 1, 0),
        MessageStatusCode(),
        Bitfield('reserved1', 2,
                 Bitfield.ReservedBit(16, 0)
                 ),
        String('console_session_id', 4, "\x00" * 4),
        VariableByteArray('integrity_check_value', _length_integrity_check_value)
    )
