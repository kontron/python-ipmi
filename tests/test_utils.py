#!/usr/bin/env python
#-*- coding: utf-8 -*-

import array
from nose.tools import eq_, raises

from pyipmi.utils import *

def test_bytebuffer_init_from_list():
    b = ByteBuffer([0xf8])
    eq_(b.array, array('B', [0xf8]))

def test_bytebuffer_init_from_tuple():
    b = ByteBuffer((0xf8,))
    eq_(b.array, array('B', [0xf8]))

def test_bytebuffer_initi_fromstring():
    b = ByteBuffer(b'\xf8')
    eq_(b.array, array('B', [0xf8]))

def test_bytebuffer_push_unsigned_int():
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

def test_bytebuffer_pop_unsigned_int():
    b = ByteBuffer((1, 0, 0, 0))
    eq_(b.pop_unsigned_int(1), 1)

    b = ByteBuffer((0, 1, 0, 0))
    eq_(b.pop_unsigned_int(2), 0x100)

    b = ByteBuffer((0, 0, 1, 0))
    eq_(b.pop_unsigned_int(3), 0x10000)

    b = ByteBuffer((0, 0, 0, 1))
    eq_(b.pop_unsigned_int(4), 0x1000000)

@raises(DecodingError)
def test_bytebuffer_pop_unsigned_int_error():
    b = ByteBuffer((0, 0))
    b.pop_unsigned_int(3)

def test_bytebuffer_push_string():
    b = ByteBuffer()
    b.push_string('0123')
    eq_(b[0], 0x30)
    eq_(b[1], 0x31)
    eq_(b[2], 0x32)
    eq_(b[3], 0x33)
    eq_(b.tostring(), '0123')

    b = ByteBuffer()
    b.push_string( b'\x00\xb4')
    eq_(b.tostring(), '\x00\xb4')

def test_bytebuffer_pop_string():
    b = ByteBuffer( b'\x30\x31\x32\x33')
    eq_(b.pop_string(2), '01')
    eq_(b.tostring(), '23')

def test_bytebuffer_tostring():
    b = ByteBuffer('\x30\x31\x32\x33')
    eq_(b.tostring(), '0123')

def test_bytebuffer_pop_slice():
    b = ByteBuffer(b'\x30\x31\x32\x33')
    c = b.pop_slice(1)
    eq_(b.tostring(), '123')
    eq_(c.tostring(), '0')

    b = ByteBuffer(b'\x30\x31\x32\x33')
    c = b.pop_slice(2)
    eq_(b.tostring(), '23')
    eq_(c.tostring(), '01')

    b = ByteBuffer(b'\x30\x31\x32\x33')
    c = b.pop_slice(3)
    eq_(b.tostring(), '3')
    eq_(c.tostring(), '012')

    b = ByteBuffer(b'\x30\x31\x32\x33')
    c = b.pop_slice(4)
    eq_(b.tostring(), '')
    eq_(c.tostring(), '0123')

@raises(DecodingError)
def test_bytebuffer_pop_slice_error():
    b = ByteBuffer(b'\x30\x31\x32\x33')
    c = b.pop_slice(5)

def test_chunks():
    d = [0,1,2,3,4,5,6,7,8,9]
    r = list()
    for c in chunks(d, 2):
       r.extend(c)
       eq_(len(c), 2)
    eq_(r,  [0,1,2,3,4,5,6,7,8,9])
