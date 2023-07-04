# Copyright (c) 2021  Kontron Europe GmbH
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

from __future__ import absolute_import

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import GroupExtensionIdentifier


GROUP_EXTENSION_VSO = 0x03


VITA_FRU_CONTROL_COLD_RESET = 0x00
VITA_FRU_CONTROL_WARM_RESET = 0x01
VITA_FRU_CONTROL_GRACEFUL_REBOOT = 0x02
VITA_FRU_CONTROL_DIAGNOSTIC_INTERRUPT = 0x03


class VitaMessage(Message):
    __group_extension__ = GROUP_EXTENSION_VSO


@register_message_class
class VitaGetVsoCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_VSO_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetVsoCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_VSO_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('ipmc_identifier', 1,
                 Bitfield.Bit('tier_functionality', 2, default=0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.Bit('layer_functionality', 2, default=0),
                 Bitfield.ReservedBit(2, 0)),
        Bitfield('ipmb_capabilities', 1,
                 Bitfield.Bit('number_ipmbs', 2, default=0),
                 Bitfield.ReservedBit(2, 0),
                 Bitfield.Bit('max_frequency', 2, default=0),
                 Bitfield.ReservedBit(2, 0)),
        Bitfield('vso_standard', 1,
                 Bitfield.Bit('standard', 2, default=0),
                 Bitfield.ReservedBit(6, 0)),
        UnsignedInt('specification_revision', 1),
        UnsignedInt('max_fru_id', 1),
        UnsignedInt('ipmc_fru_device_id', 1)
    )


@register_message_class
class VitaGetChassisAddressTableInfoReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_ADDRESS_TABLE_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetChassisAddressTableInfoRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_ADDRESS_TABLE_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFruAddressInfoReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFruAddressInfoRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('hardware_address', 1),
        UnsignedInt('ipmb_0_address', 1),
        UnsignedInt('reserved_5', 1),
        UnsignedInt('fru_id', 1),
        UnsignedInt('site_id', 1),
        UnsignedInt('site_type', 1),
        Optional(
            UnsignedInt('reserved_9', 1),
        ),
        Optional(
            UnsignedInt('address_on_channel_7', 1),
        ),
    )


@register_message_class
class VitaGetChassisIdentifierReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_IDENTIFIER
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetChassisIdentifierRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_IDENTIFIER
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaSetChassisIdentifierReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_CHASSIS_IDENTIFIER
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaSetChassisIdentifierRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_CHASSIS_IDENTIFIER
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaFruControlReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('option', 1),
    )


@register_message_class
class VitaFruControlRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFruLedPropertiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_LED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFruLedPropertiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_LED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('reserved', 1),
        UnsignedInt('led_count', 1),
    )


@register_message_class
class VitaGetFruLedCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_LED_COLOR_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('led_id', 1),
    )


@register_message_class
class VitaGetFruLedCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_LED_COLOR_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('reserved', 1),
        Bitfield('color_capabilities', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('blue', 1, default=0),
                 Bitfield.Bit('red', 1, default=0),
                 Bitfield.Bit('green', 1, default=0),
                 Bitfield.Bit('amber', 1, default=0),
                 Bitfield.Bit('orange', 1, default=0),
                 Bitfield.Bit('white', 1, default=0),
                 Bitfield.ReservedBit(1, 0)),
        Bitfield('default_color_local_control', 1,
                 Bitfield.Bit('value', 4, default=0),
                 Bitfield.ReservedBit(4, 0)),
        Bitfield('default_color_override_control', 1,
                 Bitfield.Bit('value', 4, default=0),
                 Bitfield.ReservedBit(4, 0)),
        Optional(
            UnsignedInt('flags', 1),
        ),
    )


@register_message_class
class VitaSetFruLedStateReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('led_id', 1),
        UnsignedInt('function', 1),
        UnsignedInt('on_duration', 1),
        UnsignedInt('color', 1),
    )


@register_message_class
class VitaSetFruLedStateRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFruLedStateReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('led_id', 1),
    )


@register_message_class
class VitaGetFruLedStateRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('state', 1,
                 Bitfield.Bit('ipmc_control', 1, default=0),
                 Bitfield.Bit('override', 1, default=0),
                 Bitfield.Bit('lamp_test', 1, default=0),
                 Bitfield.Bit('hardware_restrict', 1, default=0),
                 Bitfield.ReservedBit(4, 0)),
        UnsignedInt('local_control_function', 1),
        UnsignedInt('local_control_on_duration', 1),
        UnsignedInt('local_control_color', 1),
        Optional(
            UnsignedInt('override_state', 1),
        ),
        Optional(
            UnsignedInt('override_on_duration', 1),
        ),
        Optional(
            UnsignedInt('override_color', 1),
        ),
        Optional(
            UnsignedInt('lamp_test_duration', 1),
        ),
    )


@register_message_class
class VitaSetIpmbStateReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_IPMB_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('ipmb_a', 1,
                 Bitfield.Bit('state', 1, default=0),
                 Bitfield.Bit('identification', 7, default=0)),
        Bitfield('ipmb_b', 1,
                 Bitfield.Bit('state', 1, default=0),
                 Bitfield.Bit('identification', 7, default=0)),
        Bitfield('speed', 1,
                 Bitfield.Bit('ipmb_a', 2, default=0),
                 Bitfield.Bit('ipmb_b', 2, default=0),
                 Bitfield.ReservedBit(4, 0)),
    )


@register_message_class
class VitaSetIpmbStateRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_IPMB_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaSetFruStatePolicyReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_STATE_POLICY_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        Bitfield('activation_policy_mask', 1,
                 Bitfield.Bit('activation_lock', 1, default=0),
                 Bitfield.Bit('deactivation_lock', 1, default=0),
                 Bitfield.Bit('commanded_deactivation_ignored', 1, default=0),
                 Bitfield.Bit('default_activation_locked', 1, default=0),
                 Bitfield.ReservedBit(4, 0),),
        Bitfield('activation_policy_set', 1,
                 Bitfield.Bit('activation_lock', 1, default=0),
                 Bitfield.Bit('deactivation_lock', 1, default=0),
                 Bitfield.Bit('commanded_deactivation_ignored', 1, default=0),
                 Bitfield.Bit('default_activation_locked', 1, default=0),
                 Bitfield.ReservedBit(4, 0),)
    )


@register_message_class
class VitaSetFruStatePolicyRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_STATE_POLICY_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFruStatePolicyReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_STATE_POLICY_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFruStatePolicyRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_STATE_POLICY_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('activation_policies', 1,
                 Bitfield.Bit('activation_lock', 1, default=0),
                 Bitfield.Bit('deactivation_lock', 1, default=0),
                 Bitfield.Bit('commanded_deactivation_ignored', 1, default=0),
                 Bitfield.Bit('default_activation_locked', 1, default=0),
                 Bitfield.ReservedBit(4, 0),)
    )


@register_message_class
class VitaSetFruActivationReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_ACTIVATION
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('control', 1),
    )


@register_message_class
class VitaSetFruActivationRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_ACTIVATION
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetDeviceLocatorRecordReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_DEVICE_LOCATOR_RECORD_ID
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetDeviceLocatorRecordRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_DEVICE_LOCATOR_RECORD_ID
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('record_id', 2),
    )


@register_message_class
class VitaFruControlCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaFruControlCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('capabilities', 1,
                 Bitfield.Bit('cold_reset', 1, default=0),
                 Bitfield.Bit('warm_reset', 1, default=0),
                 Bitfield.Bit('graceful_reboot', 1, default=0),
                 Bitfield.Bit('diagnostic_interrupt', 1, default=0),
                 Bitfield.Bit('controlling_payload_power', 1, default=0),
                 Bitfield.ReservedBit(3, 0),)
    )


@register_message_class
class VitaGetMandatorySensorNumbersReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_MANDATORY_SENSOR_NUMBERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetMandatorySensorNumbersRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_MANDATORY_SENSOR_NUMBERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_state_sensor', 1),
        UnsignedInt('fru_health_sensor', 1),
        UnsignedInt('fru_voltage_sensor', 1),
        UnsignedInt('fru_temperature_sensor', 1),
        UnsignedInt('test_result_sensor', 1),
        UnsignedInt('test_status_sensor', 1),
        UnsignedInt('reserved_9', 1),
        UnsignedInt('payload_mode_sensor', 1),
    )


@register_message_class
class VitaGetFruHashReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_HASH
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFruHashRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_HASH
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_hash', 4),
    )


@register_message_class
class VitaGetPayloadModeCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_PAYLOAD_MODE_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetPayloadModeCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_PAYLOAD_MODE_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('supported_modes_lsb', 1),
        Optional(
             UnsignedInt('supported_modes_msb', 1),
        ),
    )


@register_message_class
class VitaSetPayloadModeReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_PAYLOAD_MODE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('mode', 1),
    )


@register_message_class
class VitaSetPayloadModeRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_PAYLOAD_MODE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Optional(
            UnsignedInt('oem_response_3', 1),
        ),
        Optional(
            UnsignedInt('oem_response_4', 1),
        ),
        Optional(
            UnsignedInt('oem_response_5', 1),
        ),
        Optional(
            UnsignedInt('oem_response_6', 1),
        ),
        Optional(
            UnsignedInt('oem_response_7', 1),
        ),
        Optional(
            UnsignedInt('oem_response_8', 1),
        ),
        Optional(
            UnsignedInt('oem_response_9', 1),
        ),
        Optional(
            UnsignedInt('oem_response_10', 1),
        ),
    )
