#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, raises

from array import array
from pyipmi.utils import ByteBuffer
from pyipmi.msgs.message import Message, UnsignedInt, RemainingBytes, String

class TestMessage(object):
    def __init__(self, field):
        setattr(self, field.name, field.create())
        self.field = field

    def encode(self):
        data = ByteBuffer()
        self.field.encode(self, data)
        return data

    def decode(self, data):
        data = ByteBuffer(data)
        self.field.decode(self, data)

def test_unsignedint_encode():
    t = TestMessage(UnsignedInt('test', 4))
    t.test = 0x12345678
    byte_buffer = t.encode()
    eq_(byte_buffer.array, array('B', [0x78, 0x56, 0x34, 0x12]))

    t = TestMessage(UnsignedInt('test', 8))
    t.test = 0x12345678
    byte_buffer = t.encode()
    eq_(byte_buffer.array, array('B', [0x78, 0x56, 0x34, 0x12, 0, 0, 0, 0]))

def test_unsignedint_decode():
    t = TestMessage(UnsignedInt('test', 1))
    t.decode('\x12')
    eq_(t.test, 0x12)

    t.decode('\xd7')
    eq_(t.test, 0xd7)

def test_string_encode():
    t = TestMessage(String('test', 10))
    t.test = '1234'
    byte_buffer = t.encode()
    eq_(byte_buffer.array, array('B', [0x31, 0x32, 0x33, 0x34]))

def test_string_decoce():
    t = TestMessage(String('test', 10))
    t.decode('abcdef')
    eq_(t.test, 'abcdef')

def test_remainingbytes_encode():
    t = TestMessage(RemainingBytes('test'))
    t.test = [0xb4, 1]
    byte_buffer = t.encode()
    eq_(byte_buffer.array, array('B', [0xb4, 0x01]))

def test_message():
    msg = Message()
    msg.__netfn__ = 0x1
    msg.__cmdid__ = 0x2

    eq_(msg.lun, 0)
    eq_(msg.netfn, 1)
    eq_(msg.cmdid, 2)
