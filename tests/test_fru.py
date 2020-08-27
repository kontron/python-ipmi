#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import nose
from nose.tools import eq_

from pyipmi.fru import (FruData, InventoryCommonHeader,
                        get_fru_inventory_from_file)


def test_frudata_object():
    fru_field = FruData((0, 1, 2, 3))
    eq_(fru_field.data[0], 0)
    eq_(fru_field.data[1], 1)
    eq_(fru_field.data[2], 2)
    eq_(fru_field.data[3], 3)

    fru_field = FruData('\x00\x01\x02\x03')
    eq_(fru_field.data[0], 0)
    eq_(fru_field.data[1], 1)
    eq_(fru_field.data[2], 2)
    eq_(fru_field.data[3], 3)


def test_commonheader_object():
    InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 235))


def test_fru_inventory_from_file():
    path = os.path.dirname(os.path.abspath(__file__))
    fru_file = os.path.join(path, 'fru_bin/kontron_am4010.bin')
    if not os.path.isfile(fru_file):
        raise nose.SkipTest("FRU file '%s' is missing." % (fru_file))
    fru = get_fru_inventory_from_file(fru_file)
    eq_(fru.chassis_info_area, None)


def test_board_area():
    path = os.path.dirname(os.path.abspath(__file__))
    fru_file = os.path.join(path, 'fru_bin/kontron_am4010.bin')
    if not os.path.isfile(fru_file):
        raise nose.SkipTest("FRU file '%s' is missing." % (fru_file))
    fru = get_fru_inventory_from_file(fru_file)

    board_area = fru.board_info_area
    eq_(board_area.manufacturer.value, 'Kontron')
    eq_(board_area.product_name.value, 'AM4010')
    eq_(board_area.serial_number.value, '0023721003')
    eq_(board_area.part_number.value, '35943')


def test_product_area():
    path = os.path.dirname(os.path.abspath(__file__))
    fru_file = os.path.join(path, 'fru_bin/kontron_am4010.bin')
    if not os.path.isfile(fru_file):
        raise nose.SkipTest("FRU file '%s' is missing." % (fru_file))
    fru = get_fru_inventory_from_file(fru_file)

    product_area = fru.product_info_area
    eq_(product_area.manufacturer.value, 'Kontron')
    eq_(product_area.name.value, 'AM4010')
    eq_(product_area.serial_number.value, '0000000000000000000000000')
    eq_(product_area.part_number.value, '0012')
