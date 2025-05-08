#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pytest

from pyipmi.errors import (DecodingError)

from pyipmi.fru import (FruData, FruInventory,
                        FruPicmgPowerModuleCapabilityRecord,
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
