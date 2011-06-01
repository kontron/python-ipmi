from array import array
import constants
from pyipmi.msgs import Message
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import DecodingError, EncodingError

PICMG_IDENTIFIER = 0x00

class PicmgIdentifier(UnsignedInt):
    def __init__(self, name='picmg_identifier'):
        UnsignedInt.__init__(self, name, 1, PICMG_IDENTIFIER)


class GetTargetUpgradeCapabilities(Message):
    CMDID = constants.CMDID_HPM_GET_TARGET_UPGRADE_CAPABILITIES
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('hpm_1_version', 1),
            Bitfield('capabilities', 1,
                Bitfield.Bit('firmware_upgrade_undesirable', 1),
                Bitfield.Bit('automatic_rollback_overriden', 1),
                Bitfield.Bit('ipmc_degraded_during_upgrade', 1),
                Bitfield.Bit('deferred_actiation', 1),
                Bitfield.Bit('services_affected_by_upgrade', 1),
                Bitfield.Bit('manual_rollback', 1),
                Bitfield.Bit('automtic_rollback', 1),
                Bitfield.Bit('selftest', 1),
            ),
            UnsignedInt('upgrade_timeout', 1),
            UnsignedInt('selftest_timeout', 1),
            UnsignedInt('rollback_timeout', 1),
            UnsignedInt('inaccessiblity_timeout', 1),
            Bitfield('component_present', 1,
                Bitfield.Bit('0', 1),
                Bitfield.Bit('1', 1),
                Bitfield.Bit('2', 1),
                Bitfield.Bit('3', 1),
                Bitfield.Bit('4', 1),
                Bitfield.Bit('5', 1),
                Bitfield.Bit('6', 1),
                Bitfield.Bit('7', 1),
            ),
    )


class GetComponentProperties(Message):
    CMDID = constants.CMDID_HPM_GET_COMPONENT_PROPERTIES
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('component_id', 1),
            UnsignedInt('component_properties_selector', 1),
    )

    def _encode_rsp(self):
        data = array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            data.extend(self.rsp.data)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)
        self.rsp.data = data[:]

class AbortFirmwareUpgrade(Message):
    CMDID = constants.CMDID_HPM_ABORT_FIRMWARE_UPGRADE
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class InitiateUpgradeAction(Message):
    CMDID = constants.CMDID_HPM_INITIATE_UPGRADE_ACTION
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('components', 1),
            UnsignedInt('upgrade_action', 1),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class UploadFirmwareBlock(Message):
    CMDID = constants.CMDID_HPM_UPLOAD_FIRMWARE_BLOCK
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    def _encode_req(self):
        data = array('c', data)
        push_unsigned_int(data, self.req.completion_code)
        if (self.rsp.completion_code == constants.CC_OK):
            push_unsigned_int(data, PICMG_IDENTIFIER)
            data.extend(self.req.data)
        return data.tostring()

    def _decode_req(self, data):
        data = array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.picmg_identifier = pop_unsigned_int(data)
        self.rsp.data = data[:]

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            data.extend(self.rsp.data)
            if self.rsp.section_offset is not None:
                push_unsigned_int(data, self.rsp.section_offset)
            if self.rsp.section_length is not None:
                push_unsigned_int(data, self.rsp.section_length)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array.array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)
        if (len(data) != 0):
            self.rsp.section_offset = pop_unsigned_int(data, 4)
        if (len(data) != 0):
            self.rsp.section_length = pop_unsigned_int(data, 4)


class FinishFirmwareUpload(Message):
    CMDID = constants.CMDID_HPM_FINISH_FIRMWARE_UPLOAD
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('component_id', 1),
            UnsignedInt('image_length', 4),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class GetUpgradeStatus(Message):
    CMDID = constants.CMDID_HPM_GET_UPGRADE_STATUS
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
    )

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)

    def _decode_rsp(self, data):
        data = array.array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)
        self.rsp.command_in_progress = pop_unsigned_int(data, 1)
        if (len(data) != 0):
            self.rsp.completion_estimate = pop_unsigned_int(data, 1)


class ActivateFirmware(Message):
    CMDID = constants.CMDID_HPM_ACTIVATE_FIRMWARE
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    def _encode_req(self):
        data = array('c', data)
        push_unsigned_int(data, PICMG_IDENTIFIER)
        if self.req.rollback_override_policy is not None:
            push_unsigned_int(data, self.req.rollback_override_policy)
        return data.tostring()

    def _decode_req(self, data):
        data = array('c', data)
        self.rsp.picmg_identifier = pop_unsigned_int(data)
        if len(data) != 0:
            self.req.rollback_override_policy = pop_unsigned_int(data)

    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class QuerySelftestResults(Message):
    CMDID = constants.CMDID_HPM_QUERY_SELFTEST_RESULTS
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
            UnsignedInt('selftest_result_1', 1),
            UnsignedInt('selftest_result_2', 1),
    )


class QueryRollbackStatus(Message):
    CMDID = constants.CMDID_HPM_QUERY_ROLLBACK_STATUS
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
    )

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)

    def _decode_rsp(self, data):
        data = array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.picmg_identifier = pop_unsigned_int(data, 1)
        self.rsp.rollback_status = pop_unsigned_int(data, 1)
        if len(data) != 0:
            self.rsp.completion_estimate = pop_unsigned_int(data, 1)


class InitiateManualRollback(Message):
    CMDID = constants.CMDID_HPM_INITIATE_MANUAL_ROLLBACK
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )
