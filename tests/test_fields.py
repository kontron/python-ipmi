#!/usr/bin/env python

import pytest

from array import array

from pyipmi.fields import (VersionField, FruTypeLengthString,
                           SdrTypeLengthString)
from pyipmi.errors import DecodingError


def test_versionfield_object():
    version = VersionField([1, 0x99])
    assert version.major == 1
    assert version.minor == 99

    version = VersionField('\x00\x99')
    assert version.major == 0
    assert version.minor == 99


def test_versionfield_invalid():
    version = VersionField('\x00\xff')
    assert version.major == 0
    assert version.minor == 255


def test_versionfield_decoding_error():
    with pytest.raises(DecodingError):
        version = VersionField('\x00\x9a')  # noqa:F841


def test_FruTypeLengthString_6bitascii():
    f = FruTypeLengthString(b'\x83d\xc9\xb2\xde', 0)
    assert f.string == 'DELL'


def pack6bitascii(string):
    """Pack a string in 6-bit ASCII, the first character in the low bits."""
    value = 0
    for (i, c) in enumerate(string):
        value |= (ord(c) - 0x20) << (6 * i)
    length = (len(string) * 6 + 7) // 8
    return value.to_bytes(length, 'little')


@pytest.mark.parametrize('string', [
    'A', 'AB', 'ABC', 'IPMI', 'IPMI5', 'KONTRO', 'KONTRON', 'KONTRON1',
    'KONTRON12',
])
def test_FruTypeLengthString_6bitascii_length(string):
    # the last group of 3 bytes can be shorter, e.g. 5 characters take 4
    # bytes. Unused characters of the last byte are decoded as spaces.
    packed = pack6bitascii(string)
    data = bytes([0x80 | len(packed)]) + packed
    f = FruTypeLengthString(data, 0)
    assert f.string == string.ljust(len(packed) * 8 // 6)


def test_SdrTypeLengthString_bcd_plus_from_array():
    # the SDR passes the device ID string as array
    f = SdrTypeLengthString(data=array('B', [0x42, 0x12, 0x34]))
    assert f.string == '1234'
