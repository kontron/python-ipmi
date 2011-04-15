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

class GetFruInventoryAreaInfo(Message):
    CMDID = constants.CMDID_GET_FRU_INVENTORY_AREA_INFO
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
        UnsignedInt('fru_id', 1, 0),
    )
    _RSP_DESC = (
        CompletionCode(),
        UnsignedInt('area_size', 2),
        Bitfield('area_info', 1,
            Bitfield.Bit('access', 1),
            Bitfield.ReservedBit(7,0)
        ),
    )


class ReadFruData(Message):
    CMDID = constants.CMDID_READ_FRU_DATA
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = (
            UnsignedInt('fru_id', 1),
            UnsignedInt('offset', 2),
            UnsignedInt('count', 1),
    )

    def _encode_rsp(self):
        data = array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            push_unsigned_int(data, self.rsp.count, 1)
            if len(self.rsp.data) != self.rsp.count:
                raise EncodingError()
            data.extend(self.rsp.data)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.count = pop_unsigned_int(data, 1)
        if len(data) != self.rsp.count:
            raise DecodingError()
        self.rsp.data = data[:self.rsp.count]
