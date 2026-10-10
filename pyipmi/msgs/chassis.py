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
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import RemainingBytes

CONTROL_POWER_DOWN = 0
CONTROL_POWER_UP = 1
CONTROL_POWER_CYCLE = 2
CONTROL_HARD_RESET = 3
CONTROL_DIAGNOSTIC_INTERRUPT = 4
CONTROL_SOFT_SHUTDOWN = 5


@register_message_class
class GetChassisCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_GET_CHASSIS_CAPABILITIES
    __netfn__ = constants.NETFN_CHASSIS


@register_message_class
class GetChassisCapabilitiesRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHASSIS_CAPABILITIES
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('capabilities_flags', 1,
                 Bitfield.Bit('intrusion_sensor', 1),
                 Bitfield.Bit('frontpanel_lockout', 1),
                 Bitfield.Bit('diagnostic_interrupt', 1),
                 Bitfield.Bit('power_interlock', 1),
                 Bitfield.ReservedBit(4, 0)),
        UnsignedInt('fru_info_device_address', 1),
        UnsignedInt('sdr_device_address', 1),
        UnsignedInt('sel_device_address', 1),
        UnsignedInt('system_management_device_address', 1),
        Optional(
            UnsignedInt('bridge_device_address', 1)
        ),
    )


@register_message_class
class GetChassisStatusReq(Message):
    __cmdid__ = constants.CMDID_GET_CHASSIS_STATUS
    __netfn__ = constants.NETFN_CHASSIS


@register_message_class
class GetChassisStatusRsp(Message):
    __cmdid__ = constants.CMDID_GET_CHASSIS_STATUS
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('current_power_state', 1,
                 Bitfield.Bit('power_on', 1),
                 Bitfield.Bit('power_overload', 1),
                 Bitfield.Bit('interlock', 1),
                 Bitfield.Bit('power_fault', 1),
                 Bitfield.Bit('power_control_fault', 1),
                 Bitfield.Bit('power_restore_policy', 2),
                 Bitfield.ReservedBit(1, 0),),
        Bitfield('last_power_event', 1,
                 Bitfield.Bit('ac_failed', 1),
                 Bitfield.Bit('power_overload', 1),
                 Bitfield.Bit('power_interlock', 1),
                 Bitfield.Bit('power_fault', 1),
                 Bitfield.Bit('power_is_on_via_ipmi_command', 1),
                 Bitfield.ReservedBit(3, 0),),
        Bitfield('misc_chassis_state', 1,
                 Bitfield.Bit('chassis_intrusion_active', 1),
                 Bitfield.Bit('front_panel_lockout_active', 1),
                 Bitfield.Bit('drive_fault', 1),
                 Bitfield.Bit('cooling_fault_detected', 1),
                 Bitfield.Bit('chassis_id_state', 2),
                 Bitfield.Bit('id_cmd_state_info_support', 1),
                 Bitfield.ReservedBit(1, 0),),
        Optional(
            UnsignedInt('front_panel_button_capabilities', 1),
        ),
    )


@register_message_class
class ChassisControlReq(Message):
    __cmdid__ = constants.CMDID_CHASSIS_CONTROL
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('control', 1,
                 Bitfield.Bit('option', 4),
                 Bitfield.ReservedBit(4, 0)),
    )


@register_message_class
class ChassisControlRsp(Message):
    __cmdid__ = constants.CMDID_CHASSIS_CONTROL
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class ChassisResetReq(Message):
    __cmdid__ = constants.CMDID_CHASSIS_RESET
    __netfn__ = constants.NETFN_CHASSIS


@register_message_class
class ChassisResetRsp(Message):
    __cmdid__ = constants.CMDID_CHASSIS_RESET
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class ChassisIdentifyReq(Message):
    __cmdid__ = constants.CMDID_CHASSIS_IDENTIFY
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        # identify interval in seconds, 0 turns off the identify, the BMC
        # uses its default (15 seconds) without it
        Optional(
            UnsignedInt('interval', 1)
        ),
        # only allowed with the interval: bit 0 set forces the identify on,
        # until it is turned off with the interval 0
        Optional(
            UnsignedInt('force_on', 1)
        ),
    )


@register_message_class
class ChassisIdentifyRsp(Message):
    __cmdid__ = constants.CMDID_CHASSIS_IDENTIFY
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetChassisCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_SET_CHASSIS_CAPABILITIES
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('capabilities_flags', 1,
                 Bitfield.Bit('intrusion_sensor', 1),
                 Bitfield.Bit('frontpanel_lockout', 1),
                 Bitfield.ReservedBit(6, 0)),
        UnsignedInt('fru_info_device_address', 1),
        UnsignedInt('sdr_device_address', 1),
        UnsignedInt('sel_device_address', 1),
        UnsignedInt('system_management_device_address', 1),
        Optional(
            UnsignedInt('bridge_device_address', 1)
        ),
    )


@register_message_class
class SetChassisCapabilitiesRsp(Message):
    __cmdid__ = constants.CMDID_SET_CHASSIS_CAPABILITIES
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetPowerRestorePolicyReq(Message):
    __cmdid__ = constants.CMDID_SET_POWER_RESTORE_POLICY
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('power_restore_policy', 1,
                 Bitfield.Bit('policy', 3),
                 Bitfield.ReservedBit(5, 0)),
    )


@register_message_class
class SetPowerRestorePolicyRsp(Message):
    __cmdid__ = constants.CMDID_SET_POWER_RESTORE_POLICY
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('power_restore_policy_support', 1,
                 Bitfield.Bit('always_off', 1),
                 Bitfield.Bit('restore_previous', 1),
                 Bitfield.Bit('always_on', 1),
                 Bitfield.ReservedBit(5, 0)),
    )


@register_message_class
class GetSystemRestartCauseReq(Message):
    __cmdid__ = constants.CMDID_GET_SYSTEM_RESTART_CAUSE
    __netfn__ = constants.NETFN_CHASSIS


@register_message_class
class GetSystemRestartCauseRsp(Message):
    __cmdid__ = constants.CMDID_GET_SYSTEM_RESTART_CAUSE
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('restart_cause', 1,
                 Bitfield.Bit('cause', 4),
                 Bitfield.ReservedBit(4, 0)),
        # mandatory, but not returned by all BMCs
        Optional(
            UnsignedInt('channel_number', 1)
        ),
    )


@register_message_class
class GetPohCounterReq(Message):
    __cmdid__ = constants.CMDID_GET_POH_COUNTER
    __netfn__ = constants.NETFN_CHASSIS


@register_message_class
class GetPohCounterRsp(Message):
    __cmdid__ = constants.CMDID_GET_POH_COUNTER
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('minutes_per_count', 1),
        UnsignedInt('counter_reading', 4),
    )


@register_message_class
class GetSystemBootOptionsReq(Message):
    __cmdid__ = constants.CMDID_GET_SYSTEM_BOOT_OPTIONS
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('parameter_selector', 1,
                 Bitfield.Bit('boot_option_parameter_selector', 7),
                 Bitfield.ReservedBit(1)),
        UnsignedInt('set_selector', 1, 0),
        UnsignedInt('block_selector', 1, 0)
    )


@register_message_class
class GetSystemBootOptionsRsp(Message):
    __cmdid__ = constants.CMDID_GET_SYSTEM_BOOT_OPTIONS
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('parameter_version', 1,
                 Bitfield.Bit('parameter_version', 4, default=1),
                 Bitfield.ReservedBit(4)),
        Bitfield('parameter_valid', 1,
                 Bitfield.Bit('boot_option_parameter_selector', 7),
                 Bitfield.Bit('parameter_validity', 1)),
        RemainingBytes('data'),
    )


@register_message_class
class SetSystemBootOptionsReq(Message):
    __cmdid__ = constants.CMDID_SET_SYSTEM_BOOT_OPTIONS
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('parameter_selector', 1,
                 Bitfield.Bit('boot_option_parameter_selector', 7),
                 Bitfield.Bit('parameter_validity', 1, default=0)),
        RemainingBytes('data')
    )


@register_message_class
class SetSystemBootOptionsRsp(Message):
    __cmdid__ = constants.CMDID_SET_SYSTEM_BOOT_OPTIONS
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetFrontPanelButtonEnablesReq(Message):
    __cmdid__ = constants.CMDID_SET_FRONT_PANEL_BUTTON_ENABLES
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        Bitfield('disable', 1,
                 Bitfield.Bit('power_off_button', 1),
                 Bitfield.Bit('reset_button', 1),
                 Bitfield.Bit('diagnostic_interrupt_button', 1),
                 Bitfield.Bit('standby_button', 1),
                 Bitfield.ReservedBit(4, 0)),
    )


@register_message_class
class SetFrontPanelButtonEnablesRsp(Message):
    __cmdid__ = constants.CMDID_SET_FRONT_PANEL_BUTTON_ENABLES
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetPowerCycleIntervalReq(Message):
    __cmdid__ = constants.CMDID_SET_POWER_CYCLE_INTERVAL
    __netfn__ = constants.NETFN_CHASSIS
    __fields__ = (
        UnsignedInt('interval', 1),
    )


@register_message_class
class SetPowerCycleIntervalRsp(Message):
    __cmdid__ = constants.CMDID_SET_POWER_CYCLE_INTERVAL
    __netfn__ = constants.NETFN_CHASSIS | 1
    __fields__ = (
        CompletionCode(),
    )
