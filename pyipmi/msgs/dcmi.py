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

from __future__ import absolute_import


from . import constants
from . import register_message_class
from . import Bitfield
from . import CompletionCode
from . import GroupExtensionIdentifier
from . import Message
from . import RemainingBytes
from . import Timestamp
from . import UnsignedInt

DCMI_GROUP_CODE = 0xdc


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
        Bitfield('specification_conformence', 2,
                 Bitfield.Bit('major', 8),
                 Bitfield.Bit('minor', 8)),
        UnsignedInt('parameter_revision', 1),
        RemainingBytes('parameter_data'),
    )


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
    __not_implemented__ = True
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
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetPowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class SetPowerLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class SetPowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetActivateDeactivatePowerLimitReq(DcmiMessage):
    __cmdid__ = constants.CMDID_ACTIVATE_DEACTIVATE_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetActivateDeactivatePowerLimitRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_ACTIVATE_DEACTIVATE_POWER_LIMIT
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetAssetTagReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetAssetTagRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
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
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class SetAssetTagRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_ASSET_TAG
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetManagementControllerIdStringReq(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class GetManagementControllerIdStringRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_GET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class SetManagementControllerIdStringReq(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __not_implemented__ = True
    __fields__ = (
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )


@register_message_class
class SetManagementControllerIdStringRsp(DcmiMessage):
    __cmdid__ = constants.CMDID_SET_MANAGEMENT_CONTROLLER_ID_STRING
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __not_implemented__ = True
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('group_extension_id', DCMI_GROUP_CODE),
    )
