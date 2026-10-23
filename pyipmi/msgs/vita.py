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

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import RemainingBytes
from . import Timestamp
from . import GroupExtensionIdentifier
from .privileges import ADMINISTRATOR, OPERATOR, USER


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
    __privilege__ = USER
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
    """Get Chassis Address Table Info (VITA 46.11 table 10.1.3.2-1).

    All fields after the VSO identifier are optional: the FRU device ID
    (needed with an address key), the address key type (``ADDRESS_KEY_*``),
    the address key and, for a physical address, the site type.
    """

    ADDRESS_KEY_HARDWARE_ADDRESS = 0x00
    ADDRESS_KEY_IPMB_ADDRESS = 0x01
    ADDRESS_KEY_PHYSICAL_ADDRESS = 0x03

    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_ADDRESS_TABLE_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Optional(UnsignedInt('fru_id', 1)),
        Optional(UnsignedInt('address_key_type', 1)),
        Optional(UnsignedInt('address_key', 1)),
        Optional(UnsignedInt('site_type', 1)),
    )


@register_message_class
class VitaGetChassisAddressTableInfoRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_ADDRESS_TABLE_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('hardware_address', 1),
        UnsignedInt('ipmb_0_address', 1),
        UnsignedInt('reserved', 1, 0xff),
        UnsignedInt('fru_id', 1),
        UnsignedInt('site_id', 1),
        UnsignedInt('site_type', 1),
    )


@register_message_class
class VitaFruInventoryDeviceLockControlReq(VitaMessage):
    """FRU Inventory Device Lock Control (VITA 46.11 table 10.1.3.19-1).

    The lock of the Chassis FRU Information of a chassis manager (FRU
    254): get the last commit timestamp, lock, unlock and discard the
    writes, or unlock and commit them (``OPERATION_*``); the lock ID is
    the one of the lock to unlock, 0 for the other operations.
    """

    OPERATION_GET_TIMESTAMP = 0
    OPERATION_LOCK = 1
    OPERATION_UNLOCK_DISCARD = 2
    OPERATION_UNLOCK_COMMIT = 3

    __cmdid__ = constants.CMDID_VITA_FRU_INVENTORY_DEVICE_LOCK_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('operation', 1),
        UnsignedInt('lock_id', 2, 0),
    )


@register_message_class
class VitaFruInventoryDeviceLockControlRsp(VitaMessage):
    """The lock ID of a lock, 0 otherwise, and the last commit timestamp.

    The completion code 80h is invalid FRU information at the commit, 81h
    a failed lock or an invalid lock ID.
    """

    __cmdid__ = constants.CMDID_VITA_FRU_INVENTORY_DEVICE_LOCK_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('lock_id', 2),
        Timestamp('last_commit'),
    )


@register_message_class
class VitaFruInventoryDeviceWriteReq(VitaMessage):
    """FRU Inventory Device Write (VITA 46.11 table 10.1.3.20-1).

    A write to a locked FRU Inventory Device, held until its commit.
    """

    __cmdid__ = constants.CMDID_VITA_FRU_INVENTORY_DEVICE_WRITE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('lock_id', 2),
        UnsignedInt('offset', 2),
        RemainingBytes('data'),
    )


@register_message_class
class VitaFruInventoryDeviceWriteRsp(VitaMessage):
    """The bytes written; the completion code 80h is an invalid lock ID."""

    __cmdid__ = constants.CMDID_VITA_FRU_INVENTORY_DEVICE_WRITE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('count_written', 1),
    )


@register_message_class
class VitaGetFruAddressInfoReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        # optional, FRU 0 if it is not given
        Optional(UnsignedInt('fru_id', 1)),
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
    __privilege__ = USER
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
        # the type/length byte and the data of the chassis identifier
        RemainingBytes('chassis_identifier'),
    )


@register_message_class
class VitaSetChassisIdentifierReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_CHASSIS_IDENTIFIER
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        # the type/length byte and the data of the chassis identifier
        RemainingBytes('chassis_identifier'),
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
    __privilege__ = OPERATOR
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
    __privilege__ = USER
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
    __privilege__ = USER
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
    __privilege__ = OPERATOR
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
    __privilege__ = USER
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
    __privilege__ = OPERATOR
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
    __privilege__ = ADMINISTRATOR
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
    __privilege__ = USER
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
    __privilege__ = OPERATOR
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
    __privilege__ = USER
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
    __privilege__ = USER
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
    __privilege__ = USER
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
    __privilege__ = USER
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
    __privilege__ = USER
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
    __privilege__ = OPERATOR
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


# the fan commands of a cooling unit (fan tray), like in PICMG 3.0: the fan
# level 0xfe is the emergency shut down, 0xff the local control

VITA_FAN_LEVEL_EMERGENCY_SHUT_DOWN = 0xfe
VITA_FAN_LEVEL_LOCAL_CONTROL = 0xff


@register_message_class
class VitaGetChassisManagerIpmbAddressReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_MANAGER_IPMB_ADDRESS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetChassisManagerIpmbAddressRsp(VitaMessage):
    """The IPMB addresses of the active and the backup chassis manager.

    The backup address is 0 if no backup chassis manager is known.
    """

    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_MANAGER_IPMB_ADDRESS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('active_address', 1),
        UnsignedInt('backup_address', 1),
    )


@register_message_class
class VitaGetChassisManagerIpAddressesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_MANAGER_IP_ADDRESSES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        # 0 is the chassis manager IP address
        UnsignedInt('address_number', 1),
    )


@register_message_class
class VitaGetChassisManagerIpAddressesRsp(VitaMessage):
    """An IP address of the chassis (VITA 46.11 table 10.1.3.22-1).

    The address type has the address in bits 6:0 (``ADDRESS_TYPE_IPV4``)
    and bit 7 set for the chassis manager IP address; the address of an
    IPv4 address is the address and the RMCP port, in network order.
    """

    ADDRESS_TYPE_IPV4 = 0x00
    ADDRESS_TYPE_CHASSIS_MANAGER = 0x80

    __cmdid__ = constants.CMDID_VITA_GET_CHASSIS_MANAGER_IP_ADDRESSES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Timestamp('last_change'),
        UnsignedInt('address_count', 1),
        UnsignedInt('site_type', 1),
        UnsignedInt('site_number', 1),
        UnsignedInt('max_unavailable_time', 1),
        UnsignedInt('address_type', 1),
        RemainingBytes('address'),
    )


@register_message_class
class VitaGetFanSpeedPropertiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FAN_SPEED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFanSpeedPropertiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FAN_SPEED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('minimum_speed_level', 1),
        UnsignedInt('maximum_speed_level', 1),
        UnsignedInt('normal_operation_level', 1),
        Bitfield('properties', 1,
                 Bitfield.ReservedBit(7, 0),
                 Bitfield.Bit('local_control_supported', 1, default=0),),
    )


@register_message_class
class VitaSetFanLevelReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        UnsignedInt('fan_level', 1),
        # 0 disables, 1 enables the local control
        Optional(
            UnsignedInt('local_control_enable_state', 1),
        ),
    )


@register_message_class
class VitaSetFanLevelRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFanLevelReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFanLevelRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('override_fan_level', 1),
        # only if the fan tray supports the local control
        Optional(
            UnsignedInt('local_control_fan_level', 1),
        ),
        Optional(
            UnsignedInt('local_control_enable_state', 1),
        ),
    )


@register_message_class
class VitaSetFanPolicyReq(VitaMessage):
    """Set Fan Policy (VITA 46.11 table 10.1.3.15-1), to a chassis manager.

    It enables (1) or disables (0) the autonomous control of a fan tray
    site by the chassis manager, for the temperature events of a site
    (site number and type) or of all sites. The timeout of a disable is in
    units of 5 seconds, ``TIMEOUT_INFINITE`` or no timeout for none.
    """

    DISABLE = 0
    ENABLE = 1
    TIMEOUT_INFINITE = 0xff

    __cmdid__ = constants.CMDID_VITA_SET_FAN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fan_tray_site', 1),
        UnsignedInt('enable', 1),
        Optional(UnsignedInt('timeout', 1)),
        Optional(UnsignedInt('site_number', 1)),
        Optional(UnsignedInt('site_type', 1)),
    )


@register_message_class
class VitaSetFanPolicyRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FAN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetFanPolicyReq(VitaMessage):
    """Get Fan Policy (VITA 46.11 table 10.1.3.16-1), to a chassis manager.

    The policy of a fan tray site, for a site (site number and type) or
    for all sites.
    """

    __cmdid__ = constants.CMDID_VITA_GET_FAN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fan_tray_site', 1),
        Optional(UnsignedInt('site_number', 1)),
        Optional(UnsignedInt('site_type', 1)),
    )


@register_message_class
class VitaGetFanPolicyRsp(VitaMessage):
    """The policy: disabled (0), enabled (1) or ``POLICY_INDETERMINATE``.

    The coverage, whether the fan tray cools the site (1) or not (0), is
    only in the response to a request with a site.
    """

    POLICY_DISABLED = 0
    POLICY_ENABLED = 1
    POLICY_INDETERMINATE = 0xff

    __cmdid__ = constants.CMDID_VITA_GET_FAN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('policy', 1),
        Optional(UnsignedInt('coverage', 1)),
    )


def power_supply_signals() -> Bitfield:
    """Return the power supply signals of the PSU module commands.

    The bits are the same in all three commands, their meaning differs: a
    supported signal (Get Power Supply Capabilities), its state (Get Power
    Supply Status), or what to set or reset (Set Power Supply Status).
    """
    return Bitfield('power_supply_signals', 1,
                    Bitfield.Bit('inhibit', 1, default=0),
                    Bitfield.Bit('fail', 1, default=0),
                    Bitfield.Bit('self_protect_bypass', 1, default=0),
                    Bitfield.Bit('over_temperature_protection', 1, default=0),
                    Bitfield.Bit('input_voltage_fault', 1, default=0),
                    Bitfield.Bit('fault_flag_latch', 1, default=0),
                    Bitfield.ReservedBit(2, 0))


@register_message_class
class VitaGetPowerSupplyCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_POWER_SUPPLY_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetPowerSupplyCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_POWER_SUPPLY_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        power_supply_signals(),
    )


@register_message_class
class VitaGetPowerSupplyStatusReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_POWER_SUPPLY_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetPowerSupplyStatusRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_POWER_SUPPLY_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        power_supply_signals(),
    )


@register_message_class
class VitaSetPowerSupplyStatusReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_POWER_SUPPLY_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        power_supply_signals(),
    )


@register_message_class
class VitaSetPowerSupplyStatusRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_POWER_SUPPLY_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetIpmbLinkInfoReq(VitaMessage):
    """Get IPMB Link Info (VITA 46.11 table 10.1.3.17-1).

    The key selects a System IPMB link by its number (0 for a bused, 1-95
    for a radial link) or by the number of its sensor.
    """

    KEY_LINK_NUMBER = 0
    KEY_SENSOR_NUMBER = 1

    __cmdid__ = constants.CMDID_VITA_GET_IPMB_LINK_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('key_type', 1, KEY_LINK_NUMBER),
        UnsignedInt('key', 1, 0),
    )


@register_message_class
class VitaGetIpmbLinkInfoRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_IPMB_LINK_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('link_number', 1),
        UnsignedInt('sensor_number', 1),
    )


def persistent_controls(name: str) -> Bitfield:
    """Return the persistent cold and warm reset bits of a FRU.

    The bits are the same in the three persistent control commands, their
    meaning differs: the current state, a capability, a selection mask or
    the requested state.
    """
    return Bitfield(name, 1,
                    Bitfield.Bit('cold_reset', 1, default=0),
                    Bitfield.Bit('warm_reset', 1, default=0),
                    Bitfield.ReservedBit(6, 0))


@register_message_class
class VitaGetFruPersistentControlReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_PERSISTENT_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaGetFruPersistentControlRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_FRU_PERSISTENT_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        persistent_controls('state'),
    )


@register_message_class
class VitaSetFruPersistentControlReq(VitaMessage):
    """Set FRU Persistent Control (VITA 46.11 table 10.1.3.24-1).

    Only the controls selected in ``mask`` are set to ``state``.
    """

    __cmdid__ = constants.CMDID_VITA_SET_FRU_PERSISTENT_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
        persistent_controls('mask'),
        persistent_controls('state'),
    )


@register_message_class
class VitaSetFruPersistentControlRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_FRU_PERSISTENT_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaFruPersistentControlCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_PERSISTENT_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('fru_id', 1),
    )


@register_message_class
class VitaFruPersistentControlCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_FRU_PERSISTENT_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        persistent_controls('capabilities'),
    )


@register_message_class
class VitaGetWriteProtectCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_WRITE_PROTECT_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetWriteProtectCapabilitiesRsp(VitaMessage):
    """The supported write protect destinations (NVMs) and categories."""

    __cmdid__ = constants.CMDID_VITA_GET_WRITE_PROTECT_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('destinations', 1,
                 Bitfield.Bit('embedded_nvm', 1, default=0),
                 Bitfield.Bit('local_nvm', 1, default=0),
                 Bitfield.Bit('remote_nvm', 1, default=0),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('oem1', 1, default=0),
                 Bitfield.Bit('oem2', 1, default=0)),
        Bitfield('categories', 1,
                 Bitfield.Bit('identification', 1, default=0),
                 Bitfield.Bit('configuration', 1, default=0),
                 Bitfield.Bit('logs', 1, default=0),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('oem1', 1, default=0),
                 Bitfield.Bit('oem2', 1, default=0)),
    )


class VitaWriteProtectOperation:
    """The selectors of the write protect enables commands.

    ``by_destination`` 0 selects a category, the enables are then one bit
    per destination; 1 selects a destination, the enables are one bit per
    category. A set bit in the enables protects against writes.
    """

    BY_CATEGORY = 0
    BY_DESTINATION = 1

    CATEGORY_IDENTIFICATION = 0
    CATEGORY_CONFIGURATION = 1
    CATEGORY_LOGS = 2
    DESTINATION_EMBEDDED_NVM = 0
    DESTINATION_LOCAL_NVM = 1
    DESTINATION_REMOTE_NVM = 2
    OEM1 = 6
    OEM2 = 7


def write_protect_operation() -> Bitfield:
    return Bitfield('operation', 1,
                    Bitfield.Bit('selector', 3, default=0),
                    Bitfield.ReservedBit(4, 0),
                    Bitfield.Bit('by_destination', 1, default=0))


@register_message_class
class VitaGetWriteProtectEnablesReq(VitaMessage, VitaWriteProtectOperation):
    __cmdid__ = constants.CMDID_VITA_GET_WRITE_PROTECT_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        write_protect_operation(),
    )


@register_message_class
class VitaGetWriteProtectEnablesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_WRITE_PROTECT_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('enables', 1),
    )


@register_message_class
class VitaSetWriteProtectEnablesReq(VitaMessage, VitaWriteProtectOperation):
    """Set Write Protect Enables (VITA 46.11 table 10.1.3.36-1).

    Only the bits set in ``mask`` are changed to those of ``enables``.
    """

    __cmdid__ = constants.CMDID_VITA_SET_WRITE_PROTECT_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        write_protect_operation(),
        UnsignedInt('mask', 1, 0),
        UnsignedInt('enables', 1, 0),
    )


@register_message_class
class VitaSetWriteProtectEnablesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_WRITE_PROTECT_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetControlBitsCapabilitiesReq(VitaMessage):
    """Get Control Bits Capabilities (VITA 46.11 table 10.1.3.40-1).

    A bank holds 8 control points; without ``number_of_banks`` one bank is
    returned. On IPMB-0 a response has room for up to 7 banks.
    """

    __cmdid__ = constants.CMDID_VITA_GET_CONTROL_BITS_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('first_bank', 1, 0),
        Optional(UnsignedInt('number_of_banks', 1)),
    )


@register_message_class
class VitaGetControlBitsCapabilitiesRsp(VitaMessage):
    """Three bytes per requested bank in ``banks``.

    The input support, the output support and the enable support (settable)
    of the 8 control points of the bank, one bit each.
    """

    __cmdid__ = constants.CMDID_VITA_GET_CONTROL_BITS_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('number_of_banks_supported', 1),
        RemainingBytes('banks'),
    )


@register_message_class
class VitaGetControlBitsReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_CONTROL_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('first_bank', 1, 0),
        Optional(UnsignedInt('number_of_banks', 1)),
    )


@register_message_class
class VitaGetControlBitsRsp(VitaMessage):
    """Three bytes per requested bank in ``banks``.

    The output enables, the output states and the input states of the 8
    control points of the bank, one bit each.
    """

    __cmdid__ = constants.CMDID_VITA_GET_CONTROL_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        RemainingBytes('banks'),
    )


@register_message_class
class VitaSetControlBitsReq(VitaMessage):
    """Set Control Bits (VITA 46.11 table 10.1.3.42-1).

    Three bytes per bank from ``first_bank`` on in ``banks``: the mask of
    the control points to change, their output enables and their output
    states.
    """

    __cmdid__ = constants.CMDID_VITA_SET_CONTROL_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = OPERATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('first_bank', 1, 0),
        RemainingBytes('banks'),
    )


@register_message_class
class VitaSetControlBitsRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_CONTROL_BITS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


# the bridged firewall commands; a group extension (2Ch) is selected by its
# body code (one byte), an OEM network function (2Eh-3Eh) by its IANA
# enterprise number (three bytes, LSB first)

def bridged_channel(all_channels: bool = False) -> Bitfield:
    """Return the destination channel byte, Eh is the request's channel."""
    if all_channels:
        return Bitfield('channel', 1,
                        Bitfield.Bit('number', 4, default=0),
                        Bitfield.ReservedBit(3, 0),
                        Bitfield.Bit('all_channels', 1, default=0))
    return Bitfield('channel', 1,
                    Bitfield.Bit('number', 4, default=0),
                    Bitfield.ReservedBit(4, 0))


@register_message_class
class VitaGetBridgedNetFnSupportReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_NETFN_SUPPORT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        Bitfield('net_function', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('code', 5, default=0),
                 Bitfield.ReservedBit(2, 0)),
        UnsignedInt('index', 1, 0),
    )


@register_message_class
class VitaGetBridgedNetFnSupportRsp(VitaMessage):
    """The group IDs (2Ch) or IANA numbers (2Eh-3Eh) from the index on."""

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_NETFN_SUPPORT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('total_elements', 1),
        RemainingBytes('elements'),
    )


class VitaBridgedCommandEnablesOperation:
    COMMANDS_00_7F = 0
    COMMANDS_80_FF = 1
    PASS_THROUGH = 2


@register_message_class
class VitaGetBridgedCommandEnablesReq(VitaMessage,
                                      VitaBridgedCommandEnablesOperation):
    """Get Bridged Command Enables (VITA 46.11 table 10.1.3.43-1).

    ``group`` is the body code or IANA number of a group extension or OEM
    network function, empty for the others.
    """

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_COMMAND_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(),
        Bitfield('operation', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('net_function', 5, default=0),
                 Bitfield.Bit('operation', 2, default=0)),
        RemainingBytes('group'),
    )


@register_message_class
class VitaGetBridgedCommandEnablesRsp(VitaMessage):
    """The 16 byte command enable mask or the 2 byte pass-through register.

    Both are LSB first; a set bit allows the command, or the pass-through
    of the messages from the channel.
    """

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_COMMAND_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        RemainingBytes('enables'),
    )


@register_message_class
class VitaSetBridgedCommandEnablesReq(VitaMessage,
                                      VitaBridgedCommandEnablesOperation):
    """Set Bridged Command Enables (VITA 46.11 table 10.1.3.44-1).

    ``data`` is the command enable mask (16 bytes) or the pass-through
    register (2 bytes), followed by the body code or IANA number of a group
    extension or OEM network function. The settings are non-volatile.
    """

    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_COMMAND_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(all_channels=True),
        Bitfield('operation', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('net_function', 5, default=0),
                 Bitfield.Bit('operation', 2, default=0)),
        RemainingBytes('data'),
    )


@register_message_class
class VitaSetBridgedCommandEnablesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_COMMAND_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetBridgedCommandSubFunctionEnablesReq(VitaMessage):
    """Get Bridged Command Sub-function Enables (VITA 46.11 10.1.3.45-1).

    ``group`` is the body code or IANA number of a group extension or OEM
    network function, empty for the others.
    """

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_COMMAND_SUB_FUNCTION_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(),
        Bitfield('net_function', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('code', 5, default=0),
                 Bitfield.ReservedBit(2, 0)),
        UnsignedInt('command', 1, 0),
        RemainingBytes('group'),
    )


@register_message_class
class VitaGetBridgedCommandSubFunctionEnablesRsp(VitaMessage):
    """One bit per sub-function, 0-31 and optionally 32-63."""

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_COMMAND_SUB_FUNCTION_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        UnsignedInt('enables', 4),
        Optional(UnsignedInt('additional_enables', 4)),
    )


@register_message_class
class VitaSetBridgedCommandSubFunctionEnablesReq(VitaMessage):
    """Set Bridged Command Sub-function Enables (VITA 46.11 10.1.3.46-1).

    ``data`` is the body code or IANA number of a group extension or OEM
    network function, followed by the sub-function enables, 4 or 8 bytes
    LSB first. The settings are non-volatile.
    """

    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_COMMAND_SUB_FUNCTION_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(all_channels=True),
        Bitfield('net_function', 1,
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('code', 5, default=0),
                 Bitfield.ReservedBit(2, 0)),
        UnsignedInt('command', 1, 0),
        RemainingBytes('data'),
    )


@register_message_class
class VitaSetBridgedCommandSubFunctionEnablesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_COMMAND_SUB_FUNCTION_ENABLES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


def bridged_netfn_policy() -> Bitfield:
    """Return the policy byte, a set bit allows the requests."""
    return Bitfield('policy', 1,
                    Bitfield.Bit('raw_messages', 1, default=0),
                    Bitfield.Bit('bmc_routing', 1, default=0),
                    Bitfield.Bit('oem_unknown_requests', 1, default=0),
                    Bitfield.ReservedBit(5, 0))


@register_message_class
class VitaSetBridgedNetFnPolicyReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_NETFN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(all_channels=True),
        bridged_netfn_policy(),
    )


@register_message_class
class VitaSetBridgedNetFnPolicyRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_SET_BRIDGED_NETFN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
    )


@register_message_class
class VitaGetBridgedNetFnPolicyReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_NETFN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __privilege__ = USER
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        bridged_channel(all_channels=True),
    )


@register_message_class
class VitaGetBridgedNetFnPolicyRsp(VitaMessage):
    """The policy byte of the channel, or with ``all_channels`` one per channel.

    The channels are 0h-Bh and Fh; a missing byte is a policy of 0h (none
    allowed).
    """

    __cmdid__ = constants.CMDID_VITA_GET_BRIDGED_NETFN_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', GROUP_EXTENSION_VSO),
        RemainingBytes('policies'),
    )
