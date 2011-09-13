import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import RemainingBytes
from pyipmi.utils import ByteBuffer
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
        data = ByteBuffer()
        data.push_unsigned_int(self.completion_code, 1)
        if (self.completion_code == constants.CC_OK):
            data.push_unsigned_int(self.count, 1)
            if len(self.data) != self.count:
                raise EncodingError()
            data.append_array(self.data)
        return data.to_string()

    def _decode(self, data):
        data = ByteBuffer(data)
        self.completion_code = data.pop_unsigned_int(1)
        if (self.completion_code != constants.CC_OK):
            return
        self.count = data.pop_unsigned_int(1)
        if len(data) != self.count:
            raise DecodingError()
        self.data = data[:self.count]


@register_message_class
class WriteFruDataReq(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE
    __default_lun__ = 0

    __fields__ = (
        UnsignedInt('fru_id', 1),
        UnsignedInt('offset', 2),
        RemainingBytes('data'),
    )


@register_message_class
class WriteFruDataRsp(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        UnsignedInt('count_written', 1)
    )
