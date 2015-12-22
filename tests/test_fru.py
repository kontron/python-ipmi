#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from nose.tools import eq_, raises

from pyipmi.fru import *

class TestFru:
    def test_FruData(self):
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

    def test_InventoryCommonHeader(self):
        h = InventoryCommonHeader((0, 1, 2, 3, 4, 5, 6, 235))
