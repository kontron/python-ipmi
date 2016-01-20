#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_

from pyipmi.hpm import *

from array import array

def test_componentpropertygeneral_object():
    p = ComponentProperty().from_data(PROPERTY_GENERAL_PROPERTIES, '\xaa')
    eq_(type(p), ComponentPropertyGeneral)

    p = ComponentProperty().from_data(PROPERTY_GENERAL_PROPERTIES, (0xaa,))
    eq_(type(p), ComponentPropertyGeneral)

def test_componentpropertycurrentversion_object():
    p = ComponentProperty().from_data(PROPERTY_CURRENT_VERSION, '\x01\x99')
    eq_(type(p), ComponentPropertyCurrentVersion)

    p = ComponentProperty().from_data(PROPERTY_CURRENT_VERSION, (0x01, 0x99))
    eq_(type(p), ComponentPropertyCurrentVersion)

def test_componentpropertydescriptionstring_object():
    p = ComponentProperty().from_data(PROPERTY_DESCRIPTION_STRING, \
            '\x30\x31\x32\x33\x34')
    eq_(type(p), ComponentPropertyDescriptionString)
    eq_(p.description, '01234')

    p = ComponentProperty().from_data(PROPERTY_DESCRIPTION_STRING, \
            (0x34, 0x35, 0x36, 0x37, 0x38))
    eq_(type(p), ComponentPropertyDescriptionString)
    eq_(p.description, '45678')

def test_componentpropertyrollbackversion_object():
    p = ComponentProperty().from_data(PROPERTY_ROLLBACK_VERSION, (0x2, 0x88))
    eq_(type(p), ComponentPropertyRollbackVersion)

def test_componentpropertydeferredversion_object():
    p = ComponentProperty().from_data(PROPERTY_DEFERRED_VERSION, (0x3, 0x77))
    eq_(type(p), ComponentPropertyDeferredVersion)


def test_upgradeactionrecord_create_from_data():
    record = UpgradeActionRecord.create_from_data('\x00\x08\x02')
    eq_(record.action, 0)
    eq_(type(record), UpgradeActionRecordBackup)

    record = UpgradeActionRecord.create_from_data('\x01\x08\x02')
    eq_(record.action, 1)
    eq_(type(record), UpgradeActionRecordPrepare)

    record = \
    UpgradeActionRecord.create_from_data(
        '\x02\x08\x02'
        '\x01\x99\xaa\xbb\xcc\xdd'
        '\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x30'
        '\x04\x00\x00\x00\x11\x22\x33\x44')
    eq_(record.firmware_version.version_to_string(), '1.99')
    eq_(record.firmware_description_string, '012345678901234567890')
    eq_(record.firmware_length, 4)

    record = UpgradeActionRecord.create_from_data('\x03\x08\x02')
    eq_(record.action, 3)
    eq_(type(record), UpgradeActionRecordUploadForCompare)
