# Copyright (c) 2018  Kontron Europe GmbH
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


import warnings
from typing import Any

from . import constants
from . import register_message_class
from . import Bitfield
from . import CompletionCode
from . import GroupExtensionIdentifier
from . import Message
from . import RemainingBytes
from . import Timestamp
from . import UnsignedInt

DCMI_GROUP_CODE = constants.GROUP_EXTENSION_DCMI


class DcmiMessage(Message):
    __group_extension__ = DCMI_GROUP_CODE


@register_message_class
class GetDcmiCapabilitiesReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_CAPABILITIES_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('parameter_selector', 1),
    )


@register_message_class
class GetDcmiCapabilitiesRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_CAPABILITIES_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        Bitfield('specification_conformance', 2,
                 Bitfield.Bit('major', 8),
                 Bitfield.Bit('minor', 8)),
        UnsignedInt('parameter_revision', 1),
        RemainingBytes('parameter_data'),
    )

    @property
    def specification_conformence(self) -> Any:
        """Deprecated, misspelled name of specification_conformance."""
        warnings.warn('specification_conformence is deprecated, use '
                      'specification_conformance', DeprecationWarning,
                      stacklevel=2)
        return self.specification_conformance


@register_message_class
class GetPowerReadingReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_POWER_READING
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('mode', 1),
        UnsignedInt('attributes', 1),
        UnsignedInt('reserved', 1),
    )


@register_message_class
class GetPowerReadingRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_POWER_READING
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('current_power', 2),
        UnsignedInt('minimum_power', 2),
        UnsignedInt('maximum_power', 2),
        UnsignedInt('average_power', 2),
        Timestamp('timestamp'),
        UnsignedInt('period', 4),
        UnsignedInt('reading_state', 1),
    )


@register_message_class
class GetPowerLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('reserved', 2, 0),
    )


@register_message_class
class GetPowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('reserved_1', 2, 0),
        UnsignedInt('exception_actions', 1),
        UnsignedInt('power_limit', 2),
        UnsignedInt('correction_time_limit', 4),
        UnsignedInt('reserved_2', 2, 0),
        UnsignedInt('statistics_sampling_period', 2),
    )


@register_message_class
class SetPowerLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('reserved_1', 3, 0),
        UnsignedInt('exception_actions', 1),
        UnsignedInt('power_limit', 2),
        UnsignedInt('correction_time_limit', 4),
        UnsignedInt('reserved_2', 2, 0),
        UnsignedInt('statistics_sampling_period', 2),
    )


@register_message_class
class SetPowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class ActivateDeactivatePowerLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_ACTIVATE_DEACTIVATE_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('activation', 1),
        UnsignedInt('reserved', 2, 0),
    )


@register_message_class
class ActivateDeactivatePowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_ACTIVATE_DEACTIVATE_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetAssetTagReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('offset', 1),
        UnsignedInt('number_of_bytes', 1),
    )


@register_message_class
class GetAssetTagRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_length', 1),
        RemainingBytes('data'),
    )


@register_message_class
class GetDcmiSensorInfoReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_SENSOR_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('sensor_type', 1),
        UnsignedInt('entity_id', 1),
        UnsignedInt('entity_instance', 1),
        UnsignedInt('entity_instance_start', 1),
    )


@register_message_class
class GetDcmiSensorInfoRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_SENSOR_INFO
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_number_of_instances', 1),
        UnsignedInt('number_of_record_ids', 1),
        RemainingBytes('record_ids'),
    )


@register_message_class
class SetAssetTagReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('offset', 1),
        UnsignedInt('number_of_bytes', 1),
        RemainingBytes('data'),
    )


@register_message_class
class SetAssetTagRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_length', 1),
    )


@register_message_class
class GetManagementControllerIdStringReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('offset', 1),
        UnsignedInt('number_of_bytes', 1),
    )


@register_message_class
class GetManagementControllerIdStringRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_length', 1),
        RemainingBytes('data'),
    )


@register_message_class
class SetManagementControllerIdStringReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('offset', 1),
        UnsignedInt('number_of_bytes', 1),
        RemainingBytes('data'),
    )


@register_message_class
class SetManagementControllerIdStringRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_length', 1),
    )


def _thermal_exception_actions() -> Bitfield:
    return Bitfield('exception_actions', 1,
                    Bitfield.ReservedBit(5, 0),
                    Bitfield.Bit('log_event_to_sel', 1),
                    Bitfield.Bit('hard_power_off', 1),
                    Bitfield.Bit('enable', 1))


@register_message_class
class SetThermalLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_THERMAL_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('entity_id', 1),
        UnsignedInt('entity_instance', 1),
        _thermal_exception_actions(),
        UnsignedInt('temperature_limit', 1),
        UnsignedInt('exception_time', 2),
    )


@register_message_class
class SetThermalLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_THERMAL_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetThermalLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_THERMAL_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('entity_id', 1),
        UnsignedInt('entity_instance', 1),
    )


@register_message_class
class GetThermalLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_THERMAL_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        _thermal_exception_actions(),
        UnsignedInt('temperature_limit', 1),
        UnsignedInt('exception_time', 2),
    )


@register_message_class
class GetTemperatureReadingsReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_TEMPERATURE_READINGS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('sensor_type', 1, 1),
        UnsignedInt('entity_id', 1),
        UnsignedInt('entity_instance', 1),
        UnsignedInt('entity_instance_start', 1),
    )


@register_message_class
class GetTemperatureReadingsRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_TEMPERATURE_READINGS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('total_number_of_instances', 1),
        UnsignedInt('number_of_readings', 1),
        # pairs of (temperature, entity instance)
        RemainingBytes('readings'),
    )


@register_message_class
class SetDcmiConfigurationParametersReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_DCMI_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('parameter_selector', 1),
        UnsignedInt('set_selector', 1, 0),
        RemainingBytes('parameter_data'),
    )


@register_message_class
class SetDcmiConfigurationParametersRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_DCMI_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetDcmiConfigurationParametersReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        UnsignedInt('parameter_selector', 1),
        UnsignedInt('set_selector', 1, 0),
    )


@register_message_class
class GetDcmiConfigurationParametersRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_DCMI_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
        Bitfield('specification_conformance', 2,
                 Bitfield.Bit('major', 8),
                 Bitfield.Bit('minor', 8)),
        UnsignedInt('parameter_revision', 1),
        RemainingBytes('parameter_data'),
    )
