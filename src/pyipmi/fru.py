#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import array
import codecs
import datetime

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import fru
from pyipmi.utils import check_completion_code, bcd_search

codecs.register(bcd_search)

class Fru:
    def get_fru_inventory_area_info(self, fru_id=0):
        m = fru.GetFruInventoryAreaInfo()
        m.fru_id = fru_id
        self.send_message(m)
        check_completion_code(m.rsp.completion_code)
        return m.rsp.area_size

    def write_fru_data(self, data, offset=0, fru_id=0):
        m = fru.WriteFruData()
        m.req.fru_id = fru_id
        m.req.offset = offset
        m.req.data = data[:]
        self.send_message(m)
        check_completion_code(m.rsp.completion_code)

    def read_fru_data(self, offset=None, count=None, fru_id=0):
        off = 0
        area_size = 0
        req_size = 32
        data = array.array('c')

        # first check for maximum area size

        if offset is None:
            area_size = self.get_fru_inventory_area_info(fru_id)
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
                self.send_message(m)
                check_completion_code(m.rsp.completion_code)
            except CompletionCodeError, e:
                if e.cc == 0xca:
                    req_size -= 2
                    continue
                else:
                    raise

            data.extend(m.rsp.data)
            off += m.rsp.count

        return data.tostring()

    def get_fru_inventory(self, fru_id=0):
        return FruInventory(self.read_fru_data(fru_id=fru_id))

class FruDataField:
    TYPE_BINARY = 0
    TYPE_BCD_PLUS = 1
    TYPE_6BIT_ASCII = 2
    TYPE_ASCII_OR_UTF16 = 3

    def __init__(self, data=None, offset=0, force_lang_english=False):
        if data:
            self.from_data(data, offset, force_lang_english)

    def __str__(self):
        if self.type is FruDataField.TYPE_BINARY:
            return ' '.join('%02x' % ord(b) for b in self.value)
        else:
            return self.value

    def from_data(self, data, offset=0, force_lang_english=False):
        self.type = ord(data[offset]) >> 6 & 0x3
        self.length = ord(data[offset]) & 0x3f

        self.raw = data[offset+1:offset+1+self.length]

        if type == self.TYPE_BCD_PLUS:
            value = self.raw.decode('bcd+')
        elif type == self.TYPE_6BIT_ASCII:
            value = self.raw.decode('6bitascii')
        else:
            value = self.raw

        self.value = value

class InventoryCommonHeader:
    def __init__(self, data=None):
        if data:
            self.from_data(data)

    def from_data(self, data):
        if len(data) != 8:
            raise DecodingError('InventoryCommonHeader length != 8')
        self.format_version = ord(data[0]) & 0x0f
        self.internal_use_area_offset = ord(data[1]) * 8 or None
        self.chassis_info_area_offset = ord(data[2]) * 8 or None
        self.board_info_area_offset = ord(data[3]) * 8 or None
        self.product_info_area_offset = ord(data[4]) * 8 or None
        self.multirecord_area_offset = ord(data[5]) * 8 or None
        if sum([ord(c) for c in data]) % 256 != 0:
            raise DecodingError('InventoryCommonHeader checksum failed')


class CommonInfoArea:
    def __init__(self, data=None):
        if data:
            self.from_data(data)

    def from_data(self, data):
        self.format_version = ord(data[0]) & 0x0f
        if self.format_version != 1:
            raise DecodingError('unsupported format version (%d)' %
                    self.format_version)
        self.length = ord(data[1]) * 8
        if sum([ord(c) for c in data[:self.length]]) % 256 != 0:
            raise DecodingError('checksum failed')

class InventoryChassisInfoArea(CommonInfoArea):
    TYPE_OTHER = 1
    TYPE_UNKNOWN = 2
    TYPE_DESKTOP = 3
    TYPE_LOW_PROFILE_DESKTOP = 4
    TYPE_PIZZA_BOX = 5
    TYPE_MINI_TOWER = 6
    TYPE_TOWER = 7
    TYPE_PORTABLE = 8
    TYPE_LAPTOP = 9
    TYPE_NOTEBOOK = 10
    TYPE_HAND_HELD = 11
    TYPE_DOCKING_STATION = 12
    TYPE_ALL_IN_ONE = 13
    TYPE_SUB_NOTEBOOK = 14
    TYPE_SPACE_SAVING = 15
    TYPE_LUNCH_BOX = 16
    TYPE_MAIN_SERVER_CHASSIS = 17
    TYPE_EXPANSION_CHASSIS = 18
    TYPE_SUB_CHASSIS = 19
    TYPE_BUS_EXPANSION_CHASSIS = 20
    TYPE_PERIPHERAL_CHASSIS = 21
    TYPE_RAID_CHASSIS = 22
    TYPE_RACK_MOUNT_CHASSIS = 23

    def from_data(self, data):
        CommonInfoArea.from_data(self, data)
        self.type = ord(data[2])
        offset = 3
        self.part_number = FruDataField(data, offset)
        offset += self.part_number.length+1
        self.serial_number = FruDataField(data, offset, True)
        offset += self.serial_number.length+1
        self.custom_chassis_info = list()
        while ord(data[offset]) != 0xc1:
            field = FruDataField(data, offset)
            self.custom_chassis_info.append(field)
            offset += field.length+1

class InventoryBoardInfoArea(CommonInfoArea):
    def from_data(self, data):
        CommonInfoArea.from_data(self, data)
        self.language_code = ord(data[2])
        minutes = ord(data[5]) << 16 | ord(data[4]) << 8 | ord(data[3])
        self.mfg_date = (datetime.datetime(1996, 1, 1)
                + datetime.timedelta(minutes=minutes))
        offset = 6
        self.manufacturer = FruDataField(data, offset)
        offset += self.manufacturer.length+1
        self.product_name = FruDataField(data, offset)
        offset += self.product_name.length+1
        self.serial_number = FruDataField(data, offset, True)
        offset += self.serial_number.length+1
        self.part_number = FruDataField(data, offset)
        offset += self.part_number.length+1
        self.fru_file_id = FruDataField(data, offset, True)
        offset += self.fru_file_id.length+1
        self.custom_mfg_info = list()
        while ord(data[offset]) != 0xc1:
            field = FruDataField(data, offset)
            self.custom_mfg_info.append(field)
            offset += field.length+1

class InventoryProductInfoArea(CommonInfoArea):
    def from_data(self, data):
        CommonInfoArea.from_data(self, data)
        self.language_code = ord(data[2])
        offset = 3
        self.manufacturer = FruDataField(data, offset)
        offset += self.manufacturer.length+1
        self.name = FruDataField(data, offset)
        offset += self.name.length+1
        self.part_number = FruDataField(data, offset)
        offset += self.part_number.length+1
        self.version = FruDataField(data, offset)
        offset += self.version.length+1
        self.serial_number = FruDataField(data, offset, True)
        offset += self.serial_number.length+1
        self.asset_tag = FruDataField(data, offset)
        offset += self.asset_tag.length+1
        self.fru_file_id = FruDataField(data, offset, True)
        offset += self.fru_file_id.length+1
        self.custom_mfg_info = list()
        while ord(data[offset]) != 0xc1:
            field = FruDataField(data, offset)
            self.custom_mfg_info.append(field)
            offset += field.length+1

class FruDataMultiRecord:
    TYPE_POWER_SUPPLY_INFORMATION = 0
    TYPE_DC_OUTPUT = 1
    TYPE_DC_LOAD = 2
    TYPE_MANAGEMENT_ACCESS_RECORD = 3
    TYPE_BASE_COMPATIBILITY_RECORD = 4
    TYPE_EXTENDED_COMPATIBILITY_RECORD = 5
    TYPE_OEM = range(0x0c, 0x100)

    def __init__(self, data, offset=0):
        if data:
            self.from_data(data, offset)

    def __str__(self):
        return '%02x: %s' % (self.type,
                ' '.join('%02x' % ord(b) for b in self.raw))

    def from_data(self, data, offset=0):
        self.type = ord(data[offset])
        self.format_version = ord(data[offset+1]) & 0x0f
        self.length = ord(data[offset+2])
        if sum([ord(c) for c in data[offset:offset+5]]) % 256 != 0:
            raise DecodingError('FruDataMultiRecord header checksum failed')
        self.raw = data[offset+5:offset+5+self.length]
        if (sum([ord(c) for c in self.raw]) + ord(data[offset+3])) % 256 != 0:
            raise DecodingError('FruDataMultiRecord record checksum failed')

class InventoryMultiRecordArea:
    def __init__(self, data):
        if data:
            self.from_data(data)

    def from_data(self, data):
        self.records = list()
        offset = 0
        while not ord(data[offset+1]) & 0x80:
            record = FruDataMultiRecord(data, offset)
            self.records.append(record)
            offset += record.length+5

class FruInventory:
    def __init__(self, data=None):
        self.chassis_info_area = None
        self.board_info_area = None
        self.product_info_area = None

        if data:
            self.from_data(data)

    def from_data(self, data):
        self.raw = data
        self.common_header = InventoryCommonHeader(data[:8])

        if self.common_header.chassis_info_area_offset:
            self.chassis_info_area = InventoryChassisInfoArea(
                    data[self.common_header.chassis_info_area_offset:])

        if self.common_header.board_info_area_offset:
            self.board_info_area = InventoryBoardInfoArea(
                    data[self.common_header.board_info_area_offset:])

        if self.common_header.product_info_area_offset:
            self.product_info_area = InventoryProductInfoArea(
                    data[self.common_header.product_info_area_offset:])

        if self.common_header.multirecord_area_offset:
            self.multirecord_area = InventoryMultiRecordArea(
                    data[self.common_header.multirecord_area_offset:])
