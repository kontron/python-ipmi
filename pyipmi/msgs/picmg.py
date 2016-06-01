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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from __future__ import absolute_import
from builtins import range

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import RemainingBytes
from . import Optional

PICMG_IDENTIFIER = 0x00

FRU_ACTIVATION_FRU_ACTIVATE = 0x1
FRU_ACTIVATION_FRU_DEACTIVATE = 0x0

LINK_INTERFACE_BASE = 0x0
LINK_INTERFACE_FABRIC = 0x1
LINK_INTERFACE_UPDATE_CHANNEL = 0x2

LINK_TYPE_BASE = 0x01
LINK_TYPE_ETHERNET_FABRIC = 0x02
LINK_TYPE_INFINIBAND_FABRIC = 0x03
LINK_TYPE_STARFABRIC_FABRIC = 0x04
LINK_TYPE_PCIEXPRESS_FABRIC = 0x05
LINK_TYPE_OEM0 = 0xf0
LINK_TYPE_OEM1 = 0xf1
LINK_TYPE_OEM2 = 0xf2
LINK_TYPE_OEM3 = 0xf3

LINK_TYPE_EXT_BASE0 = 0x00
LINK_TYPE_EXT_BASE1 = 0x01

LINK_SIGNALING_CLASS_BASIC = 0
LINK_SIGNALING_CLASS_10_3125_GBD = 3

# when link signaling class value is 0000b
LINK_TYPE_EXT_ETHERNET_FIX1000_BX = 0x0
LINK_TYPE_EXT_ETHERNET_FIX10G_BX4 = 0x1
LINK_TYPE_EXT_ETHERNET_FCPI = 0x02
LINK_TYPE_EXT_ETHERNET_FIX1000_KX = 0x3
LINK_TYPE_EXT_ETHERNET_FIX10G_KX4 = 0x4

# when link signaling class value is 0011b
LINK_TYPE_EXT_ETHERNET_FIX10G_KR = 0x0
LINK_TYPE_EXT_ETHERNET_FIX40G_KR4 = 0x1

LINK_TYPE_EXT_OEM_LINK_TYPE_EXT_0 = 0x00

LINK_FLAGS_LANE0 = 0x01
LINK_FLAGS_LANE0123 = 0x0f

LINK_STATE_DISABLE = 0
LINK_STATE_ENABLE = 1

FRU_CONTROL_COLD_RESET = 0x00
FRU_CONTROL_WARM_RESET = 0x01
FRU_CONTROL_GRACEFUL_REBOOT = 0x02
FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT = 0x03
FRU_CONTROL_QUIESCED = 0x04

LED_COLOR_BLUE = 0x01
LED_COLOR_RED = 0x02
LED_COLOR_GREEN = 0x03
LED_COLOR_AMBER = 0x04
LED_COLOR_ORANGE = 0x05
LED_COLOR_WHITE = 0x06

LED_FUNCTION_OFF = 0x00
LED_FUNCTION_BLINKING_RANGE = list(range(0x01, 0xfa))
LED_FUNCTION_LAMP_TEST = 0xfb
LED_FUNCTION_ON = 0xff

LED_STATE_LOCAL_CONTROL = 0
LED_STATE_OVERRIDE = 1
LED_STATE_LAMP_TEST = 2

class PicmgIdentifier(UnsignedInt):
    def __init__(self, name='picmg_identifier'):
        super(self.__class__, self).__init__(name, 1, PICMG_IDENTIFIER)


@register_message_class
class GetPicmgPropertiesReq(Message):
    __cmdid__ = constants.CMDID_GET_PICMG_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
    )


@register_message_class
class GetPicmgPropertiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_PICMG_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('extension_version', 1),
            UnsignedInt('max_fru_device_id', 1),
            UnsignedInt('fru_device_id', 1),
    )


@register_message_class
class GetAddressInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetAddressInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('hardware_address', 1),
            UnsignedInt('ipmb_0_address', 1),
            UnsignedInt('ipmb_1_address', 1),
            Optional(
                UnsignedInt('fru_id', 1),
            ),
            Optional(
                UnsignedInt('site_id', 1),
            ),
            Optional(
                UnsignedInt('site_type', 1),
            ),
            Optional(
                UnsignedInt('carrier_number', 1),
            ),
    )


@register_message_class
class GetShelfAddressInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SHELF_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
    )


@register_message_class
class GetShelfAddressInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SHELF_ADDRESS_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            RemainingBytes('shelf_address'),
    )


@register_message_class
class FruControlReq(Message):
    __cmdid__ = constants.CMDID_FRU_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('option', 1),
    )


@register_message_class
class FruControlRsp(Message):
    __cmdid__ = constants.CMDID_FRU_CONTROL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            RemainingBytes('rsp_data'),
    )


@register_message_class
class GetFruControlCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_FRU_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetFruControlCapabilitiesRsp(Message):
    __cmdid__ = constants.CMDID_FRU_CONTROL_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('capabilities', 1,
                Bitfield.ReservedBit(1),
                Bitfield.Bit('warm_reset', 1),
                Bitfield.Bit('graceful_reboot', 1),
                Bitfield.Bit('diagnostic_interrupt', 1),
                Bitfield.ReservedBit(4),
            ),
    )


@register_message_class
class SetFruActivationPolicyReq(Message):
    __cmdid__ = constants.CMDID_SET_FRU_ACTIVATION_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            Bitfield('mask', 1,
                Bitfield.Bit('activation_locked', 1, default=0),
                Bitfield.Bit('deactivation_locked', 1, default=0),
                Bitfield.ReservedBit(6),
            ),
            Bitfield('set', 1,
                Bitfield.Bit('activation_locked', 1, default=0),
                Bitfield.Bit('deactivation_locked', 1, default=0),
                Bitfield.ReservedBit(6),
            ),
    )


@register_message_class
class SetFruActivationPolicyRsp(Message):
    __cmdid__ = constants.CMDID_SET_FRU_ACTIVATION_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )


@register_message_class
class GetFruActivationPolicyReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_ACTIVATION_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetFruActivationPolicyRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_ACTIVATION_POLICY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('policy', 1,
                Bitfield.Bit('activation_locked', 1, default=0),
                Bitfield.Bit('deactivation_locked', 1, default=0),
                Bitfield.ReservedBit(6),
            ),
    )


@register_message_class
class SetFruActivationReq(Message):
    __cmdid__ = constants.CMDID_SET_FRU_ACTIVATION
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('control', 1),
    )


@register_message_class
class SetFruActivationRsp(Message):
    __cmdid__ = constants.CMDID_SET_FRU_ACTIVATION
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )


@register_message_class
class GetDeviceLocatorRecordIdReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVLOC_RECORD_ID
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetDeviceLocatorRecordIdRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVLOC_RECORD_ID
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('record_id', 2),
    )


@register_message_class
class GetFruLedPropertiesReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetFruLedPropertiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('general_status_led_properties', 1,
                Bitfield.Bit('blue_led', 1),
                Bitfield.Bit('led1', 1),
                Bitfield.Bit('led2', 1),
                Bitfield.Bit('led3', 1),
                Bitfield.ReservedBit(4),
            ),
            UnsignedInt('application_specific_led_count', 1),
    )


@register_message_class
class GetFruLedColorCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_COLOR_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
    )


@register_message_class
class GetFruLedColorCapabilitiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_COLOR_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('color_capabilities', 1,
                Bitfield.ReservedBit(1),
                Bitfield.Bit('blue', 1),
                Bitfield.Bit('red', 1),
                Bitfield.Bit('green', 1),
                Bitfield.Bit('amber', 1),
                Bitfield.Bit('orange', 1),
                Bitfield.Bit('white', 1),
                Bitfield.ReservedBit(1)
            ),
            UnsignedIntMask('local_def_color', 1, 0x0f),
            UnsignedIntMask('override_def_color', 1, 0x0f),
    )


@register_message_class
class GetPowerLevelReq(Message):
    __cmdid__ = constants.CMDID_GET_POWER_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        PicmgIdentifier(),
        UnsignedInt('fru_id', 1),
        UnsignedInt('power_type', 1),
    )


@register_message_class
class GetPowerLevelRsp(Message):
    __cmdid__ = constants.CMDID_GET_POWER_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('properties', 1,
                Bitfield.Bit('power_level', 5, 0),
                Bitfield.ReservedBit(2, 0),
                Bitfield.Bit('dynamic_power_configuration', 1, 0),
            ),
            UnsignedInt('delay_to_stable_power', 1),
            UnsignedInt('power_multiplier', 1),
            RemainingBytes('power_draw'),
    )

@register_message_class
class GetFanSpeedPropertiesReq(Message):
    __cmdid__ = constants.CMDID_GET_FAN_SPEED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )

@register_message_class
class GetFanSpeedPropertiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_FAN_SPEED_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('minimum_speed_level', 1),
            UnsignedInt('maximum_speed_level', 1),
            UnsignedInt('normal_operation_level', 1),
            Bitfield('properties', 1,
                Bitfield.ReservedBit(7, 0),
                Bitfield.Bit('local_control_supported', 1),
            ),
    )

@register_message_class
class SetFanLevelReq(Message):
    __cmdid__ = constants.CMDID_SET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('fan_level', 1),
            UnsignedInt('extra_byte', 1),
    )

@register_message_class
class SetFanLevelRsp(Message):
    __cmdid__ = constants.CMDID_SET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )

@register_message_class
class GetFanLevelReq(Message):
    __cmdid__ = constants.CMDID_GET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )

@register_message_class
class GetFanLevelRsp(Message):
    __cmdid__ = constants.CMDID_GET_FAN_LEVEL
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('override_fan_level', 1),
            Optional(
                RemainingBytes('data'),
            )
    )


@register_message_class
class SetFruLedStateReq(Message):
    __cmdid__ = constants.CMDID_SET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
            UnsignedInt('led_function', 1),
            UnsignedInt('on_duration', 1),
            UnsignedIntMask('color', 1, 0x0f),
    )


@register_message_class
class SetFruLedStateRsp(Message):
    __cmdid__ = constants.CMDID_SET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )


@register_message_class
class GetFruLedStateReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION

    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
    )


@register_message_class
class GetFruLedStateRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_LED_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1

    def _cond_override(obj):
        return (obj.led_states.override_en == 1
                or obj.led_states.lamp_test_en == 1)

    def _cond_lamp_test(obj):
        return obj.led_states.lamp_test_en == 1

    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('led_states', 1,
                Bitfield.Bit('local_avail', 1),
                Bitfield.Bit('override_en', 1),
                Bitfield.Bit('lamp_test_en', 1),
                Bitfield.ReservedBit(5)
            ),
            UnsignedInt('local_function', 1),
            UnsignedInt('local_on_duration', 1),
            UnsignedIntMask('local_color', 1, 0x0f),
            Conditional(_cond_override,
                UnsignedInt('override_function', 1)),
            Conditional(_cond_override,
                UnsignedInt('override_on_duration', 1)),
            Conditional(_cond_override,
                UnsignedIntMask('override_color', 1, 0x0f)),
            Conditional(_cond_lamp_test,
                UnsignedIntMask('lamp_test_duration', 1, 0x7f)),
    )


@register_message_class
class SetPortStateReq(Message):
    __cmdid__ = constants.CMDID_SET_PORT_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            Bitfield('link_info', 4,
                Bitfield.Bit('channel', 6),
                Bitfield.Bit('interface', 2),
                Bitfield.Bit('port_0', 1),
                Bitfield.Bit('port_1', 1),
                Bitfield.Bit('port_2', 1),
                Bitfield.Bit('port_3', 1),
                Bitfield.Bit('type', 4),
                Bitfield.Bit('sig_class', 4, 0),
                Bitfield.Bit('type_extension', 4),
                Bitfield.Bit('grouping_id', 8, 0),
            ),
            UnsignedInt('state', 1),
    )


@register_message_class
class SetPortStateRsp(Message):
    __cmdid__ = constants.CMDID_SET_PORT_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )


@register_message_class
class GetPortStateReq(Message):
    __cmdid__ = constants.CMDID_GET_PORT_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            Bitfield('channel', 1,
                Bitfield.Bit('number', 6),
                Bitfield.Bit('interface', 2),
            ),
    )


@register_message_class
class GetPortStateRsp(Message):
    __cmdid__ = constants.CMDID_GET_PORT_STATE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            RemainingBytes('data'),
    )


@register_message_class
class SetSignalingClassReq(Message):
    __cmdid__ = constants.CMDID_SET_CHANNEL_SIGNALING_CLASS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            Bitfield('channel_info', 1,
                Bitfield.Bit('channel_number', 6, 0),
                Bitfield.Bit('interface', 2, 0),
            ),
            Bitfield('channel_signaling', 1,
                Bitfield.Bit('class_capability', 4, 0),
                Bitfield.ReservedBit(4)
            ),
    )


@register_message_class
class SetSignalingClassRsp(Message):
    __cmdid__ = constants.CMDID_SET_CHANNEL_SIGNALING_CLASS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
    )


@register_message_class
class GetSignalingClassReq(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_SIGNALING_CLASS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            Bitfield('channel_info', 1,
                Bitfield.Bit('channel_number', 6, 0),
                Bitfield.Bit('interface', 2, 0),
            ),
    )


@register_message_class
class GetSignalingClassRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHANNEL_SIGNALING_CLASS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('channel_info', 1,
                Bitfield.Bit('channel_number', 6, 0),
                Bitfield.Bit('interface', 2, 0),
            ),
            Bitfield('channel_signaling', 1,
                Bitfield.Bit('class_capability', 4, 0),
                Bitfield.ReservedBit(4)
            ),
    )


@register_message_class
class GetLocationInformationReq(Message):
    __cmdid__ = constants.CMDID_GET_LOCATION_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            Bitfield('info', 1,
                Bitfield.Bit('carrier_number', 5, 0),
                Bitfield.ReservedBit(1),
                Bitfield.Bit('mcs', 2, 0),
            ),
            UnsignedInt('site_number', 1),
            UnsignedInt('site_type', 1),
    )


@register_message_class
class GetLocationInformationRsp(Message):
    __cmdid__ = constants.CMDID_GET_LOCATION_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('slot_number', 1),
            UnsignedInt('tier_number', 1),
            Bitfield('info', 1,
                Bitfield.ReservedBit(5),
                Bitfield.Bit('carrier_orientation', 1, 0),
                Bitfield.Bit('tier_number', 1, 0),
                Bitfield.Bit('slot_number', 1, 0),
            ),
            UnsignedInt('origin_x', 2),
            UnsignedInt('origin_y', 2),
    )


@register_message_class
class GetPowerChannelStatusReq(Message):
    __cmdid__ = constants.CMDID_GET_POWER_CHANNEL_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('starting_power_channel_number', 1),
            UnsignedInt('power_channel_count', 1),
    )


@register_message_class
class GetPowerChannelStatusRsp(Message):
    __cmdid__ = constants.CMDID_GET_POWER_CHANNEL_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('max_power_channel_number', 1),
            Bitfield('global_status', 1,
                Bitfield.Bit('role', 1, 0),
                Bitfield.Bit('management_power_good', 1, 0),
                Bitfield.Bit('payload_power_good', 1, 0),
                Bitfield.Bit('unidentified_fault', 1, 0),
                Bitfield.ReservedBit(4),
            ),
            RemainingBytes('data'),
    )


@register_message_class
class GetTelcoAlarmCapabilityReq(Message):
    __cmdid__ = constants.CMDID_GET_TELCO_ALARM_CAPABILITY
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
    )


@register_message_class
class GetTelcoAlarmCapabilityRsp(Message):
    __cmdid__ = constants.CMDID_GET_TELCO_ALARM_CAPABILITY
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('alarm_capabilities', 1,
                Bitfield.Bit('critical_alarm', 1, 0),
                Bitfield.Bit('major_alarm', 1, 0),
                Bitfield.Bit('minor_alarm', 1, 0),
                Bitfield.Bit('power_alarm', 1, 0),
                Bitfield.Bit('test_alarm', 1, 0),
                Bitfield.Bit('autonomous_alarm_cutoff', 1, 0),
                Bitfield.Bit('autonomous_minor_reset', 1, 0),
                Bitfield.Bit('autonomous_majorreset', 1, 0),
            ),
    )
