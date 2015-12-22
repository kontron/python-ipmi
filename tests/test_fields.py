#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from nose.tools import eq_, raises

from pyipmi.fields import *

class TestFields:
    def test_VersionField(self):
        v = VersionField([1, 0x99])
        eq_(v.major, 1)
        eq_(v.minor, 99)

        v = VersionField('\x00\x99')
        eq_(v.major, 0)
        eq_(v.minor, 99)

    def test_VersionField_invalid(self):
        v = VersionField('\x00\xff')
        eq_(v.major, 0)
        eq_(v.minor, 255)

    @raises(DecodingError)
    def test_VersionField_decoding_error(self):
        v = VersionField('\x00\x9a')
        eq_(v.major, 0)
        eq_(v.minor, 99)
