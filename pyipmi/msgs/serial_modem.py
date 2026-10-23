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

"""The serial/modem commands (IPMI v2.0 section 25)."""

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import RemainingBytes
from .privileges import ADMINISTRATOR, NONE, OPERATOR


@register_message_class
class SetSerialModemConfigurationReq(Message):
    __cmdid__ = constants.CMDID_SET_SERIAL_MODEM_CONFIGURATION
    __netfn__ = constants.NETFN_TRANSPORT
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('command', 1,
                 Bitfield.Bit('channel_number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        UnsignedInt('parameter_selector', 1),
        RemainingBytes('data'),
    )


@register_message_class
class SetSerialModemConfigurationRsp(Message):
    __cmdid__ = constants.CMDID_SET_SERIAL_MODEM_CONFIGURATION
    __netfn__ = constants.NETFN_TRANSPORT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetSerialModemConfigurationReq(Message):
    __cmdid__ = constants.CMDID_GET_SERIAL_MODEM_CONFIGURATION
    __netfn__ = constants.NETFN_TRANSPORT
    __privilege__ = OPERATOR
    __fields__ = (
        Bitfield('command', 1,
                 Bitfield.Bit('channel_number', 4),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('get_parameter_revision_only', 1, 0),),
        UnsignedInt('parameter_selector', 1, 0),
        UnsignedInt('set_selector', 1, 0),
        UnsignedInt('block_selector', 1, 0),
    )


@register_message_class
class GetSerialModemConfigurationRsp(Message):
    __cmdid__ = constants.CMDID_GET_SERIAL_MODEM_CONFIGURATION
    __netfn__ = constants.NETFN_TRANSPORT | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('parameter_revision', 1, 0),
        RemainingBytes('data'),
    )


@register_message_class
class SerialModemConnectionActiveReq(Message):
    """Sent by the BMC to the remote console, also before a session.

    The IPMI version is in hexadecimal with the LSN first, 51h is IPMI 1.5.
    """

    NO_SESSION_ACTIVE = 0
    SESSION_ACTIVE = 1
    SWITCHING_MUX_TO_SYSTEM = 2

    __cmdid__ = constants.CMDID_SERIAL_MODEM_CONNECTION_ACTIVE
    __netfn__ = constants.NETFN_TRANSPORT
    __privilege__ = NONE
    __fields__ = (
        Bitfield('session_state', 1,
                 Bitfield.Bit('state', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        UnsignedInt('ipmi_version', 1, 0x51),
    )


@register_message_class
class SerialModemConnectionActiveRsp(Message):
    __cmdid__ = constants.CMDID_SERIAL_MODEM_CONNECTION_ACTIVE
    __netfn__ = constants.NETFN_TRANSPORT | 1
    __fields__ = (
        CompletionCode(),
    )
