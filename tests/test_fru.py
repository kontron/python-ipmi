#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_

from pyipmi.fru import *

def test_frudata_object():
    fruField = FruData((0,1,2,3))
    eq_(fruField.data[0], 0)
    eq_(fruField.data[1], 1)
    eq_(fruField.data[2], 2)
    eq_(fruField.data[3], 3)

    fruField = FruData('\x00\x01\x02\x03')
    eq_(fruField.data[0], 0)
    eq_(fruField.data[1], 1)
    eq_(fruField.data[2], 2)
    eq_(fruField.data[3], 3)

def test_inventorycommonheader_object():
    h = InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 235))
