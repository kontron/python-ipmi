#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from pyipmi.hpm import (ComponentProperty, ComponentPropertyDescriptionString,
                        ComponentPropertyGeneral,
                        ComponentPropertyCurrentVersion,
                        ComponentPropertyDeferredVersion,
                        ComponentPropertyRollbackVersion,
                        UpgradeActionRecord, UpgradeActionRecordBackup,
                        UpgradeActionRecordPrepare,
                        UpgradeActionRecordUploadForUpgrade,
                        UpgradeActionRecordUploadForCompare, UpgradeImage,
                        PROPERTY_GENERAL_PROPERTIES, PROPERTY_CURRENT_VERSION,
                        PROPERTY_DESCRIPTION_STRING, PROPERTY_ROLLBACK_VERSION,
                        PROPERTY_DEFERRED_VERSION)


class TestComponentProperty(object):
    def test_general(self):
        prop = ComponentProperty().from_data(PROPERTY_GENERAL_PROPERTIES, b'\xaa')
        assert type(prop) is ComponentPropertyGeneral

        prop = ComponentProperty().from_data(PROPERTY_GENERAL_PROPERTIES, (0xaa,))
        assert type(prop) is ComponentPropertyGeneral

    def test_currentversion(self):
        prop = ComponentProperty().from_data(PROPERTY_CURRENT_VERSION, b'\x01\x99')
        assert type(prop) is ComponentPropertyCurrentVersion

        prop = ComponentProperty().from_data(
            PROPERTY_CURRENT_VERSION, (0x01, 0x99))
        assert type(prop) is ComponentPropertyCurrentVersion

    def test_descriptionstring(self):
        prop = ComponentProperty().from_data(PROPERTY_DESCRIPTION_STRING,
                                             b'\x30\x31\x32')
        assert type(prop) is ComponentPropertyDescriptionString
        assert prop.description == '012'

        prop = ComponentProperty().from_data(
            PROPERTY_DESCRIPTION_STRING, (0x33, 0x34, 0x35))
        assert type(prop) is ComponentPropertyDescriptionString
        assert prop.description == '345'

    def test_descriptionstring_with_trailinge_zeros(self):
        prop = ComponentProperty().from_data(PROPERTY_DESCRIPTION_STRING,
                                             b'\x36\x37\x38\x00\x00')
        assert type(prop) is ComponentPropertyDescriptionString
        assert prop.description == '678'

    def test_rollbackversion(self):
        prop = ComponentProperty().from_data(
            PROPERTY_ROLLBACK_VERSION, (0x2, 0x88))
        assert type(prop) is ComponentPropertyRollbackVersion

    def test_deferredversion(self):
        prop = ComponentProperty().from_data(
            PROPERTY_DEFERRED_VERSION, (0x3, 0x77))
        assert type(prop) is ComponentPropertyDeferredVersion


def test_upgradeactionrecord_create_from_data():
    record = UpgradeActionRecord.create_from_data(b'\x00\x08\x02')
    assert record.action == 0
    assert type(record) is UpgradeActionRecordBackup

    record = UpgradeActionRecord.create_from_data(b'\x01\x08\x02')
    assert record.action == 1
    assert type(record) is UpgradeActionRecordPrepare

    record = \
        UpgradeActionRecord.create_from_data(
            b'\x02\x08\x02'
            b'\x01\x99\xaa\xbb\xcc\xdd'
            b'\x30\x31\x32\x33\x34\x35\x36\x37'
            b'\x38\x39\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x30'
            b'\x04\x00\x00\x00\x11\x22\x33\x44')
    assert record.firmware_version.version_to_string() == '1.99'
    assert record.firmware_description_string == '012345678901234567890'
    assert record.firmware_length == 4

    record = UpgradeActionRecord.create_from_data(b'\x03\x08\x02')
    assert record.action == 3
    assert type(record) is UpgradeActionRecordUploadForCompare


def test_upgrade_image():
    path = os.path.dirname(os.path.abspath(__file__))
    hpm_file = os.path.join(path, 'hpm_bin/firmware.hpm')
    image = UpgradeImage(hpm_file)
    assert isinstance(image.actions[0], UpgradeActionRecordPrepare)
    assert isinstance(image.actions[1], UpgradeActionRecordUploadForUpgrade)
