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

from __future__ import absolute_import


from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import RemainingBytes

SELFTEST_RESULT_NO_ERROR = 0x55
SELFTEST_RESULT_NOT_IMPLEMENTED = 0x56
SELFTEST_RESULT_CORRUPTED_DATA_OR_INACCESSIBLE_DEVICE = 0x57
SELFTEST_RESULT_FATAL_HARDWARE_ERROR = 0x58


@register_message_class
class GetDeviceIdReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_ID
    __netfn__ = constants.NETFN_APP


@register_message_class
class GetDeviceIdRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_ID
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('device_id', 1),
        Bitfield('device_revision', 1,
                 Bitfield.Bit('device_revision', 4),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('provides_device_sdrs', 1)),
        Bitfield('firmware_revision', 2,
                 Bitfield.Bit('major', 7),
                 Bitfield.Bit('device_available', 1),
                 Bitfield.Bit('minor', 8)),
        UnsignedInt('ipmi_version', 1),
        Bitfield('additional_support', 1,
                 Bitfield.Bit('sensor', 1),
                 Bitfield.Bit('sdr_repository', 1),
                 Bitfield.Bit('sel', 1),
                 Bitfield.Bit('fru_inventory', 1),
                 Bitfield.Bit('ipmb_event_receiver', 1),
                 Bitfield.Bit('ipmb_event_generator', 1),
                 Bitfield.Bit('bridge', 1),
                 Bitfield.Bit('chassis', 1)),
        UnsignedInt('manufacturer_id', 3),
        UnsignedInt('product_id', 2),
        Optional(ByteArray('auxiliary', 4))
    )


@register_message_class
class ColdResetReq(Message):
    __cmdid__ = constants.CMDID_COLD_RESET
    __netfn__ = constants.NETFN_APP


@register_message_class
class ColdResetRsp(Message):
    __cmdid__ = constants.CMDID_COLD_RESET
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class WarmResetReq(Message):
    __cmdid__ = constants.CMDID_WARM_RESET
    __netfn__ = constants.NETFN_APP


@register_message_class
class WarmResetRsp(Message):
    __cmdid__ = constants.CMDID_WARM_RESET
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class ManufacturingTestOnReq(Message):
    __cmdid__ = constants.CMDID_MANUFACTURING_TEST_ON
    __netfn__ = constants.NETFN_APP
    __fields__ = (
        RemainingBytes('data'),
    )


@register_message_class
class ManufacturingTestOnRsp(Message):
    __cmdid__ = constants.CMDID_MANUFACTURING_TEST_ON
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        RemainingBytes('data'),
    )


@register_message_class
class GetSelftestResultsReq(Message):
    __cmdid__ = constants.CMDID_GET_SELF_TEST_RESULTS
    __netfn__ = constants.NETFN_APP


@register_message_class
class GetSelftestResultsRsp(Message):
    __cmdid__ = constants.CMDID_GET_SELF_TEST_RESULTS
    __netfn__ = constants.NETFN_APP | 1

    __fields__ = (
        CompletionCode(),
        UnsignedInt('result', 1),
        Bitfield('status', 1,
                 Bitfield.Bit('controller_firmware_corrupted', 1, 0),
                 Bitfield.Bit('controller_bootblock_corrupted', 1, 0),
                 Bitfield.Bit('internal_use_area_corrupted', 1, 0),
                 Bitfield.Bit('sdr_repository_empty', 1, 0),
                 Bitfield.Bit('ipmb_signal_lines_do_not_respond', 1, 0),
                 Bitfield.Bit('cannot_access_bmc_fru_device', 1, 0),
                 Bitfield.Bit('cannot_access_sdr_device', 1, 0),
                 Bitfield.Bit('cannot_access_sel_device', 1, 0),),
    )


@register_message_class
class SetAcpiPowerStateReq(Message):
    __cmdid__ = constants.CMDID_SET_ACPI_POWER_STATE
    __netfn__ = constants.NETFN_APP
    __not_implemented__ = True


@register_message_class
class SetAcpiPowerStateRsp(Message):
    __cmdid__ = constants.CMDID_SET_ACPI_POWER_STATE
    __netfn__ = constants.NETFN_APP | 1
    __not_implemented__ = True


@register_message_class
class GetAcpiPowerStateReq(Message):
    __cmdid__ = constants.CMDID_GET_ACPI_POWER_STATE
    __netfn__ = constants.NETFN_APP
    __not_implemented__ = True


@register_message_class
class GetAcpiPowerStateRsp(Message):
    __cmdid__ = constants.CMDID_GET_ACPI_POWER_STATE
    __netfn__ = constants.NETFN_APP | 1
    __not_implemented__ = True


@register_message_class
class GetDeviceGuideReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_GUID
    __netfn__ = constants.NETFN_APP
    __not_implemented__ = True


@register_message_class
class GetDeviceGuideRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_GUID
    __netfn__ = constants.NETFN_APP | 1
    __not_implemented__ = True


@register_message_class
class ResetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_RESET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP


@register_message_class
class ResetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_RESET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_SET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP
    __fields__ = (
        Bitfield('timer_use', 1,
                 Bitfield.Bit('timer_use', 3),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('dont_stop', 1, 0),
                 Bitfield.Bit('dont_log', 1, 0),),
        Bitfield('timer_actions', 1,
                 Bitfield.Bit('timeout_action', 3),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('pre_timeout_interrupt', 3),
                 Bitfield.ReservedBit(1, 0),),
        UnsignedInt('pre_timeout_interval', 1),
        UnsignedInt('timer_use_expiration_flags', 1),
        UnsignedInt('initial_countdown', 2),
    )


@register_message_class
class SetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_SET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_GET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP


@register_message_class
class GetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_GET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('timer_use', 1,
                 Bitfield.Bit('timer_use', 3),
                 Bitfield.ReservedBit(3, 0),
                 Bitfield.Bit('is_running', 1, 0),
                 Bitfield.Bit('dont_log', 1, 0),),
        Bitfield('timer_actions', 1,
                 Bitfield.Bit('timeout_action', 3),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('pre_timeout_interrupt', 3),
                 Bitfield.ReservedBit(1, 0),),
        UnsignedInt('pre_timeout_interval', 1),
        UnsignedInt('timer_use_expiration_flags', 1),
        UnsignedInt('initial_countdown', 2),
        UnsignedInt('present_countdown', 2),
    )
