#!/usr/bin/env python
import datetime
import os
from types import SimpleNamespace

import pytest

from pyipmi.errors import CompletionCodeError, DataNotFound, DecodingError
from pyipmi.msgs import constants

from pyipmi.fru import (Fru, FruData, FruDataMultiRecord, FruInventory,
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
    assert str(records[2]) == 'd0 (OEM, manufacturer ID 11): 0b 00 00 02 0b 00 00'


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

    def send_message_with_name(self, name, fru_id, offset=None, count=None):
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


@pytest.mark.parametrize('filename', sorted(os.listdir(FRU_BIN_DIR)))
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
    'get_fru_chassis_area', 'get_fru_board_area', 'get_fru_product_area',
    'get_fru_multirecord_area',
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
    assert str(record).startswith('c0 (OEM, manufacturer ID 12634): 5a 31 00')


def _multirecord(record_type, data):
    """Return a multirecord, the last one of the area, with checksums."""
    header = [record_type, 0x82, len(data), -sum(data) & 0xff]
    return bytes(header + [-sum(header) & 0xff] + list(data))


def test_multirecord_not_oem():
    # a DC output record (type 0x01) is no OEM record
    record = FruDataMultiRecord.create_from_record_id(
        _multirecord(0x01, b'\x01\x02\x03'))
    assert record.manufacturer_id is None
    assert str(record) == '01: 01 02 03'


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
