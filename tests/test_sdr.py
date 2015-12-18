#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from mock import MagicMock, call
from nose.tools import eq_, raises

from pyipmi.sdr import *

class TestSdr:

    @raises(DecodingError)
    def test_SdrCommon_invalid_data_length(self):
        data = (0x00, 0x01, 0x02, 0x03)
        sdr = SdrCommon(data)

    def test_SdrCommon(self):
        data = (0x00, 0x01, 0x02, 0x03, 0x04)
        sdr = SdrCommon(data)
        eq_(sdr.id, 0x0100)
        eq_(sdr.version, 0x02)
        eq_(sdr.type, 0x03)
        eq_(sdr.length, 0x04)

    @raises(DecodingError)
    def test_SdrFullSensorRecord_invalid_length(self):
        data = (0, 0, 0, 0, 0)
        sdr = SdrFullSensorRecord(data)

    @raises(DecodingError)
    def test_SdrCompactSensorRecord(self):
        data = (0, 0, 0, 0, 0)
        sdr = SdrCompactSensorRecord(data)

    @raises(DecodingError)
    def test_SdrEventOnlySensorRecord(self):
        data = (0, 0, 0, 0, 0)
        sdr = SdrEventOnlySensorRecord(data)

    @raises(DecodingError)
    def test_SdrFruDeviceLocator(self):
        data = (0, 0, 0, 0, 0)
        sdr = SdrFruDeviceLocator(data)

    @raises(DecodingError)
    def test_SdrManagementContollerDeviceLocator(self):
        data = (0, 0, 0, 0, 0)
        sdr = SdrManagementContollerDeviceLocator(data)
