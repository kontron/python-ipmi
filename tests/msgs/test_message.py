#!/usr/bin/env python
# -*- coding: utf-8 -*-

from array import array
from pyipmi.utils import ByteBuffer
from pyipmi.msgs.message import (Bitfield, Message, UnsignedInt,
                                 RemainingBytes, String)


class TMessage(object):
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


def test_bitfield_encode():
    t = TMessage(Bitfield('status', 1,
                             Bitfield.Bit('erase_in_progress', 4),
                             Bitfield.ReservedBit(4, 0),))
    t.status.erase_in_progress = 1
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x1])


def test_unsignedint_encode():
    t = TMessage(UnsignedInt('test', 4))
    t.test = 0x12345678
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x78, 0x56, 0x34, 0x12])

    t = TMessage(UnsignedInt('test', 8))
    t.test = 0x12345678
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x78, 0x56, 0x34, 0x12, 0, 0, 0, 0])


def test_unsignedint_decode():
    t = TMessage(UnsignedInt('test', 1))
    t.decode(b'\x12')
    assert t.test == 0x12

    t.decode(b'\xd7')
    assert t.test == 0xd7


def test_string_encode():
    t = TMessage(String('test', 10))
    t.test = '1234'
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x31, 0x32, 0x33, 0x34])


def test_string_decode():
    t = TMessage(String('test', 10))
    t.decode(b'abcdef')
    assert t.test == b'abcdef'


def test_remainingbytes_encode():
    t = TMessage(RemainingBytes('test'))
    t.test = [0xb4, 1]
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0xb4, 0x01])


def test_message():
    msg = Message()
    msg.__netfn__ = 0x1
    msg.__cmdid__ = 0x2

    assert msg.lun == 0
    assert msg.netfn == 1
    assert msg.cmdid == 2
