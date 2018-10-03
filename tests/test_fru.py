#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_

from pyipmi.fru import FruData, InventoryCommonHeader


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


def test_inventorycommonheader_object():
    InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 235))
