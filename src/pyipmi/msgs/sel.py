import array

import constants
from pyipmi.msgs import Message
from pyipmi.msgs import ByteArray
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import DecodingError, EncodingError

class GetSelInfo(Message):
    CMDID = constants.CMDID_GET_SEL_INFO
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('version', 1, default=0x51),
            UnsignedInt('entries', 2),
            UnsignedInt('free_bytes', 2),
            Timestamp('most_recent_addition'),
            Timestamp('most_recent_erase'),
            Bitfield('operation_support', 1,
                Bitfield.Bit('get_sel_allocation_info', 1),
                Bitfield.Bit('reserve_sel', 1),
                Bitfield.Bit('partial_add_sel_entry', 1),
                Bitfield.Bit('delete_sel', 1),
                Bitfield.ReservedBit(3),
                Bitfield.Bit('overflow_flag', 1)
            )
    )


class GetSelAllocationInfo(Message):
    CMDID = constants.CMDID_GET_SEL_ALLOCATION_INFO
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('possible_alloc_units', 2),
            UnsignedInt('alloc_unit_size', 2),
            UnsignedInt('free_alloc_units', 2),
            UnsignedInt('largest_free_block', 2),
            UnsignedInt('max_record_size', 1)
    )


class ReserveSel(Message):
    CMDID = constants.CMDID_RESERVE_SEL
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2)
    )


class GetSelEntry(Message):
    CMDID = constants.CMDID_GET_SEL_ENTRY
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('length', 1),
    )
    _RSP_DESC = ()

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            push_unsigned_int(data, self.rsp.next_record_id, 2)
            data.extend(self.rsp.record_data)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array.array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.next_record_id = pop_unsigned_int(data, 2)
        self.rsp.record_data = data[:]


class AddSelEntry(Message):
    CMDID = constants.CMDID_ADD_SEL_ENTRY
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            ByteArray('record_data', 16)
    )
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('record_id', 2)
    )


class DeleteSelEntry(Message):
    CMDID = constants.CMDID_DELETE_SEL_ENTRY
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2)
    )
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('record_id', 2)
    )


class ClearSel(Message):
    CMDID = constants.CMDID_CLEAR_SEL
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            UnsignedInt('reservation_id', 2),
            ByteArray('key', 3, default='CLR'),
            UnsignedInt('cmd', 1)
    )
    _RSP_DESC = (
            CompletionCode(),
            Bitfield('status', 1,
                Bitfield.Bit('erase_in_progress', 4),
                Bitfield.ReservedBit(4),
            )
    )

class GetSelTime(Message):
    CMDID = constants.CMDID_GET_SEL_TIME
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            Timestamp('timestamp')
    )


class SetSelTime(Message):
    CMDID = constants.CMDID_SET_SEL_TIME
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            Timestamp('timestamp')
    )
    _RSP_DESC = (
            CompletionCode()
    )
