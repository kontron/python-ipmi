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

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Bitfield
from . import String
from . import CompletionCode
from . import RemainingBytes
from . import Conditional
from . import Optional
from .privileges import ADMINISTRATOR, CALLBACK, NONE, OPERATOR, SYSTEM_INTERFACE, USER


@register_message_class
class SetBmcGlobalEnablesReq(Message):
    __cmdid__ = constants.CMDID_SET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE
    __fields__ = (
        Bitfield('enables', 1,
                 Bitfield.Bit('receive_message_queue_interrupt', 1, 0),
                 Bitfield.Bit('event_message_buffer_full_interrupt', 1, 0),
                 Bitfield.Bit('event_message_buffer', 1, 0),
                 Bitfield.Bit('system_event_logging', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('oem_0', 1, 0),
                 Bitfield.Bit('oem_1', 1, 0),
                 Bitfield.Bit('oem_2', 1, 0),),
    )


@register_message_class
class SetBmcGlobalEnablesRsp(Message):
    __cmdid__ = constants.CMDID_SET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetBmcGlobalEnablesReq(Message):
    __cmdid__ = constants.CMDID_GET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER


@register_message_class
class GetBmcGlobalEnablesRsp(Message):
    __cmdid__ = constants.CMDID_GET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('enables', 1,
                 Bitfield.Bit('receive_message_queue_interrupt', 1, 0),
                 Bitfield.Bit('event_message_buffer_full_interrupt', 1, 0),
                 Bitfield.Bit('event_message_buffer', 1, 0),
                 Bitfield.Bit('system_event_logging', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('oem_0', 1, 0),
                 Bitfield.Bit('oem_1', 1, 0),
                 Bitfield.Bit('oem_2', 1, 0),),
    )


@register_message_class
class ClearMessageFlagsReq(Message):
    __cmdid__ = constants.CMDID_CLEAR_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE
    __fields__ = (
        Bitfield('clear', 1,
                 Bitfield.Bit('receive_message_queue', 1, 0),
                 Bitfield.Bit('event_message_buffer', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('watchdog_pretimeout_interrupt_flag', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('oem_0', 1, 0),
                 Bitfield.Bit('oem_1', 1, 0),
                 Bitfield.Bit('oem_2', 1, 0),),
    )


@register_message_class
class ClearMessageFlagsRsp(Message):
    __cmdid__ = constants.CMDID_CLEAR_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetMessageFlagsReq(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE


@register_message_class
class GetMessageFlagsRsp(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('flag', 1,
                 Bitfield.Bit('receive_message_available', 1, 0),
                 Bitfield.Bit('event_message_buffer_full', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('watchdog_pretimeout_interrupt_occurred', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('oem_0', 1, 0),
                 Bitfield.Bit('oem_1', 1, 0),
                 Bitfield.Bit('oem_2', 1, 0),),
    )


@register_message_class
class EnableMessageChannelReceiveReq(Message):
    __cmdid__ = constants.CMDID_ENABLE_MESSAGE_CHANNEL_RECEIVE
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE
    __fields__ = (
        Bitfield('channel', 2,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),
                 Bitfield.Bit('state', 2, 0),
                 Bitfield.ReservedBit(6, 0),),
    )


@register_message_class
class EnableMessageChannelReceiveRsp(Message):
    __cmdid__ = constants.CMDID_ENABLE_MESSAGE_CHANNEL_RECEIVE
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('channel', 2,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),
                 Bitfield.Bit('state', 1, 0),
                 Bitfield.ReservedBit(7, 0),),
    )


@register_message_class
class GetMessageReq(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE


@register_message_class
class GetMessageRsp(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.Bit('privilege_level', 4, 0),),
        RemainingBytes('data'),
    )


@register_message_class
class SendMessageReq(Message):
    __cmdid__ = constants.CMDID_SEND_MESSAGE
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.Bit('authenticated', 1, 0),
                 Bitfield.Bit('encrypted', 1, 0),
                 Bitfield.Bit('tracking', 2, 0),),
        RemainingBytes('data'),
    )


@register_message_class
class SendMessageRsp(Message):
    __cmdid__ = constants.CMDID_SEND_MESSAGE
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        RemainingBytes('data'),
    )


@register_message_class
class ReadEventMessageBufferReq(Message):
    __cmdid__ = constants.CMDID_READ_EVENT_MESSAGE_BUFFER
    __netfn__ = constants.NETFN_APP
    __privilege__ = SYSTEM_INTERFACE


@register_message_class
class ReadEventMessageBufferRsp(Message):
    __cmdid__ = constants.CMDID_READ_EVENT_MESSAGE_BUFFER
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        RemainingBytes('event_data'),
    )


@register_message_class
class GetBtInterfaceCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_GET_BT_INTERFACE_CAPABILITIES
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER


@register_message_class
class GetBtInterfaceCapabilitiesRsp(Message):
    """The buffer sizes are those of the length byte, the time in seconds."""

    __cmdid__ = constants.CMDID_GET_BT_INTERFACE_CAPABILITIES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('outstanding_requests', 1),
        UnsignedInt('input_buffer_size', 1),
        UnsignedInt('output_buffer_size', 1),
        UnsignedInt('request_to_response_time', 1),
        UnsignedInt('recommended_retries', 1),
    )


@register_message_class
class GetSystemGuidReq(Message):
    """Get System GUID, also before a session is established."""

    __cmdid__ = constants.CMDID_GET_SYSTEM_GUID
    __netfn__ = constants.NETFN_APP
    __privilege__ = NONE


@register_message_class
class GetSystemGuidRsp(Message):
    """The GUID in the format of IPMI v2.0 Table 20-10, like Get Device GUID."""

    __cmdid__ = constants.CMDID_GET_SYSTEM_GUID
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        ByteArray('system_guid', 16),
    )


@register_message_class
class MasterWriteReadReq(Message):
    __cmdid__ = constants.CMDID_MASTER_WRITE_READ
    __netfn__ = constants.NETFN_APP
    __privilege__ = OPERATOR
    __fields__ = (
        Bitfield('bus_id', 2,
                 Bitfield.Bit('type', 1, 0),
                 Bitfield.Bit('id', 3, 0),
                 Bitfield.Bit('channel', 4, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('slave_address', 7, 0),),
        UnsignedInt('read_count', 1),
        RemainingBytes('data'),
    )


@register_message_class
class MasterWriteReadRsp(Message):
    __cmdid__ = constants.CMDID_MASTER_WRITE_READ
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        RemainingBytes('data'),
    )


@register_message_class
class GetChannelAuthenticationCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_AUTHENTICATION_CAPABILITIES
    __netfn__ = constants.NETFN_APP
    __privilege__ = NONE
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('type', 1, 0),),
        Bitfield('privilege_level', 1,
                 Bitfield.Bit('requested', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class GetChannelAuthenticationCapabilitiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_AUTHENTICATION_CAPABILITIES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('channel_number', 1),
        Bitfield('support', 1,
                 Bitfield.Bit('none', 1, 0),
                 Bitfield.Bit('md2', 1, 0),
                 Bitfield.Bit('md5', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('straight', 1, 0),
                 Bitfield.Bit('oem_proprietary', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('ipmi_2_0', 1, 0),),
        Bitfield('status', 1,
                 Bitfield.Bit('anonymous_login_enabled', 1, 0),
                 Bitfield.Bit('anonymous_login_null_user', 1, 0),
                 Bitfield.Bit('anonymous_login_non_null', 1, 0),
                 Bitfield.Bit('user_level', 1, 0),
                 Bitfield.Bit('per_message', 1, 0),
                 Bitfield.Bit('kg', 1, 0),
                 Bitfield.ReservedBit(2, 0),),
        Bitfield('extended_capabilities', 1,
                 Bitfield.Bit('1_5', 1, 0),
                 Bitfield.Bit('2_0', 1, 0),
                 Bitfield.ReservedBit(6, 0),),
        UnsignedInt('oem_id', 3),
        UnsignedInt('oem_auxiliary_data', 1),
    )


@register_message_class
class GetChannelCipherSuitesReq(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_CIPHER_SUITES
    __netfn__ = constants.NETFN_APP
    __privilege__ = NONE
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        Bitfield('payload', 1,
                 Bitfield.Bit('type', 6, 0),
                 Bitfield.ReservedBit(2, 0),),
        Bitfield('list', 1,
                 Bitfield.Bit('index', 6, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('by_cipher_suite', 1, 0),),
    )


@register_message_class
class GetChannelCipherSuitesRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_CIPHER_SUITES
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('channel_number', 1),
        # up to 16 bytes of the cipher suite records (IPMI v2.0, table
        # 22-19) of the list index
        RemainingBytes('data'),
    )


@register_message_class
class SetChannelAccessReq(Message):
    __cmdid__ = constants.CMDID_SET_CHANNEL_ACCESS
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        # set: 0 do not set, 1 non-volatile, 2 volatile (active) settings
        Bitfield('access', 1,
                 Bitfield.Bit('mode', 3, 0),
                 Bitfield.Bit('user_level_auth_disable', 1, 0),
                 Bitfield.Bit('per_message_auth_disable', 1, 0),
                 Bitfield.Bit('alerting_disable', 1, 0),
                 Bitfield.Bit('set', 2, 0),),
        Bitfield('privilege', 1,
                 Bitfield.Bit('limit', 4, 0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.Bit('set', 2, 0),),
    )


@register_message_class
class SetChannelAccessRsp(Message):
    __cmdid__ = constants.CMDID_SET_CHANNEL_ACCESS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetChannelAccessReq(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_ACCESS
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        # 1 non-volatile, 2 volatile (active) settings
        Bitfield('access', 1,
                 Bitfield.ReservedBit(6, 0),
                 Bitfield.Bit('get', 2, 2),),
    )


@register_message_class
class GetChannelAccessRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_ACCESS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('access', 1,
                 Bitfield.Bit('mode', 3, 0),
                 Bitfield.Bit('user_level_auth_disable', 1, 0),
                 Bitfield.Bit('per_message_auth_disable', 1, 0),
                 Bitfield.Bit('alerting_disable', 1, 0),
                 Bitfield.ReservedBit(2, 0),),
        Bitfield('privilege', 1,
                 Bitfield.Bit('limit', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class GetChannelInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_INFO
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class GetChannelInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_INFO
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('channel', 1,
                 Bitfield.Bit('number', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        Bitfield('medium', 1,
                 Bitfield.Bit('type', 7, 0),
                 Bitfield.ReservedBit(1, 0),),
        Bitfield('protocol', 1,
                 Bitfield.Bit('type', 5, 0),
                 Bitfield.ReservedBit(3, 0),),
        Bitfield('session', 1,
                 Bitfield.Bit('active_count', 6, 0),
                 Bitfield.Bit('support', 2, 0),),
        UnsignedInt('vendor_id', 3, 0),
        RemainingBytes('auxiliary_info'),
    )


@register_message_class
class GetSessionChallengeReq(Message):
    __cmdid__ = constants.CMDID_GET_SESSION_CHALLENGE
    __netfn__ = constants.NETFN_APP
    __privilege__ = NONE
    __fields__ = (
        Bitfield('authentication', 1,
                 Bitfield.Bit('type', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        String('user_name', 16, '\x00' * 16),
    )


@register_message_class
class GetSessionChallengeRsp(Message):
    __cmdid__ = constants.CMDID_GET_SESSION_CHALLENGE
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('temporary_session_id', 4),
        String('challenge_string', 16, '\x00' * 16),
    )


@register_message_class
class ActivateSessionReq(Message):
    __cmdid__ = constants.CMDID_ACTIVATE_SESSION
    __netfn__ = constants.NETFN_APP
    __privilege__ = NONE
    __fields__ = (
        Bitfield('authentication', 1,
                 Bitfield.Bit('type', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        Bitfield('privilege_level', 1,
                 Bitfield.Bit('maximum_requested', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        String('challenge_string', 16),
        UnsignedInt('initial_outbound_sequence_number', 4),
    )


@register_message_class
class ActivateSessionRsp(Message):
    __cmdid__ = constants.CMDID_ACTIVATE_SESSION
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('authentication', 1,
                 Bitfield.Bit('type', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
        UnsignedInt('session_id', 4),
        UnsignedInt('initial_inbound_sequence_number', 4),
        Bitfield('privilege_level', 1,
                 Bitfield.Bit('maximum_allowed', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class SetSessionPrivilegeLevelReq(Message):
    __cmdid__ = constants.CMDID_SET_SESSION_PRIVILEGE_LEVEL
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        Bitfield('privilege_level', 1,
                 Bitfield.Bit('requested', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class SetSessionPrivilegeLevelRsp(Message):
    __cmdid__ = constants.CMDID_SET_SESSION_PRIVILEGE_LEVEL
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('privilege_level', 1,
                 Bitfield.Bit('new', 4, 0),
                 Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class CloseSessionReq(Message):
    __cmdid__ = constants.CMDID_CLOSE_SESSION
    __netfn__ = constants.NETFN_APP
    __privilege__ = CALLBACK
    __fields__ = (
        UnsignedInt('session_id', 4),
    )


@register_message_class
class CloseSessionRsp(Message):
    __cmdid__ = constants.CMDID_CLOSE_SESSION
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetSessionInfoReq(Message):
    """Get Session Info: a session by index, handle or ID.

    The session index is 0 for the session of the request, 1 to 63 for
    the active sessions, ``SESSION_HANDLE`` with the session handle or
    ``SESSION_ID`` with the session ID.
    """

    CURRENT_SESSION = 0x00
    SESSION_HANDLE = 0xfe
    SESSION_ID = 0xff

    __cmdid__ = constants.CMDID_GET_SESSION_INFO
    __netfn__ = constants.NETFN_APP
    __privilege__ = USER
    __fields__ = (
        UnsignedInt('session_index', 1, 0),
        Conditional(lambda m: m.session_index == GetSessionInfoReq.SESSION_HANDLE,
                    UnsignedInt('session_handle', 1, 0)),
        Conditional(lambda m: m.session_index == GetSessionInfoReq.SESSION_ID,
                    UnsignedInt('session_id', 4, 0)),
    )


@register_message_class
class GetSessionInfoRsp(Message):
    """The session and the numbers of possible and active sessions.

    An unused session index has only the handle 0 and the numbers. The
    channel data of a LAN channel (IPMI v1.5) is the IP address, the MAC
    address and the port of the remote console.
    """

    __cmdid__ = constants.CMDID_GET_SESSION_INFO
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('session_handle', 1),
        Bitfield('possible_sessions', 1,
                 Bitfield.Bit('count', 6, 0),
                 Bitfield.ReservedBit(2, 0),),
        Bitfield('active_sessions', 1,
                 Bitfield.Bit('count', 6, 0),
                 Bitfield.ReservedBit(2, 0),),
        # without them for an unused session index: the user ID in bits
        # 5:0, the operating privilege level in bits 3:0, the channel
        # number in bits 3:0 (the protocol auxiliary data in bits 7:4)
        Optional(UnsignedInt('user_id', 1)),
        Optional(UnsignedInt('privilege_level', 1)),
        Optional(UnsignedInt('channel', 1)),
        RemainingBytes('channel_data'),
    )


@register_message_class
class SetUserNameReq(Message):
    __cmdid__ = constants.CMDID_SET_USER_NAME
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('userid', 1,
                 Bitfield.Bit('userid', 6, 0),
                 Bitfield.ReservedBit(2, 0),),
        String('user_name', 16),
    )


@register_message_class
class SetUserNameRsp(Message):
    __cmdid__ = constants.CMDID_SET_USER_NAME
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetUserNameReq(Message):
    __cmdid__ = constants.CMDID_GET_USER_NAME
    __netfn__ = constants.NETFN_APP
    __privilege__ = OPERATOR
    __fields__ = (
        Bitfield('userid', 1,
                 Bitfield.Bit('userid', 6, 0),
                 Bitfield.ReservedBit(2, 0),),
    )


@register_message_class
class GetUserNameRsp(Message):
    __cmdid__ = constants.CMDID_GET_USER_NAME
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        String('user_name', 16, '\x00' * 16),
    )


@register_message_class
class SetUserPasswordReq(Message):
    __cmdid__ = constants.CMDID_SET_USER_PASSWORD
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('userid', 1,
                 Bitfield.Bit('userid', 6, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('password_size', 1, 0)),
        Bitfield('operation', 1,
                 Bitfield.Bit('operation', 2, 0),
                 Bitfield.ReservedBit(6, 0)),
        String('password', 16, '\x00' * 16)
    )


@register_message_class
class SetUserPasswordRsp(Message):
    __cmdid__ = constants.CMDID_SET_USER_PASSWORD
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetUserAccessReq(Message):
    __cmdid__ = constants.CMDID_GET_USER_ACCESS
    __netfn__ = constants.NETFN_APP
    __privilege__ = OPERATOR
    __fields__ = (
        Bitfield('channel', 1,
                 Bitfield.Bit('channel_number', 4, 0),
                 Bitfield.ReservedBit(4, 0)),
        Bitfield('userid', 1,
                 Bitfield.Bit('userid', 6, 0),
                 Bitfield.ReservedBit(2, 0))
    )


@register_message_class
class GetUserAccessRsp(Message):
    __cmdid__ = constants.CMDID_GET_USER_ACCESS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('max_user', 1,
                 Bitfield.Bit('max_user', 6, 0),
                 Bitfield.ReservedBit(2, 0)),
        Bitfield('enabled_user', 1,
                 Bitfield.Bit('count', 6, 0),
                 Bitfield.Bit('status', 2, 0)),
        Bitfield('fixed_names', 1,
                 Bitfield.Bit('count', 6, 0),
                 Bitfield.ReservedBit(2, 0)),
        Bitfield('channel_access', 1,
                 Bitfield.Bit('privilege', 4, 0),
                 Bitfield.Bit('ipmi_msg', 1, 0),
                 Bitfield.Bit('link_auth', 1, 0),
                 Bitfield.Bit('callback', 1, 0),
                 Bitfield.ReservedBit(1, 0))
    )


@register_message_class
class SetUserAccessReq(Message):
    __cmdid__ = constants.CMDID_SET_USER_ACCESS
    __netfn__ = constants.NETFN_APP
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('channel_access', 1,
                 Bitfield.Bit('channel_number', 4, 0),
                 Bitfield.Bit('ipmi_msg', 1, 0),
                 Bitfield.Bit('link_auth', 1, 0),
                 Bitfield.Bit('callback', 1, 0),
                 Bitfield.Bit('enable_change', 1, 0)),
        Bitfield('userid', 1,
                 Bitfield.Bit('userid', 6, 0),
                 Bitfield.ReservedBit(2, 0)),
        Bitfield('privilege', 1,
                 Bitfield.Bit('privilege_level', 4, 0x0f),
                 Bitfield.ReservedBit(4, 0)),
        Bitfield('session_limit', 1,
                 Bitfield.Bit('simultaneous_session_limit', 4, 0),
                 Bitfield.ReservedBit(4, 0))
    )


@register_message_class
class SetUserAccessRsp(Message):
    __cmdid__ = constants.CMDID_SET_USER_ACCESS
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )
