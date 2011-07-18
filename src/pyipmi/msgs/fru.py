from array import array

import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import DecodingError, EncodingError

@register_message_class
class GetFruInventoryAreaInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_INVENTORY_AREA_INFO
    __netfn__ = constants.NETFN_STORAGE
    __default_lun__ = 0
    __fields__ = (
        UnsignedInt('fru_id', 1, 0),
    )


@register_message_class
class GetFruInventoryAreaInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_INVENTORY_AREA_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        UnsignedInt('area_size', 2),
        Bitfield('area_info', 1,
            Bitfield.Bit('access', 1),
            Bitfield.ReservedBit(7,0)
        ),
    )


@register_message_class
class ReadFruDataReq(Message):
    __cmdid__ = constants.CMDID_READ_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE
    __default_lun__ = 0
    __fields__ = (
            UnsignedInt('fru_id', 1),
            UnsignedInt('offset', 2),
            UnsignedInt('count', 1),
    )


@register_message_class
class ReadFruDataRsp(Message):
    __cmdid__ = constants.CMDID_READ_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE | 1
    __default_lun__ = 0

    def _encode(self):
        data = array('c')
        push_unsigned_int(data, self.completion_code, 1)
        if (self.completion_code == constants.CC_OK):
            push_unsigned_int(data, self.count, 1)
            if len(self.data) != self.count:
                raise EncodingError()
            data.extend(self.data)
        return data.tostring()

    def _decode(self, data):
        data = array('c', data)
        self.completion_code = pop_unsigned_int(data, 1)
        if (self.completion_code != constants.CC_OK):
            return
        self.count = pop_unsigned_int(data, 1)
        if len(data) != self.count:
            raise DecodingError()
        self.data = data[:self.count]


@register_message_class
class WriteFruDataReq(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE
    __default_lun__ = 0

    def _encode(self):
        data = array('c')
        push_unsigned_int(data, self.fru_id, 1)
        push_unsigned_int(data, self.offset, 2)
        data.extend(self.data)
        return data.tostring()

    def _decode(self, data):
        data = array('c', data)
        self.fru_id = pop_unsigned_int(data, 1)
        self.offset = pop_unsigned_int(data, 2)
        self.data = data[:]


@register_message_class
class WriteFruDataRsp(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        UnsignedInt('count_written', 1)
    )
