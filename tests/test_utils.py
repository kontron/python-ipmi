#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from mock import MagicMock, call
from nose.tools import eq_, raises

from pyipmi.utils import *

class TestUtils:

    def test_ByteBuffer_push_unsigned_int(self):
        b = ByteBuffer((1, 0))
        b.push_unsigned_int(255, 1)
        eq_(b[0], 1)
        eq_(b[1], 0)
        eq_(b[2], 255)
        b.push_unsigned_int(255, 2)
        eq_(b[3], 255)
        eq_(b[4], 0)
        b.push_unsigned_int(256, 2)
        eq_(b[5], 0)
        eq_(b[6], 1)

    def test_ByteBuffer_pop_unsigned_int(self):
        b = ByteBuffer((1, 0, 0, 0))
        eq_(b.pop_unsigned_int(1), 1)

        b = ByteBuffer((0, 1, 0, 0))
        eq_(b.pop_unsigned_int(2), 256)

        b = ByteBuffer((0, 0, 1, 0))
        eq_(b.pop_unsigned_int(3), 65536)

        b = ByteBuffer((0, 0, 0, 1))
        eq_(b.pop_unsigned_int(4), 16777216)

    @raises(DecodingError)
    def test_ByteBuffer_pop_unsigned_int_error(self):
        b = ByteBuffer((0, 0))
        b.pop_unsigned_int(3)

    def test_ByteBuffer_push_string(self):
        b = ByteBuffer()
        b.push_string('0123')
        eq_(b[0], 0x30)
        eq_(b[1], 0x31)
        eq_(b[2], 0x32)
        eq_(b[3], 0x33)
        eq_(b.tostring(), '0123')

    def test_ByteBuffer_pop_string(self):
        b = ByteBuffer('\x30\x31\x32\x33')
        eq_(b.pop_string(2), '01')
        eq_(b.tostring(), '23')

    def test_ByteBuffer_tostring(self):
        b = ByteBuffer('\x30\x31\x32\x33')
        eq_(b.tostring(), '0123')

    def test_ByteBuffer_pop_slice(self):
        b = ByteBuffer('\x30\x31\x32\x33')
        c = b.pop_slice(1)
        eq_(b.tostring(), '123')
        eq_(c.tostring(), '0')

        b = ByteBuffer('\x30\x31\x32\x33')
        c = b.pop_slice(2)
        eq_(b.tostring(), '23')
        eq_(c.tostring(), '01')

        b = ByteBuffer('\x30\x31\x32\x33')
        c = b.pop_slice(3)
        eq_(b.tostring(), '3')
        eq_(c.tostring(), '012')

        b = ByteBuffer('\x30\x31\x32\x33')
        c = b.pop_slice(4)
        eq_(b.tostring(), '')
        eq_(c.tostring(), '0123')

    @raises(DecodingError)
    def test_ByteBuffer_pop_slice_error(self):
        b = ByteBuffer('\x30\x31\x32\x33')
        c = b.pop_slice(5)
