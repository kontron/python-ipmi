from __future__ import absolute_import
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
from . import UnsignedInt
from . import Bitfield
from . import CompletionCode
from . import Optional
from . import RemainingBytes
from . import GroupExtensionIdentifier
from .picmg import PicmgMessage, PICMG_IDENTIFIER


@register_message_class
class GetTargetUpgradeCapabilitiesReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_TARGET_UPGRADE_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class GetTargetUpgradeCapabilitiesRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_TARGET_UPGRADE_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('hpm_1_version', 1),
        Bitfield('capabilities', 1,
                 Bitfield.Bit('firmware_upgrade_undesirable', 1),
                 Bitfield.Bit('automatic_rollback_overriden', 1),
                 Bitfield.Bit('ipmc_degraded_during_upgrade', 1),
                 Bitfield.Bit('deferred_activation', 1),
                 Bitfield.Bit('services_affected_by_upgrade', 1),
                 Bitfield.Bit('manual_rollback', 1),
                 Bitfield.Bit('automatic_rollback', 1),
                 Bitfield.Bit('selftest', 1),),
        Bitfield('timeout', 4,
                 Bitfield.Bit('upgrade', 8),
                 Bitfield.Bit('selftest', 8),
                 Bitfield.Bit('rollback', 8),
                 Bitfield.Bit('inaccessibility', 8),),
        UnsignedInt('component_present', 1),
    )


@register_message_class
class GetComponentPropertiesReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_COMPONENT_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('id', 1),
        UnsignedInt('selector', 1),
    )


@register_message_class
class GetComponentPropertiesRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_COMPONENT_PROPERTIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        RemainingBytes('data'),
    )


@register_message_class
class AbortFirmwareUpgradeReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_ABORT_FIRMWARE_UPGRADE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class AbortFirmwareUpgradeRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_ABORT_FIRMWARE_UPGRADE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class InitiateUpgradeActionReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_INITIATE_UPGRADE_ACTION
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('components', 1),
        UnsignedInt('action', 1),
    )


@register_message_class
class InitiateUpgradeActionRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_INITIATE_UPGRADE_ACTION
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class UploadFirmwareBlockReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_UPLOAD_FIRMWARE_BLOCK
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('number', 1),
        RemainingBytes('data'),
    )


@register_message_class
class UploadFirmwareBlockRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_UPLOAD_FIRMWARE_BLOCK
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        Optional(UnsignedInt('section_offset', 4)),
        Optional(UnsignedInt('section_length', 4)),
    )


@register_message_class
class FinishFirmwareUploadReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_FINISH_FIRMWARE_UPLOAD
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('component_id', 1),
        UnsignedInt('image_length', 4),
    )


@register_message_class
class FinishFirmwareUploadRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_FINISH_FIRMWARE_UPLOAD
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class GetUpgradeStatusReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_UPGRADE_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class GetUpgradeStatusRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_GET_UPGRADE_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('command_in_progress', 1),
        UnsignedInt('last_completion_code', 1),
        Optional(UnsignedInt('completion_estimate', 1)),
    )


@register_message_class
class ActivateFirmwareReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_ACTIVATE_FIRMWARE
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        Optional(UnsignedInt('rollback_override_policy', 1)),
    )


@register_message_class
class ActivateFirmwareRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_ACTIVATE_FIRMWARE
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class QuerySelftestResultsReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_QUERY_SELFTEST_RESULTS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class QuerySelftestResultsRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_QUERY_SELFTEST_RESULTS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('selftest_result_1', 1),
        UnsignedInt('selftest_result_2', 1),
    )


@register_message_class
class QueryRollbackStatusReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_QUERY_ROLLBACK_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class QueryRollbackStatusRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_QUERY_ROLLBACK_STATUS
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
        UnsignedInt('rollback_status', 1),
        Optional(UnsignedInt('completion_estimate', 1)),
    )


@register_message_class
class InitiateManualRollbackReq(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_INITIATE_MANUAL_ROLLBACK
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )


@register_message_class
class InitiateManualRollbackRsp(PicmgMessage):
    __cmdid__ = constants.CMDID_HPM_INITIATE_MANUAL_ROLLBACK
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('picmg_identifier', PICMG_IDENTIFIER),
    )
