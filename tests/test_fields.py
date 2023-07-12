#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from pyipmi.fields import (VersionField, FruTypeLengthString)
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
