#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, raises

from pyipmi.fields import VersionField
from pyipmi.errors import DecodingError


def test_versionfield_object():
    version = VersionField([1, 0x99])
    eq_(version.major, 1)
    eq_(version.minor, 99)

    version = VersionField('\x00\x99')
    eq_(version.major, 0)
    eq_(version.minor, 99)


def test_versionfield_invalid():
    version = VersionField('\x00\xff')
    eq_(version.major, 0)
    eq_(version.minor, 255)


@raises(DecodingError)
def test_versionfield_decoding_error():
    version = VersionField('\x00\x9a')
    eq_(version.major, 0)
    eq_(version.minor, 99)
