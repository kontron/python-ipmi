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

"""The firmware firewall and command discovery commands (IPMI v2.0 section 21).

The commands look up a network function and LUN on a channel (Eh is the
channel of the request). For the group extension network function (2Ch)
``group`` is the defining body code (one byte), for the OEM/group network
function (2Eh) the IANA enterprise number (three bytes, LSB first); it is
empty for the others. The command masks are 16 bytes for 128 commands, the
operation selects commands 00h-7Fh or 80h-FFh; byte 1 bit 0 is command 00h
or 80h. The sub-function masks are 32 bits, optionally followed by 32 bits
for the sub-functions 32-63 (IPMI v2.0 Appendix H).
"""

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import RemainingBytes
from .privileges import ADMINISTRATOR, USER


class CommandMaskOperation:
    COMMANDS_00_7F = 0
    COMMANDS_80_FF = 1


class LunSupport:
    """The support of a LUN, as returned for each of the four LUNs."""

    NOT_SUPPORTED = 0
    BASE_SPECIFICATION = 1
    RESTRICTED_BY_FIREWALL = 2


def channel() -> Bitfield:
    return Bitfield('channel', 1,
                    Bitfield.Bit('number', 4, default=0),
                    Bitfield.ReservedBit(4, 0))


def net_function(with_operation: bool) -> Bitfield:
    """Return the network function byte, the code of bit 0 is ignored."""
    if with_operation:
        return Bitfield('net_function', 1,
                        Bitfield.Bit('code', 6, default=0),
                        Bitfield.Bit('operation', 2, default=0))
    return Bitfield('net_function', 1,
                    Bitfield.Bit('code', 6, default=0),
                    Bitfield.ReservedBit(2, 0))


def lun_support() -> Bitfield:
    return Bitfield('lun_support', 1,
                    Bitfield.Bit('lun0', 2, default=0),
                    Bitfield.Bit('lun1', 2, default=0),
                    Bitfield.Bit('lun2', 2, default=0),
                    Bitfield.Bit('lun3', 2, default=0))


def command_mask_request() -> tuple:
    """Return the fields of the requests for a command mask."""
    return (
        channel(),
        net_function(with_operation=True),
        UnsignedInt('lun_number', 1, 0),
        RemainingBytes('group'),
    )


def sub_function_request() -> tuple:
    """Return the fields of the requests for the sub-functions of a command."""
    return (
        channel(),
        net_function(with_operation=False),
        UnsignedInt('lun_number', 1, 0),
        UnsignedInt('command', 1, 0),
        RemainingBytes('group'),
    )


@register_message_class
class GetNetFnSupportReq(Message):
    __cmdid__ = constants.CMDID_GET_NETFN_SUPPORT
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        channel(),
    )


@register_message_class
class GetNetFnSupportRsp(Message, LunSupport):
    """The support of each LUN and the network functions used per LUN.

    ``netfn_support`` has 4 bytes per LUN, one bit per network function
    pair: byte 1 bit 0 is NetFn 00h/01h of LUN 0, byte 16 bit 7 NetFn
    3Eh/3Fh of LUN 3.
    """

    __cmdid__ = constants.CMDID_GET_NETFN_SUPPORT
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        lun_support(),
        ByteArray('netfn_support', 16),
    )


@register_message_class
class GetCommandSupportReq(Message, CommandMaskOperation):
    __cmdid__ = constants.CMDID_GET_COMMAND_SUPPORT
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = command_mask_request()


@register_message_class
class GetCommandSupportRsp(Message):
    """The support mask; note that a set bit is a command NOT available."""

    __cmdid__ = constants.CMDID_GET_COMMAND_SUPPORT
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        ByteArray('support_mask', 16),
    )


@register_message_class
class GetCommandSubFunctionSupportReq(Message):
    __cmdid__ = constants.CMDID_GET_COMMAND_SUBFUNCTION_SUPPORT
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = sub_function_request()


@register_message_class
class GetCommandSubFunctionSupportRsp(Message):
    """The specification of the command and its unavailable sub-functions.

    The type is 0 for IPMI, 1 for IPMB and 2 for ICMB, the version and
    revision are BCD (20h, 10h for v2.0 rev. 1.0). A set bit of the support
    mask is a mandatory sub-function or option NOT available.
    """

    IPMI = 0
    IPMB = 1
    ICMB = 2

    __cmdid__ = constants.CMDID_GET_COMMAND_SUBFUNCTION_SUPPORT
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('specification', 1,
                 Bitfield.Bit('errata', 4, default=0),
                 Bitfield.Bit('type', 4, default=0)),
        UnsignedInt('version', 1),
        UnsignedInt('revision', 1),
        Optional(UnsignedInt('support_mask', 4)),
    )


@register_message_class
class GetConfigurableCommandsReq(Message, CommandMaskOperation):
    __cmdid__ = constants.CMDID_GET_CONFIGURATION_COMMANDS
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = command_mask_request()


@register_message_class
class GetConfigurableCommandsRsp(Message):
    """A set bit is a command that can be enabled and disabled."""

    __cmdid__ = constants.CMDID_GET_CONFIGURATION_COMMANDS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        ByteArray('configurable_mask', 16),
    )


@register_message_class
class GetConfigurableCommandSubFunctionsReq(Message):
    __cmdid__ = constants.CMDID_GET_CONFIGURATION_SUBFUNCTION_COMMANDS
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = sub_function_request()


@register_message_class
class GetConfigurableCommandSubFunctionsRsp(Message):
    """A set bit is a sub-function that can be enabled and disabled."""

    __cmdid__ = constants.CMDID_GET_CONFIGURATION_SUBFUNCTION_COMMANDS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('configurable_mask', 4),
        Optional(UnsignedInt('additional_configurable_mask', 4)),
    )


@register_message_class
class SetCommandEnablesReq(Message, CommandMaskOperation):
    """Set Command Enables; a set bit enables a command.

    The settings are non-volatile. The mask replaces all 128 settings, so it
    is read with Get Command Enables and modified first.
    """

    __cmdid__ = constants.CMDID_SET_COMMAND_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        channel(),
        net_function(with_operation=True),
        UnsignedInt('lun_number', 1, 0),
        ByteArray('enables', 16, default=bytes(16)),
        RemainingBytes('group'),
    )


@register_message_class
class SetCommandEnablesRsp(Message):
    __cmdid__ = constants.CMDID_SET_COMMAND_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetCommandEnablesReq(Message, CommandMaskOperation):
    __cmdid__ = constants.CMDID_GET_COMMAND_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = command_mask_request()


@register_message_class
class GetCommandEnablesRsp(Message):
    """A set bit is an enabled command, a clear one disabled or unsupported."""

    __cmdid__ = constants.CMDID_GET_COMMAND_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        ByteArray('enables', 16),
    )


@register_message_class
class SetCommandSubFunctionEnablesReq(Message):
    """Set Configurable Command Sub-function Enables.

    ``data`` is the group (for NetFn 2Ch or 2Eh), followed by the enables of
    the sub-functions 0-31 and optionally 32-63, LSB first; a set bit enables
    the sub-function. The settings are non-volatile.
    """

    __cmdid__ = constants.CMDID_SET_COMMAND_SUBFUNCTION_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        channel(),
        net_function(with_operation=False),
        UnsignedInt('lun_number', 1, 0),
        UnsignedInt('command', 1, 0),
        RemainingBytes('data'),
    )


@register_message_class
class SetCommandSubFunctionEnablesRsp(Message):
    __cmdid__ = constants.CMDID_SET_COMMAND_SUBFUNCTION_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetCommandSubFunctionEnablesReq(Message):
    __cmdid__ = constants.CMDID_GET_COMMAND_SUBFUNCTION_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = sub_function_request()


@register_message_class
class GetCommandSubFunctionEnablesRsp(Message):
    """A set bit is an enabled sub-function."""

    __cmdid__ = constants.CMDID_GET_COMMAND_SUBFUNCTION_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('enables', 4),
        Optional(UnsignedInt('additional_enables', 4)),
    )


@register_message_class
class GetOemNetFnIanaSupportReq(Message):
    """Get OEM NetFn IANA Support, for NetFn 2Ch or 2Eh.

    The list index starts at 0 and is incremented until the response is
    the last one.
    """

    __cmdid__ = constants.CMDID_GET_OEM_NETFN_IANA_SUPPORT
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        channel(),
        net_function(with_operation=False),
        Bitfield('list', 1,
                 Bitfield.Bit('index', 6, default=0),
                 Bitfield.ReservedBit(2, 0)),
    )


@register_message_class
class GetOemNetFnIanaSupportRsp(Message, LunSupport):
    __cmdid__ = constants.CMDID_GET_OEM_NETFN_IANA_SUPPORT
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('list', 1,
                 Bitfield.ReservedBit(7, 0),
                 Bitfield.Bit('last', 1, default=0)),
        lun_support(),
        RemainingBytes('group'),
    )
