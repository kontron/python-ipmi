#!/usr/bin/env python
import datetime
import os
from types import SimpleNamespace

import pytest

from pyipmi.errors import CompletionCodeError, DataNotFound, DecodingError
from pyipmi.msgs import constants

from pyipmi.fru import (Fru, FruData, FruDataMultiRecord, FruDataUnknown,
                        FruDcLoadRecord, FruDcOutputRecord,
                        FruFmcI2cDeviceDefinition, FruFmcMainDefinition,
                        FruFmcPlusMainDefinition, FruFmcRecord, FruInventory,
                        FruPicmgPowerModuleCapabilityRecord, FruPicmgRecord,
                        InventoryCommonHeader, InventoryBoardInfoArea,
                        get_fru_inventory_from_file)


this_file_path = os.path.dirname(os.path.abspath(__file__))


def test_frudata_object():
    fru_field = FruData((0, 1, 2, 3))
    assert fru_field.data[0] == 0
    assert fru_field.data[1] == 1
    assert fru_field.data[2] == 2
    assert fru_field.data[3] == 3

    fru_field = FruData('\x00\x01\x02\x03')
    assert fru_field.data[0] == 0
    assert fru_field.data[1] == 1
    assert fru_field.data[2] == 2
    assert fru_field.data[3] == 3


def test_commonheader_object():
    InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 235))


def test_commonheader_object_invalid_checksum():
    with pytest.raises(DecodingError):
        InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 0))

    InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 0), ignore_checksum=True)


def test_fru_inventory_from_file():
    fru_file = os.path.join(this_file_path, 'fru_bin/kontron_am4010.bin')
    fru = get_fru_inventory_from_file(fru_file)
    assert fru.chassis_info_area is None
    assert fru.board_info_area is not None
    assert fru.product_info_area is not None
    assert fru.multirecord_area is not None


def test_fru_inventory_from_file_2():
    fru_file = os.path.join(this_file_path, 'fru_bin/fru_supermicro_x11scz-f.bin')
    fru = get_fru_inventory_from_file(fru_file)
    assert fru.chassis_info_area is None
    assert fru.board_info_area is not None
    assert fru.product_info_area is not None
    assert fru.multirecord_area is None


def test_fru_inventory_from_file_3():
    fru_file = os.path.join(this_file_path,
                            'fru_bin/supermicro_A2SDi-4C-HLN4F.bin')
    fru = get_fru_inventory_from_file(fru_file)
    assert fru.multirecord_area is None

    chassis_area = fru.chassis_info_area
    assert chassis_area.type == 23  # rack mount chassis
    assert chassis_area.part_number.string == ''
    assert chassis_area.serial_number.string == ''

    board_area = fru.board_info_area
    assert board_area.mfg_date == datetime.datetime(2025, 2, 15, 16, 0)
    assert board_area.manufacturer.string == 'Supermicro'
    assert board_area.product_name.string == 'A2SDi-4C-HLN4F'
    assert board_area.serial_number.string == 'OM252S008784'
    assert board_area.part_number.string == ''

    product_area = fru.product_info_area
    assert product_area.manufacturer.string == 'Thomas-Krenn.AG'
    assert product_area.name.string == '1HE Intel Single-CPU RI1102A-F Server'
    assert product_area.version.string == '2.0'
    assert product_area.serial_number.string == '9000430981'
    assert product_area.part_number.string == ''
    assert product_area.asset_tag.string == ''


def test_fru_inventory_from_file_4():
    fru_file = os.path.join(this_file_path,
                            'fru_bin/HP_ProLiant_BL460c_Gen8.bin')
    fru = get_fru_inventory_from_file(fru_file)

    chassis_area = fru.chassis_info_area
    assert chassis_area.type == 17  # main server chassis
    assert chassis_area.part_number.string == ''
    assert chassis_area.serial_number.string == 'CZJ2380K2L'
    assert len(chassis_area.custom_chassis_info) == 2

    board_area = fru.board_info_area
    assert board_area.language_code == 25  # english
    assert board_area.mfg_date == datetime.datetime(2012, 9, 14, 14, 42)
    assert board_area.manufacturer.string == 'HP'
    assert board_area.product_name.string == 'HP ProLiant BL460c Gen8'
    assert board_area.serial_number.string == 'TW29NQ0583    '
    assert board_area.part_number.string == '654609-001'
    assert board_area.fru_file_id.string == '06/08/11'
    assert len(board_area.custom_mfg_info) == 2

    product_area = fru.product_info_area
    assert product_area.manufacturer.string == 'HP'
    assert product_area.name.string == 'HP ProLiant BL460c Gen8'
    assert product_area.part_number.string == '666162-B21'
    assert product_area.version.string == 'G8'
    assert product_area.serial_number.string == 'CZJ2380K2L'
    assert product_area.asset_tag.string == ''
    assert product_area.fru_file_id.string == ''

    # three HP OEM records
    records = fru.multirecord_area.records
    assert len(records) == 3
    assert [r.record_type_id for r in records] == [0xd0, 0xd0, 0xd0]
    assert [r.length for r in records] == [47, 8, 7]
    assert [r.end_of_list for r in records] == [False, False, True]
    # the manufacturer ID of the OEM records is 11, Hewlett-Packard
    assert [r.manufacturer_id for r in records] == [11, 11, 11]
    assert [r.manufacturer_name for r in records] == ['Hewlett-Packard'] * 3
    assert str(records[2]) == ('d0 (OEM, manufacturer ID 11 = Hewlett-Packard): '
                               '0b 00 00 02 0b 00 00')


def test_board_area():
    fru_file = os.path.join(this_file_path, 'fru_bin/kontron_am4010.bin')
    fru = get_fru_inventory_from_file(fru_file)

    board_area = fru.board_info_area
    assert board_area.manufacturer.string == 'Kontron'
    assert board_area.product_name.string == 'AM4010'
    assert board_area.serial_number.string == '0023721003'
    assert board_area.part_number.string == '35943'


def test_product_area():
    fru_file = os.path.join(this_file_path, 'fru_bin/kontron_am4010.bin')
    fru = get_fru_inventory_from_file(fru_file)

    product_area = fru.product_info_area
    assert product_area.manufacturer.string == 'Kontron'
    assert product_area.name.string == 'AM4010'
    assert product_area.serial_number.string == '0000000000000000000000000'
    assert product_area.part_number.string == '0012'


def test_multirecord_with_power_module_capability_record():
    fru_file = os.path.join(this_file_path, 'fru_bin/vadatech_utc017.bin')
    fru = get_fru_inventory_from_file(fru_file)
    assert len(fru.multirecord_area.records) == 1
    record = fru.multirecord_area.records[0]
    assert isinstance(record, FruPicmgPowerModuleCapabilityRecord)
    assert record.maximum_current_output == 42.0


def test_BoardInfoArea():
    area = InventoryBoardInfoArea(b'\x01\t\x00\x00\x00\x00\x83d\xc9\xb2\xdePowerEdge R515                \xceCN717033AI0058\xc90RMRF7A05A\x03\xc1\x00\x00*')
    assert area.manufacturer.string == 'DELL'
    assert area.product_name.string == 'PowerEdge R515                '
    assert area.serial_number.string == 'CN717033AI0058'
    assert area.part_number.string == '0RMRF7A05'


def test_FruInventory_ignore_checksum_error():
    data = b'\x01\x00\x00\x01\x04\x00\x00\xfa\x01\x03\x00vq\xb4\xcaASRockRack\xc0\xc0\xc0\xc0\xc1\x00\x1b\x01\x03\x00\xcaASRockRack\xc0\xc0\xc0\xc0\xc0\xc0\xc1\x00\x00M\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    with pytest.raises(DecodingError):
        FruInventory(data, ignore_checksum=False)

    inv = FruInventory(data, ignore_checksum=True)

    assert inv.board_info_area.manufacturer.string == 'ASRockRack'
    assert inv.product_info_area.manufacturer.string == 'ASRockRack'


def _area_checksum(data, offset):
    """Return the position of the checksum of an info area."""
    return offset + data[offset + 1] * 8 - 1


def _record_data(data, offset):
    """Return the position of the last data byte of the first record."""
    return offset + 5 + data[offset + 2] - 1


@pytest.mark.parametrize('filename, position', [
    # common header checksum
    ('HP_ProLiant_BL460c_Gen8.bin', lambda d, h: 7),
    ('HP_ProLiant_BL460c_Gen8.bin',
     lambda d, h: _area_checksum(d, h.chassis_info_area_offset)),
    ('HP_ProLiant_BL460c_Gen8.bin',
     lambda d, h: _area_checksum(d, h.board_info_area_offset)),
    ('HP_ProLiant_BL460c_Gen8.bin',
     lambda d, h: _area_checksum(d, h.product_info_area_offset)),
    # multirecord header checksum
    ('HP_ProLiant_BL460c_Gen8.bin', lambda d, h: h.multirecord_area_offset + 4),
    # record data of an unknown, a PICMG and a power module record
    ('HP_ProLiant_BL460c_Gen8.bin',
     lambda d, h: _record_data(d, h.multirecord_area_offset)),
    ('kontron_am4010.bin',
     lambda d, h: _record_data(d, h.multirecord_area_offset)),
    ('vadatech_utc017.bin',
     lambda d, h: _record_data(d, h.multirecord_area_offset)),
], ids=['header', 'chassis', 'board', 'product', 'record-header',
        'record-data', 'picmg-record-data', 'power-module-record-data'])
def test_fru_inventory_ignore_checksum(filename, position):
    with open(os.path.join(this_file_path, 'fru_bin', filename), 'rb') as f:
        data = bytearray(f.read())
    header = InventoryCommonHeader(data[:8])
    data[position(data, header)] ^= 0x01

    with pytest.raises(DecodingError, match='checksum'):
        FruInventory(data)
    FruInventory(data, ignore_checksum=True)


class FakeFruDevice(Fru):
    """Answers Read FRU Data like a device with a maximum read length."""

    def __init__(self, data, max_length=32,
                 cc=constants.CC_CANT_RET_NUM_REQ_BYTES, fru_size=None,
                 area_info_cc=None):
        super().__init__()
        self.data = data
        self.max_length = max_length
        self.cc = cc
        # reported FRU size, the data can be shorter than that
        self.fru_size = len(data) if fru_size is None else fru_size
        self.area_info_cc = area_info_cc
        self.requests = []
        self.fru_ids = set()

    def send_message_by_name(self, name, fru_id, offset=None, count=None):
        if name == 'GetFruInventoryAreaInfo':
            if self.area_info_cc is not None:
                raise CompletionCodeError(self.area_info_cc)
            return SimpleNamespace(area_size=self.fru_size)
        assert name == 'ReadFruData'
        # reading beyond the FRU data is an error on real devices
        assert offset + count <= len(self.data)
        self.requests.append((offset, count))
        self.fru_ids.add(fru_id)
        if count > self.max_length:
            raise CompletionCodeError(self.cc)
        rsp = SimpleNamespace(data=self.data[offset:offset + count])
        rsp.count = len(rsp.data)
        return rsp


FRU_DATA = bytes(range(100))


def test_read_fru_data():
    fru = FakeFruDevice(FRU_DATA)
    assert fru.read_fru_data(offset=0, count=100) == FRU_DATA
    assert fru.requests == [(0, 32), (32, 32), (64, 32), (96, 4)]


def test_read_fru_data_offset_without_count():
    fru = FakeFruDevice(FRU_DATA)
    assert fru.read_fru_data(offset=90) == FRU_DATA[90:]


@pytest.mark.parametrize('cc', [constants.CC_CANT_RET_NUM_REQ_BYTES,
                                constants.CC_REQ_DATA_FIELD_EXCEED,
                                constants.CC_PARAM_OUT_OF_RANGE])
def test_read_fru_data_reduce_read_length(cc):
    fru = FakeFruDevice(FRU_DATA, max_length=28, cc=cc)
    assert fru.read_fru_data(offset=0, count=60) == FRU_DATA[:60]
    assert fru.requests == [(0, 32), (0, 30), (0, 28), (28, 28), (56, 4)]

    # the reduced length is kept for the following reads
    fru.requests = []
    assert fru.read_fru_data(offset=8, count=40) == FRU_DATA[8:48]
    assert fru.requests == [(8, 28), (36, 12)]


def test_read_fru_data_read_length_per_fru_id():
    fru = FakeFruDevice(FRU_DATA, max_length=28)
    fru.read_fru_data(offset=0, count=60, fru_id=0)
    fru.max_length = 32
    fru.requests = []
    fru.read_fru_data(offset=0, count=60, fru_id=1)
    assert fru.requests == [(0, 32), (32, 28)]


def test_read_fru_data_read_length_exhausted():
    fru = FakeFruDevice(FRU_DATA, max_length=0)
    with pytest.raises(CompletionCodeError):
        fru.read_fru_data(offset=0, count=8)


def test_read_fru_data_other_error():
    fru = FakeFruDevice(FRU_DATA, max_length=0, cc=constants.CC_TIMEOUT)
    with pytest.raises(CompletionCodeError):
        fru.read_fru_data(offset=0, count=8)
    assert fru.requests == [(0, 8)]


FRU_BIN_DIR = os.path.join(os.path.dirname(__file__), 'fru_bin')
FRUGY_DIR = os.path.join(FRU_BIN_DIR, 'frugy')

# FRU data that does not conform to the specification
NON_CONFORMING = ('frugy/opalkelly_default.bin',
                  'frugy/opalkelly_default_2k.bin')


def _fru_bin_files():
    """Return the paths of the FRU data files relative to FRU_BIN_DIR."""
    paths = []
    for root, _, files in os.walk(FRU_BIN_DIR):
        for name in files:
            if name.endswith('.bin'):
                paths.append(os.path.relpath(os.path.join(root, name),
                                             FRU_BIN_DIR))
    return sorted(paths)


@pytest.mark.parametrize('filename', [f for f in _fru_bin_files()
                                      if f not in NON_CONFORMING])
def test_get_fru_inventory(filename):
    path = os.path.join(FRU_BIN_DIR, filename)
    with open(path, 'rb') as f:
        fru = FakeFruDevice(f.read())
    inventory = fru.get_fru_inventory(fru_id=1)
    expected = get_fru_inventory_from_file(path)
    if expected.multirecord_area is None:
        assert inventory.multirecord_area is None
    else:
        assert ([bytes(r.raw) for r in inventory.multirecord_area.records]
                == [bytes(r.raw) for r in expected.multirecord_area.records])
    if expected.internal_use_area is None:
        assert inventory.internal_use_area is None
    else:
        assert (inventory.internal_use_area.internal_use_data
                == expected.internal_use_area.internal_use_data)
    for area in ('chassis_info_area', 'board_info_area', 'product_info_area'):
        if getattr(expected, area) is None:
            assert getattr(inventory, area) is None
        else:
            # the area from file contains all data up to the end of the file
            data = bytes(getattr(inventory, area).data)
            assert data == bytes(getattr(expected, area).data)[:len(data)]
            assert data
    # the common header is read only once
    assert fru.requests.count((0, 8)) == 1
    assert fru.fru_ids == {1}


def test_get_fru_inventory_requests():
    path = os.path.join(FRU_BIN_DIR, 'supermicro_A2SDi-4C-HLN4F.bin')
    with open(path, 'rb') as f:
        fru = FakeFruDevice(f.read())
    fru.get_fru_inventory()
    assert fru.requests == [
        (0, 8),                         # common header
        (8, 8),                         # chassis area, up to the board area
        (16, 32), (48, 24),             # board area, up to the product area
        (72, 8), (80, 32), (112, 32), (144, 8),  # product area (last one)
    ]


def _truncated_fru_data():
    """FRU data like on the Asus ASMB5-iKVM (issue #187).

    The product info area at offset 0x60 declares 80 bytes, but the FRU data
    ends at 0x70.
    """
    path = os.path.join(FRU_BIN_DIR, 'supermicro_A2SDi-4C-HLN4F.bin')
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    header = InventoryCommonHeader(data[:8])
    offset = header.product_info_area_offset
    return bytes(data[:offset + 16]), offset


def test_get_fru_inventory_area_exceeds_fru_size():
    data, offset = _truncated_fru_data()
    fru = FakeFruDevice(data)
    with pytest.raises(DecodingError,
                       match=f'product info area at offset 0x{offset:x} '
                             f'with .* bytes exceeds the FRU size of '
                             f'{len(data)} bytes'):
        fru.get_fru_inventory()
    # nothing is read beyond the end of the FRU data
    assert all(o + c <= len(data) for o, c in fru.requests)
    # and the read length is not reduced
    assert fru._fru_read_lengths[0].length == 32


def test_get_fru_area_exceeds_fru_size():
    data, offset = _truncated_fru_data()
    fru = FakeFruDevice(data)
    # the areas before the broken one can still be read
    header = fru.get_fru_inventory_header()
    assert header.fru_size == len(data)
    fru.get_fru_chassis_area(header=header)
    fru.get_fru_board_area(header=header)
    with pytest.raises(DecodingError):
        fru.get_fru_product_area(header=header)


def test_get_fru_inventory_area_starts_beyond_fru_size():
    data, offset = _truncated_fru_data()
    fru = FakeFruDevice(data, fru_size=offset + 4)
    with pytest.raises(DecodingError, match='product info area'):
        fru.get_fru_product_area()
    assert all(o + c <= offset + 4 for o, c in fru.requests)


def test_get_fru_inventory_without_area_info():
    # devices that do not support Get FRU Inventory Area Info are read
    # without the size check
    path = os.path.join(FRU_BIN_DIR, 'supermicro_A2SDi-4C-HLN4F.bin')
    with open(path, 'rb') as f:
        fru = FakeFruDevice(f.read(), area_info_cc=constants.CC_INV_CMD)
    header = fru.get_fru_inventory_header()
    assert header.fru_size is None
    fru.get_fru_inventory()


@pytest.mark.parametrize('method', [
    'get_fru_internal_use_area', 'get_fru_chassis_area', 'get_fru_board_area',
    'get_fru_product_area', 'get_fru_multirecord_area',
])
def test_get_fru_area_not_present(method):
    # common header without any area
    fru = FakeFruDevice(b'\x01\x00\x00\x00\x00\x00\x00\xff')
    with pytest.raises(DataNotFound):
        getattr(fru, method)()
    assert fru.requests == [(0, 8)]


def test_multirecord_picmg_manufacturer_id():
    fru_file = os.path.join(this_file_path, 'fru_bin/kontron_am4010.bin')
    record = get_fru_inventory_from_file(fru_file).multirecord_area.records[0]
    assert isinstance(record, FruPicmgRecord)
    assert record.manufacturer_id == 0x315a
    assert record.manufacturer_name == 'PICMG'
    assert str(record).startswith(
        'c0 (OEM, manufacturer ID 12634 = PICMG): 5a 31 00')


def _multirecord(record_type, data):
    """Return a multirecord, the last one of the area, with checksums."""
    header = [record_type, 0x82, len(data), -sum(data) & 0xff]
    return bytes(header + [-sum(header) & 0xff] + list(data))


def test_multirecord_not_oem():
    # an extended compatibility record (type 0x05) is no OEM record
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0x05, b'\x01\x02\x03'))
    assert record.manufacturer_id is None
    assert record.manufacturer_name is None
    assert str(record) == '05: 01 02 03'


def test_multirecord_oem_too_short():
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0xd0, b'\x0b\x00'))
    assert record.manufacturer_id is None
    assert str(record) == 'd0: 0b 00'


def test_multirecord_type_oem():
    assert FruDataMultiRecord.TYPE_OEM == list(range(0xc0, 0x100))


def test_fru_inventory_from_missing_file(tmp_path, capsys):
    with pytest.raises(FileNotFoundError):
        get_fru_inventory_from_file(str(tmp_path / 'missing.bin'))
    # the error is raised, not printed
    assert capsys.readouterr().out == ''


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0,
                    reason='needs file permissions')
def test_fru_inventory_from_unreadable_file(tmp_path):
    fru_file = tmp_path / 'fru.bin'
    fru_file.write_bytes(b'\x01\x00\x00\x01\x00\x00\x00\xfe')
    fru_file.chmod(0)
    with pytest.raises(PermissionError):
        get_fru_inventory_from_file(str(fru_file))


def test_internal_use_area_from_file():
    path = os.path.join(FRU_BIN_DIR, 'HP_ProLiant_BL460c_Gen8.bin')
    with open(path, 'rb') as f:
        raw = f.read()
    area = get_fru_inventory_from_file(path).internal_use_area
    assert area.format_version == 1
    # the area ends at the chassis info area at offset 24
    assert area.internal_use_data == raw[9:24]


def test_internal_use_area_erased():
    # the internal use area of this FRU is erased (0xff), it is decoded
    path = os.path.join(FRU_BIN_DIR, 'kontron_am4904.bin')
    area = get_fru_inventory_from_file(path).internal_use_area
    assert area.format_version == 0x0f
    assert area.internal_use_data == b'\xff' * 255


# common header with only an internal use area at offset 8 and its data up
# to the end of the FRU data
INTERNAL_USE_ONLY = (b'\x01\x01\x00\x00\x00\x00\x00\xfe' + b'\x01'
                     + bytes(range(1, 24)))


def test_internal_use_area_last_area_from_file():
    inventory = FruInventory(INTERNAL_USE_ONLY)
    assert inventory.internal_use_area.internal_use_data == bytes(range(1, 24))


def test_get_fru_internal_use_area():
    path = os.path.join(FRU_BIN_DIR, 'HP_ProLiant_BL460c_Gen8.bin')
    with open(path, 'rb') as f:
        raw = f.read()
    fru = FakeFruDevice(raw)
    area = fru.get_fru_internal_use_area()
    assert area.internal_use_data == raw[9:24]
    # read up to the next area
    assert fru.requests == [(0, 8), (8, 16)]


def test_get_fru_internal_use_area_last_area():
    fru = FakeFruDevice(INTERNAL_USE_ONLY)
    area = fru.get_fru_internal_use_area()
    assert area.internal_use_data == bytes(range(1, 24))
    # read up to the end of the FRU data
    assert fru.requests == [(0, 8), (8, 24)]


def _fru_image(multirecords, after=b''):
    """Return FRU data with a multirecord area at offset 8.

    `after` is an area that follows the multirecord area, e.g. a board info
    area, the header points to it if it is given.
    """
    multirecord_area = b''.join(multirecords)
    following = 8 + len(multirecord_area)
    board_offset = following // 8 if after else 0
    header = [1, 0, 0, board_offset, 0, 1, 0]
    header.append(-sum(header) & 0xff)
    return bytes(header) + multirecord_area + after


def _record(data, end_of_list=False):
    """Return an extended compatibility multirecord with valid checksums."""
    header = [0x05, 0x82 if end_of_list else 0x02, len(data), -sum(data) & 0xff]
    return bytes(header + [-sum(header) & 0xff]) + bytes(data)


# a board info area of 16 bytes: format 1, length 2, language, date, five
# empty fields (0xc0), the end marker 0xc1, padding and the checksum
_BOARD = [1, 2, 0, 0, 0, 0, 0xc0, 0xc0, 0xc0, 0xc0, 0xc0, 0xc1, 0, 0, 0]
BOARD_AREA = bytes(_BOARD + [-sum(_BOARD) & 0xff])


def test_multirecord_area_without_end_of_list():
    # two records without the end of list flag, followed by the board area
    data = _fru_image([_record([1, 2, 3]), _record([4, 5, 6])], BOARD_AREA)
    inventory = FruInventory(data)
    assert [bytes(r.raw) for r in inventory.multirecord_area.records] \
        == [b'\x01\x02\x03', b'\x04\x05\x06']
    assert inventory.board_info_area is not None


def test_get_fru_multirecord_area_without_end_of_list():
    data = _fru_image([_record([1, 2, 3]), _record([4, 5, 6])], BOARD_AREA)
    fru = FakeFruDevice(data)
    area = fru.get_fru_multirecord_area()
    assert len(area.records) == 2
    # nothing is read beyond the multirecord area at 8 - 24
    assert all(o + c <= 24 for o, c in fru.requests[1:])


def test_multirecord_area_record_exceeds_data():
    # the last record declares 8 bytes, but only 3 follow
    record = _record([1, 2, 3], end_of_list=True)
    record = record[:2] + b'\x08' + record[3:4] \
        + bytes([-(sum(record[:2]) + 8 + record[3]) & 0xff]) + record[5:]
    data = _fru_image([record])
    with pytest.raises(DecodingError):
        FruInventory(data)
    with pytest.raises(DecodingError):
        FruInventory(data, ignore_checksum=True)


@pytest.mark.parametrize('filename, area, manufacturer, name, serial_number', [
    ('ADRV9375-N.bin', 'board_info_area', 'Analog Devices',
     'Narrow Tuning Range AD9375 Eval', '0000'),
    ('caen-fmc-pico-1m4.bin', 'board_info_area', 'CAEN ELS s.r.l.',
     'FMC-Pico-1M4', '20160173'),
    ('damc-fmc2zup.bin', 'board_info_area', 'DESY/CAEN ELS',
     'DAMC-FMC2ZUP-11EG', '21Y01W0000'),
    ('damc-fmc2zup.bin', 'product_info_area', 'DESY/CAEN ELS',
     'DAMC-FMC2ZUP-11EG', '21Y01W0000'),
    ('drtm-rtm-evalkit.bin', 'product_info_area', 'TUL/DESY',
     'DRTM-RTM-EvalKit', 'N/A'),
    ('xilinx_vhk158.bin', 'board_info_area', 'XILINX', 'VEK385',
     '519101A01220'),
])
def test_frugy_info_areas(filename, area, manufacturer, name, serial_number):
    # the expected values are from the frugy examples the files were
    # generated from
    inventory = get_fru_inventory_from_file(os.path.join(FRUGY_DIR, filename))
    info = getattr(inventory, area)
    name_field = info.product_name if area == 'board_info_area' else info.name
    assert (info.manufacturer.string, name_field.string,
            info.serial_number.string) == (manufacturer, name, serial_number)


def test_frugy_internal_use_area():
    inventory = get_fru_inventory_from_file(
        os.path.join(FRUGY_DIR, 'caen-fmc-pico-1m4.bin'))
    area = inventory.internal_use_area
    assert area.format_version == 1
    assert area.internal_use_data == bytes.fromhex(
        '50 00 00 00 50 e1 e2 ca c0 71 2c f2 a5 16 0a 31 c0 cf 29 b3 eb 11 0a '
        '31 8f f0 f2 30 ba 12 0a 31 29 ce 84 32 93 14 0a 31 a9 82 4a 32 2a 56 '
        '0d 2c c2 fb 24 ae a8 4c 0d 2c 0b 8c 85 2c e0 47 0d 2c 95 be 9a 2d 63 '
        '4b 0d 2c 3e 45 68 2d 0c 5b 98 5e 02 02 00 00')


@pytest.mark.parametrize('filename, records', [
    # DC load/output records and the FMC record of VITA (0x0012a2)
    ('ADRV9375-N.bin', [(0x01, None)] * 3 + [(0x02, None)] * 3
     + [(0xfa, 0x0012a2)] * 2),
    # PICMG records (0x00315a)
    ('damc-fmc2zup.bin', [(0xc0, 0x00315a)] * 3),
    # Xilinx OEM records (0x0010da)
    ('xilinx_vhk158.bin', [(0xd2, 0x0010da), (0xd2, 0x0010da),
                           (0xd3, 0x0010da)]),
])
def test_frugy_multirecords(filename, records):
    inventory = get_fru_inventory_from_file(os.path.join(FRUGY_DIR, filename))
    assert [(r.record_type_id, r.manufacturer_id)
            for r in inventory.multirecord_area.records] == records


@pytest.mark.parametrize('filename', ['opalkelly_default.bin',
                                      'opalkelly_default_2k.bin'])
def test_opalkelly_non_conforming(filename):
    path = os.path.join(FRUGY_DIR, filename)
    # the multirecords have no end of list flag, the list ends with records
    # with wrong checksums
    with pytest.raises(DecodingError, match='checksum'):
        get_fru_inventory_from_file(path)

    inventory = get_fru_inventory_from_file(path, ignore_checksum=True)
    assert inventory.board_info_area.manufacturer.string \
        == 'Opal Kelly Incorporated'
    # DC load, DC output and the FMC record
    assert [r.record_type_id for r in inventory.multirecord_area.records[:7]] \
        == [0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0xfa]


def test_opalkelly_multirecords_end_at_next_area():
    # the multirecord area at offset 8 is followed by the board area at 144
    inventory = get_fru_inventory_from_file(
        os.path.join(FRUGY_DIR, 'opalkelly_default_2k.bin'),
        ignore_checksum=True)
    records = inventory.multirecord_area.records
    assert sum(r.length + 5 for r in records) == 144 - 8


def _frugy_records(filename):
    path = os.path.join(FRUGY_DIR, filename)
    return get_fru_inventory_from_file(path).multirecord_area.records


def test_dc_output_records():
    records = [r for r in _frugy_records('ADRV9375-N.bin')
               if isinstance(r, FruDcOutputRecord)]
    # P1_VIO_B_M2C, P1_VREF_A_M2C and P1_VREF_B_M2C
    assert [r.output_number for r in records] == [3, 4, 5]
    record = records[0]
    assert record.standby_enable is False
    assert record.nominal_voltage == 2500
    assert (record.max_negative_voltage, record.max_positive_voltage) == (0, 0)
    assert record.ripple_and_noise == 50
    assert (record.min_current_draw, record.max_current_draw) == (0, 0)
    assert str(record) == ('01 DC Output 3: 2500 mV (0 - 0 mV), ripple and '
                           'noise 50 mV, 0 - 0 mA')


def test_dc_load_records():
    records = [r for r in _frugy_records('ADRV9375-N.bin')
               if isinstance(r, FruDcLoadRecord)]
    # P1_VADJ, P1_3P3V and P1_12P0V
    assert [(r.output_number, r.nominal_voltage, r.min_voltage, r.max_voltage,
             r.ripple_and_noise, r.min_current_load, r.max_current_load)
            for r in records] == [
        (0, 2500, 1800, 2500, 50, 0, 1000),
        (1, 3300, 2970, 3630, 0, 0, 500),
        (2, 12000, 10800, 13200, 6, 500, 1000),
    ]
    assert str(records[2]) == ('02 DC Load 2: 12000 mV (10800 - 13200 mV), '
                               'ripple and noise 6 mV, 500 - 1000 mA')


def test_fmc_main_definition():
    records = _frugy_records('ADRV9375-N.bin')
    record = records[6]
    assert isinstance(record, FruFmcMainDefinition)
    assert (record.manufacturer_id, record.subtype) == (0x0012a2, 0)
    assert record.module_size == FruFmcRecord.MODULE_SIZE_SINGLE_WIDTH
    assert record.p1_connector_size == FruFmcRecord.CONNECTOR_HPC
    assert record.p2_connector_size == FruFmcMainDefinition.CONNECTOR_NOT_FITTED
    assert record.clock_direction == FruFmcRecord.CLOCK_DIRECTION_M2C
    assert (record.p1_a_num_signals, record.p1_b_num_signals,
            record.p2_a_num_signals, record.p2_b_num_signals) == (26, 0, 0, 0)
    assert (record.p1_gbt_num_trcv, record.p2_gbt_num_trcv) == (4, 0)
    assert record.tck_max_clock == 0
    assert str(record) == ('fa (OEM, manufacturer ID 4770 = VITA) FMC Main '
                           'Definition: single width, P1 HPC, P2 not fitted, '
                           'clock M2C, P1 26/0 signals, P2 0/0 signals, '
                           'P1 4 GBT, P2 0 GBT, TCK 0 MHz')


def test_fmc_i2c_device_definition():
    record = _frugy_records('ADRV9375-N.bin')[7]
    assert isinstance(record, FruFmcI2cDeviceDefinition)
    assert record.subtype == 0x10
    assert record.devices == [('AD7291', [1])]
    assert str(record) == ('fa (OEM, manufacturer ID 4770 = VITA) FMC I2C '
                           'Devices: AD7291 (1)')


def test_fmc_plus_main_definition():
    record = _frugy_records('fmc+_loopback.bin')[-1]
    assert isinstance(record, FruFmcPlusMainDefinition)
    assert record.subtype == 1
    assert record.module_size == FruFmcRecord.MODULE_SIZE_SINGLE_WIDTH
    assert record.p1_p3_connector_size == FruFmcRecord.CONNECTOR_HSPC
    assert record.p2_p4_connector_size == \
        FruFmcPlusMainDefinition.CONNECTOR_NOT_FITTED
    assert record.clock_direction == FruFmcRecord.CLOCK_DIRECTION_M2C
    assert (record.p1_a_num_signals, record.p1_b_num_signals,
            record.p2_a_num_signals, record.p2_b_num_signals) == (112, 48, 0, 0)
    assert (record.p1_gbt_num_trcv, record.p2_gbt_num_trcv) == (24, 0)
    assert record.tck_max_clock == 128


def _oem_record(record_type, data):
    """Return a multirecord, the last one of the area, with checksums."""
    header = [record_type, 0x82, len(data), -sum(data) & 0xff]
    return bytes(header + [-sum(header) & 0xff] + list(data))


def test_dc_output_negative_voltage():
    # -12 V (0xfb50 in 10 mV units), -10.8 V (0xfbc8) and -13.2 V (0xfad8)
    # on output 1, standby enabled
    data = [0x81, 0x50, 0xfb, 0xc8, 0xfb, 0xd8, 0xfa, 0x64, 0x00,
            0x00, 0x00, 0xe8, 0x03]
    record = FruDataMultiRecord.create_from_record_id(_oem_record(0x01, data))
    assert record.standby_enable is True
    assert record.output_number == 1
    assert record.nominal_voltage == -12000
    assert (record.max_negative_voltage, record.max_positive_voltage) \
        == (-10800, -13200)


@pytest.mark.parametrize('record_type', [0x01, 0x02])
def test_dc_record_too_short(record_type):
    with pytest.raises(DecodingError, match='too short'):
        FruDataMultiRecord.create_from_record_id(
            _oem_record(record_type, bytes(12)))


def test_fmc_unknown_subtype():
    record = FruDataMultiRecord.create_from_record_id(
        _oem_record(0xfa, b'\xa2\x12\x00\x20\x01\x02'))
    assert type(record) is FruFmcRecord
    assert record.subtype == 0x20


def test_fmc_record_without_vita_id():
    # an Opal Kelly FMC record has no manufacturer ID, it is not decoded
    record = FruDataMultiRecord.create_from_record_id(
        _oem_record(0xfa, b'\x0c\x15\x00\x00\x00\x00\x0a\x00'))
    assert type(record) is FruDataUnknown


def test_multirecord_unknown_manufacturer():
    # an OEM record of a manufacturer that is not well known
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0xd0, b'\x39\x30\x00\x01'))
    assert record.manufacturer_id == 12345
    assert record.manufacturer_name is None
    assert str(record) == 'd0 (OEM, manufacturer ID 12345): 39 30 00 01'


def _board_area(fields):
    """Return a board info area with the given fields after the date."""
    data = [1, 0, 0, 0, 0, 0] + list(fields)
    data += [0] * (-(len(data) + 1) % 8)
    data[1] = (len(data) + 1) // 8
    return bytes(data + [-sum(data) & 0xff])


def test_board_area_without_end_marker():
    # five empty fields and a custom field, but no end marker 0xc1
    area = _board_area([0xc0] * 5 + [0xc2, 0x41, 0x42])
    with pytest.raises(DecodingError):
        InventoryBoardInfoArea(area)
    with pytest.raises(DecodingError):
        InventoryBoardInfoArea(area, ignore_checksum=True)


def test_board_area_custom_field_exceeds_area():
    # the custom field declares 20 bytes, more than the area has
    area = _board_area([0xc0] * 5 + [0xd4, 0x41, 0x42])
    with pytest.raises(DecodingError):
        InventoryBoardInfoArea(area)


def test_board_area_custom_fields():
    area = _board_area([0xc0] * 5 + [0xc2, 0x41, 0x42, 0xc2, 0x43, 0x44,
                                     0xc1])
    fields = InventoryBoardInfoArea(area).custom_mfg_info
    assert [f.string for f in fields] == ['AB', 'CD']


def test_multirecord_oem_c0_not_picmg():
    # an OEM record of type 0xc0 of another manufacturer, only with its
    # manufacturer ID
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0xc0, b'\x98\x3a\x00'))
    assert type(record) is FruDataUnknown
    assert record.manufacturer_id == 0x3a98

    # longer, with bytes that look like a PICMG record type ID
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0xc0, b'\x98\x3a\x00\x16\x00\x01\x02'))
    assert type(record) is FruDataUnknown


def test_multirecord_picmg_too_short():
    # a record with the PICMG manufacturer ID, but without the record type
    # ID and the format version, is not decoded as PICMG record
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0xc0, b'\x5a\x31\x00\x27'))
    assert type(record) is FruDataUnknown
    assert record.manufacturer_id == 0x315a


def test_multirecord_picmg_power_module_followed_by_record():
    # the power module capability record (0x27) needs the 2 bytes of the
    # maximum current, they must not be taken from the next record
    picmg = _multirecord(0xc0, b'\x5a\x31\x00\x27\x00')
    data = picmg[:1] + b'\x02' + picmg[2:4] \
        + bytes([-(picmg[0] + 0x02 + picmg[2] + picmg[3]) & 0xff]) \
        + picmg[5:] + _multirecord(0x05, b'\x01\x02\x03')
    with pytest.raises(DecodingError):
        FruDataMultiRecord.create_from_record_id(data)


def test_multirecord_area_with_oem_c0_record():
    # the area is decoded although it has a non PICMG 0xc0 record
    oem = _record([0x98, 0x3a, 0x00])
    oem = bytes([0xc0]) + oem[1:4] + bytes([-(0xc0 + sum(oem[1:4])) & 0xff]) \
        + oem[5:]
    data = _fru_image([oem, _record([1, 2, 3], end_of_list=True)])
    records = FruInventory(data).multirecord_area.records
    assert [type(r) for r in records] == [FruDataUnknown, FruDataUnknown]
    assert records[0].manufacturer_id == 0x3a98
