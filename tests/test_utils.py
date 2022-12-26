#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from array import array

from pyipmi.utils import ByteBuffer, chunks
from pyipmi.errors import DecodingError


def test_bytebuffer_init_from_list():
    buf = ByteBuffer([0xf8])
    assert buf.array == array('B', [0xf8])


def test_bytebuffer_init_from_tuple():
    buf = ByteBuffer((0xf8,))
    assert buf.array == array('B', [0xf8])


def test_bytebuffer_initi_fromstring():
    buf = ByteBuffer(b'\xf8')
    assert buf.array == array('B', [0xf8])


def test_bytebuffer_push_unsigned_int():
    buf = ByteBuffer((1, 0))
    buf.push_unsigned_int(255, 1)
    assert buf[0] == 1
    assert buf[1] == 0
    assert buf[2] == 255
    buf.push_unsigned_int(255, 2)
    assert buf[3] == 255
    assert buf[4] == 0
    buf.push_unsigned_int(256, 2)
    assert buf[5] == 0
    assert buf[6] == 1


def test_bytebuffer_pop_unsigned_int():
    buf = ByteBuffer((1, 0, 0, 0))
    assert buf.pop_unsigned_int(1) == 1

    buf = ByteBuffer((0, 1, 0, 0))
    assert buf.pop_unsigned_int(2) == 0x100

    buf = ByteBuffer((0, 0, 1, 0))
    assert buf.pop_unsigned_int(3) == 0x10000

    buf = ByteBuffer((0, 0, 0, 1))
    assert buf.pop_unsigned_int(4) == 0x1000000


def test_bytebuffer_pop_unsigned_int_error():
    with pytest.raises(DecodingError):
        buf = ByteBuffer((0, 0))
        buf.pop_unsigned_int(3)


def test_bytebuffer_push_string():
    buf = ByteBuffer()
    buf.push_string(b'0123')
    assert buf[0] == 0x30
    assert buf[1] == 0x31
    assert buf[2] == 0x32
    assert buf[3] == 0x33
    assert buf.tostring() == b'0123'

    buf = ByteBuffer()
    buf.push_string(b'\x00\xb4')
    assert buf.tostring() == b'\x00\xb4'


def test_bytebuffer_pop_string():
    buf = ByteBuffer(b'\x30\x31\x32\x33')
    assert buf.pop_string(2) == b'01'
    assert buf.tostring() == b'23'


def test_bytebuffer_tostring():
    buf = ByteBuffer(b'\x30\x31\x32\x33')
    assert buf.tostring() == b'0123'


def test_bytebuffer_pop_slice():
    buf = ByteBuffer(b'\x30\x31\x32\x33')
    cut = buf.pop_slice(1)
    assert buf.tostring() == b'123'
    assert cut.tostring() == b'0'

    buf = ByteBuffer(b'\x30\x31\x32\x33')
    cut = buf.pop_slice(2)
    assert buf.tostring() == b'23'
    assert cut.tostring() == b'01'

    buf = ByteBuffer(b'\x30\x31\x32\x33')
    cut = buf.pop_slice(3)
    assert buf.tostring() == b'3'
    assert cut.tostring() == b'012'

    buf = ByteBuffer(b'\x30\x31\x32\x33')
    cut = buf.pop_slice(4)
    assert buf.tostring() == b''
    assert cut.tostring() == b'0123'


def test_bytebuffer_pop_slice_error():
    with pytest.raises(DecodingError):
        buf = ByteBuffer(b'\x30\x31\x32\x33')
        buf.pop_slice(5)


def test_chunks():
    data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    result = list()
    for chunk in chunks(data, 2):
        result.extend(chunk)
        assert len(chunk) == 2
    assert result == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
