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

"""The PEF and alerting commands (IPMI v2.0 section 30)."""

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import RemainingBytes
from . import Timestamp
from .privileges import ADMINISTRATOR, OPERATOR, USER


@register_message_class
class GetPefCapabilitiesReq(Message):
    __cmdid__ = constants.CMDID_GET_PEF_CAPABILITIES
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = USER


@register_message_class
class GetPefCapabilitiesRsp(Message):
    """The PEF version (51h), the supported actions, the filter count."""

    __cmdid__ = constants.CMDID_GET_PEF_CAPABILITIES
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('pef_version', 1, 0x51),
        Bitfield('action_support', 1,
                 Bitfield.Bit('alert', 1, 0),
                 Bitfield.Bit('power_down', 1, 0),
                 Bitfield.Bit('reset', 1, 0),
                 Bitfield.Bit('power_cycle', 1, 0),
                 Bitfield.Bit('oem', 1, 0),
                 Bitfield.Bit('diagnostic_interrupt', 1, 0),
                 Bitfield.ReservedBit(1, 0),
                 Bitfield.Bit('oem_event_record_filtering', 1, 0),),
        UnsignedInt('event_filter_table_entries', 1),
    )


@register_message_class
class ArmPefPostponeTimerReq(Message):
    """Arm PEF Postpone Timer.

    The timeout: 0 disables the postpone timer, 1 to FDh seconds,
    ``TEMPORARY_DISABLE`` disables PEF until it is armed again,
    ``GET_COUNTDOWN`` only returns the present countdown.
    """

    DISABLE = 0x00
    TEMPORARY_DISABLE = 0xfe
    GET_COUNTDOWN = 0xff

    __cmdid__ = constants.CMDID_ARM_PEF_POSTPONE_TIMER
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        UnsignedInt('timeout', 1),
    )


@register_message_class
class ArmPefPostponeTimerRsp(Message):
    __cmdid__ = constants.CMDID_ARM_PEF_POSTPONE_TIMER
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('countdown', 1),
    )


@register_message_class
class SetPefConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_SET_PEFCONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('parameter', 1,
                 Bitfield.Bit('selector', 7, 0),
                 Bitfield.ReservedBit(1, 0),),
        RemainingBytes('data'),
    )


@register_message_class
class SetPefConfigurationParametersRsp(Message):
    """Set PEF Configuration Parameters.

    The completion codes 80h parameter not supported, 81h set in
    progress, 82h read-only parameter.
    """

    __cmdid__ = constants.CMDID_SET_PEFCONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetPefConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_GET_PEFCONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = OPERATOR
    __fields__ = (
        Bitfield('parameter', 1,
                 Bitfield.Bit('selector', 7, 0),
                 Bitfield.Bit('get_revision_only', 1, 0),),
        UnsignedInt('set_selector', 1, 0),
        UnsignedInt('block_selector', 1, 0),
    )


@register_message_class
class GetPefConfigurationParametersRsp(Message):
    __cmdid__ = constants.CMDID_GET_PEFCONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('parameter_revision', 1, 0x11),
        RemainingBytes('data'),
    )


@register_message_class
class SetLastProcessedEventIdReq(Message):
    """Set Last Processed Event ID.

    The record ID of the last event processed by software (0) or by the
    BMC (1).
    """

    SOFTWARE = 0
    BMC = 1

    __cmdid__ = constants.CMDID_SET_LAST_PROCESSED_EVENT_ID
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = ADMINISTRATOR
    __fields__ = (
        Bitfield('processor', 1,
                 Bitfield.Bit('bmc', 1, 0),
                 Bitfield.ReservedBit(7, 0),),
        UnsignedInt('record_id', 2),
    )


@register_message_class
class SetLastProcessedEventIdRsp(Message):
    """The completion code 81h is a SEL erase in progress."""

    __cmdid__ = constants.CMDID_SET_LAST_PROCESSED_EVENT_ID
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetLastProcessedEventIdReq(Message):
    __cmdid__ = constants.CMDID_GET_LAST_PROCESSED_EVENT_ID
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __privilege__ = ADMINISTRATOR


@register_message_class
class GetLastProcessedEventIdRsp(Message):
    """Get Last Processed Event ID.

    The time of the last SEL addition, the record ID of the last SEL
    record (FFFFh if the SEL is empty), and the last ones processed by
    software and by the BMC.
    """

    __cmdid__ = constants.CMDID_GET_LAST_PROCESSED_EVENT_ID
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
        Timestamp('most_recent_addition'),
        UnsignedInt('last_record_id', 2),
        UnsignedInt('last_software_processed_id', 2),
        UnsignedInt('last_bmc_processed_id', 2),
    )
