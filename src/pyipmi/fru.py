#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import array

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import fru
from pyipmi.utils import check_completion_code

class Helper:
    def get_fru_inventory_area_info(self, fn, fru_id=0):
        m = fru.GetFruInventoryAreaInfo()
        m.fru_id = fru_id
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def write_fru_data(self, fn, data, fru_id=0, offset=0):
        m = fru.WriteFruData()
        m.req.fru_id = fru_id
        m.req.offset = offset
        m.req.data = data[:]
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def read_fru_data(self, fn, fru_id=0, offset=None, count=None):
        off = 0
        area_size = 0
        req_size = 32
        data = array.array('c')

        # first check for maximum area size
        info = fru.GetFruInventoryAreaInfo()
        info.fru_id = fru_id
        fn(info)
        check_completion_code(info.rsp.completion_code)

        if offset is None:
            area_size = info.rsp.area_size
            off = 0
        else:
            area_size = offset + count
            off = offset

        while off < area_size:
            if (off + req_size) > area_size:
                req_size = area_size - off

            m = fru.ReadFruData()
            m.req.fru_id = fru_id
            m.req.offset = off
            m.req.count = req_size
            try:
                fn(m)
                check_completion_code(m.rsp.completion_code)
            except CompletionCodeError:
                if m.rsp.completion_code == 0xca:
                    req_size -= 2
                    continue
                else:
                    check_completion_code(m.rsp.completion_code)

            data.extend(m.rsp.data)
            off += m.rsp.count

        f = FruInventory(data.tostring())
        return f

class FruField:
    TYPE_CODE_BINARY = 0
    TYPE_CODE_BCD = 1
    TYPE_CODE_6_BIT_ASCII = 2
    TYPE_CODE_8_BIT_ASCII = 3

class FruInventory:
    def __init__(self, data=None):
        if data:
            self.data = data

    def __str__(self):
        s = ''
        s += 'data len: %d\n' % len(self.data)
        s += ' '.join( ["%02X" % ord(x) for x in self.data])
        return s

    def get_data(self, offset=None, count=None):
        if not offset:
            return self.data[:]
        elif not count:
            return self.data[offset:]
        else:
            return self.data[offset:offset+count]
