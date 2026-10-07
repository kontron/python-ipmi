#!/usr/bin/env python

import hashlib
import os
import struct
from unittest import mock

import pytest

import pyipmi
from pyipmi.errors import HpmError, IpmiTimeoutError
from pyipmi.hpm import (Hpm, ComponentProperty,
                        ComponentPropertyDescriptionString,
                        ComponentPropertyOem,
                        ComponentPropertyGeneral,
                        ComponentPropertyCurrentVersion,
                        ComponentPropertyDeferredVersion,
                        ComponentPropertyRollbackVersion,
                        UpgradeActionRecord, UpgradeActionRecordBackup,
                        UpgradeActionRecordPrepare,
                        UpgradeActionRecordUploadForUpgrade, UpgradeImage,
                        UpgradeImageHeaderRecord,
                        PROPERTY_GENERAL_PROPERTIES, PROPERTY_CURRENT_VERSION,
                        PROPERTY_DESCRIPTION_STRING, PROPERTY_ROLLBACK_VERSION,
                        PROPERTY_DEFERRED_VERSION, PROPERTY_OEM,
                        ACTION_BACKUP_COMPONENT, ACTION_PREPARE_COMPONENT,
                        ACTION_UPLOAD_FOR_UPGRADE, ACTION_UPLOAD_FOR_COMPARE)

from .ipmi_helper import create_ipmi


class TestComponentProperty:
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

    def test_str(self):
        prop = ComponentProperty().from_data(PROPERTY_GENERAL_PROPERTIES,
                                             b'\x15')
        assert str(prop) == ('General: rollback_is_supported, preparation, '
                             'deferred_activation')

        prop = ComponentProperty().from_data(PROPERTY_CURRENT_VERSION,
                                             b'\x01\x40')
        assert str(prop) == 'Current version: 1.40'

        prop = ComponentProperty().from_data(PROPERTY_DESCRIPTION_STRING,
                                             b'IPMC\x00\x00')
        assert str(prop) == 'Description: IPMC'

        prop = ComponentProperty().from_data(PROPERTY_ROLLBACK_VERSION,
                                             b'\x01\x02')
        assert str(prop) == 'Rollback version: 1.2'

        prop = ComponentProperty().from_data(PROPERTY_DEFERRED_VERSION,
                                             b'\x00\x00')
        assert str(prop) == 'Deferred version: 0.0'

        prop = ComponentPropertyOem(b'\x01\xab')
        assert str(prop) == 'OEM data: 01 ab'


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

    record = UpgradeActionRecord.create_from_data(
        _upload_record(b'\x11\x22\x33'))
    assert type(record) is UpgradeActionRecordUploadForUpgrade
    assert record.firmware_version.version_to_string() == '1.2'
    assert record.firmware_description_string == 'firmware'
    assert record.firmware_length == 3
    assert record.firmware_image_data == b'\x11\x22\x33'
    assert record.length == 3 + 31 + 3


def test_upgradeactionrecord_reserved_type():
    # compare is no action record type, only an Initiate Upgrade Action
    with pytest.raises(HpmError, match='unsupported ActionRecord type 0x03'):
        UpgradeActionRecord.create_from_data(b'\x03\x02\xfb')


def _upload_record(image, components=0x02):
    return (bytes((0x02, components, 0))
            + b'\x01\x02\x00\x00\x00\x00'
            + b'firmware'.ljust(21, b'\x00')
            + struct.pack('<L', len(image)) + image)


@pytest.mark.parametrize('cls', [
    UpgradeActionRecordBackup, UpgradeActionRecordPrepare,
    UpgradeActionRecordUploadForUpgrade,
])
def test_upgradeactionrecord_without_data(cls):
    record = cls()
    assert record.action is None
    assert record.components is None


def test_upgradeactionrecord_upload_truncated():
    data = _upload_record(b'\x11\x22\x33')
    with pytest.raises(HpmError, match='truncated'):
        UpgradeActionRecord.create_from_data(data[:-1])


def test_upgradeactionrecord_upload_str():
    record = UpgradeActionRecord.create_from_data(
        _upload_record(b'\x11\x22\x33'))
    assert str(record) == '\n'.join([
        'Action Record Type: 0x2 (Upload Firmware Image) ',
        ' Components: 0x02',
        ' Firmware Version: 1.2',
        ' Description:      firmware',
        ' Firmware Length:  3'])


def _image_with_actions(tmp_path, actions):
    """Write an image for device ID 4, manufacturer 15000, product 1701
    with component 1 and return the filename."""
    header = (b'PICMGFWU\x00\x04\x98\x3a\x00\xa5\x06' + bytes(5)
              + b'\x02' + bytes(13))
    header += bytes(((-sum(header)) & 0xff,))
    data = header + b''.join(actions)
    path = tmp_path / 'image.hpm'
    path.write_bytes(data + hashlib.md5(data).digest())
    return str(path)


def test_upgrade_image_md5_mismatch(tmp_path):
    filename = _image_with_actions(tmp_path, [b'\x01\x02\xfd'])
    with open(filename, 'r+b') as f:
        f.seek(-1, os.SEEK_END)
        f.write(b'\x00')
    with pytest.raises(HpmError, match='MD5'):
        UpgradeImage(filename)


UPGRADE_STAGE_RSP = {
    'InitiateUpgradeAction': b'\x00\x00',
    'UploadFirmwareBlock': b'\x00\x00',
    'FinishFirmwareUpload': b'\x00\x00',
}


def _initiated_actions(ipmi):
    return [data[-1] for (name, data) in ipmi.requests
            if name == 'InitiateUpgradeActionReq']


def test_upgrade_stage_actions(tmp_path):
    image = UpgradeImage(_image_with_actions(tmp_path, [
        b'\x00\x02\xfe', b'\x01\x02\xfd', _upload_record(bytes(30))]))
    ipmi = create_ipmi(UPGRADE_STAGE_RSP)
    ipmi.upgrade_stage(image, 1)
    assert _initiated_actions(ipmi) == [
        ACTION_BACKUP_COMPONENT, ACTION_PREPARE_COMPONENT,
        ACTION_UPLOAD_FOR_UPGRADE]
    assert ipmi.requests[-1][0] == 'FinishFirmwareUploadReq'


def test_upgrade_stage_compare(tmp_path):
    image = UpgradeImage(_image_with_actions(tmp_path, [
        b'\x00\x02\xfe', b'\x01\x02\xfd', _upload_record(bytes(30))]))
    ipmi = create_ipmi(UPGRADE_STAGE_RSP)
    ipmi.upgrade_stage(image, 1, compare=True)
    # backup and prepare are skipped
    assert _initiated_actions(ipmi) == [ACTION_UPLOAD_FOR_COMPARE]
    names = [name for (name, _) in ipmi.requests]
    assert names.count('UploadFirmwareBlockReq') == 2
    assert names[-1] == 'FinishFirmwareUploadReq'


def test_compare_component_from_file(tmp_path):
    filename = _image_with_actions(tmp_path, [
        b'\x01\x02\xfd', _upload_record(bytes(30))])
    ipmi = create_ipmi({
        **UPGRADE_STAGE_RSP,
        'AbortFirmwareUpgrade': b'\x00\x00',
        'GetDeviceId': DEVICE_ID_RSP,
        'GetTargetUpgradeCapabilities': TARGET_CAPS_RSP,
    })
    ipmi.compare_component_from_file(filename, 1)
    names = [name for (name, _) in ipmi.requests]
    assert _initiated_actions(ipmi) == [ACTION_UPLOAD_FOR_COMPARE]
    assert 'ActivateFirmwareReq' not in names
    assert names[-1] == 'FinishFirmwareUploadReq'


def test_upgrade_image():
    path = os.path.dirname(os.path.abspath(__file__))
    hpm_file = os.path.join(path, 'hpm_bin/firmware.hpm')
    image = UpgradeImage(hpm_file)
    assert isinstance(image.actions[0], UpgradeActionRecordPrepare)
    assert isinstance(image.actions[1], UpgradeActionRecordUploadForUpgrade)


class FakeTime:
    """Replaces the time module.

    Time advances when sleeping and by `tick` on every time() call.
    """

    def __init__(self):
        self.now = 1000.0
        self.tick = 0.0
        self.sleeps = []

    def time(self):
        self.now += self.tick
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def fake_time(monkeypatch):
    fake = FakeTime()
    monkeypatch.setattr('pyipmi.hpm.time', fake)
    return fake


HPM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'hpm_bin/firmware.hpm')

# HPM.1 version 0x55, components 0 and 1
TARGET_CAPS_RSP = b'\x00\x00\x55\x00\x05\x0a\x0b\x0c\x03'
# device ID 4, manufacturer 15000, product 1701 as in firmware.hpm
DEVICE_ID_RSP = b'\x00\x04\x00\x01\x00\x02\x00\x98\x3a\x00\xa5\x06'


def test_get_target_upgrade_capabilities():
    ipmi = create_ipmi(TARGET_CAPS_RSP)
    caps = ipmi.get_target_upgrade_capabilities()
    assert ipmi.requests == [('GetTargetUpgradeCapabilitiesReq', b'\x00')]
    assert caps.version == 0x55
    assert caps.components == [0, 1]
    assert 'Components: [0, 1]' in str(caps)


def test_get_component_property():
    ipmi = create_ipmi(b'\x00\x00\x01\x12\x00\x00\x00\x00')
    prop = ipmi.get_component_property(1, PROPERTY_CURRENT_VERSION)
    assert ipmi.requests == [('GetComponentPropertiesReq', b'\x00\x01\x01')]
    assert prop.version.version_to_string() == '1.12'


def test_get_component_properties():
    ipmi = create_ipmi({'GetComponentProperties': [
        b'\x00\x00\x2c',                     # general properties
        b'\x00\x00\x01\x02',                 # current version
        b'\x00\x00fw\x00',                   # description
        b'\x83',                             # rollback: invalid selector
        b'\x00\x00\x01\x01',                 # deferred version
    ]})
    props = ipmi.get_component_properties(1)
    assert [type(p) for p in props] == [
        ComponentPropertyGeneral, ComponentPropertyCurrentVersion,
        ComponentPropertyDescriptionString, ComponentPropertyDeferredVersion]
    assert props[0].general == ['rollback_backup_not_supported',
                                'preparation', 'comparison',
                                'payload_cold_reset_required']
    assert props[2].description == 'fw'


@pytest.mark.parametrize('cap, support', [
    (0x01, 'rollback_is_supported'),
    (0x02, 'rollback_is_supported'),
    (0x03, 'reserved'),
    (0x10, 'deferred_activation'),
])
def test_component_property_general(cap, support):
    prop = ComponentProperty.from_data(PROPERTY_GENERAL_PROPERTIES, [cap])
    assert support in prop.general


def test_component_property_from_str_and_oem():
    prop = ComponentProperty.from_data(PROPERTY_DESCRIPTION_STRING, 'abc')
    assert prop.description == 'abc'
    with pytest.raises(NotImplementedError):
        ComponentProperty.from_data(PROPERTY_OEM[0], b'\x00')
    assert ComponentPropertyOem(b'\x01\x02').oem_data == b'\x01\x02'


def test_find_component_id_by_descriptor():
    ipmi = create_ipmi({
        'GetTargetUpgradeCapabilities': TARGET_CAPS_RSP,
        'GetComponentProperties': [b'\x00\x00boot\x00', b'\x00\x00fw\x00'],
    })
    assert ipmi.find_component_id_by_descriptor('fw') == 1


def test_find_component_id_by_descriptor_not_found():
    ipmi = create_ipmi({
        'GetTargetUpgradeCapabilities': TARGET_CAPS_RSP,
        'GetComponentProperties': [b'\x00\x00boot\x00', b'\x00\x00fw\x00'],
    })
    assert ipmi.find_component_id_by_descriptor('other') is None


def test_initiate_upgrade_action():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.initiate_upgrade_action(0x02, ACTION_PREPARE_COMPONENT)
    assert ipmi.requests == [('InitiateUpgradeActionReq', b'\x00\x02\x01')]


def test_initiate_upgrade_action_multiple_components():
    ipmi = create_ipmi(b'\x00\x00')
    with pytest.raises(HpmError):
        ipmi.initiate_upgrade_action(0x03, ACTION_UPLOAD_FOR_UPGRADE)
    assert ipmi.requests == []


def test_initiate_upgrade_action_and_wait(fake_time):
    ipmi = create_ipmi({
        'InitiateUpgradeAction': b'\x80',
        # still in progress, then completed
        'GetUpgradeStatus': [b'\x00\x00\x31\x80', b'\x00\x00\x31\x00'],
    })
    ipmi.initiate_upgrade_action_and_wait(0x02, ACTION_PREPARE_COMPONENT,
                                          interval=0.1)
    assert [name for (name, _) in ipmi.requests] == [
        'InitiateUpgradeActionReq', 'GetUpgradeStatusReq',
        'GetUpgradeStatusReq']
    assert fake_time.sleeps == [0.1]


@pytest.mark.parametrize('method, args, command', [
    ('initiate_upgrade_action_and_wait', (0x02, ACTION_PREPARE_COMPONENT),
     'InitiateUpgradeAction'),
    ('finish_upload_and_wait', (1, 100), 'FinishFirmwareUpload'),
    ('activate_firmware_and_wait', (), 'ActivateFirmware'),
    ('initiate_manual_rollback_and_wait', (), 'InitiateManualRollback'),
])
def test_and_wait_error(method, args, command):
    ipmi = create_ipmi({command: b'\xcc'})
    with pytest.raises(HpmError):
        getattr(ipmi, method)(*args)


@pytest.mark.parametrize('method, args, command', [
    ('finish_upload_and_wait', (1, 100), 'FinishFirmwareUpload'),
    ('activate_firmware_and_wait', (), 'ActivateFirmware'),
    ('initiate_manual_rollback_and_wait', (), 'InitiateManualRollback'),
])
def test_and_wait_long_duration(fake_time, method, args, command):
    ipmi = create_ipmi({command: b'\x80',
                        'GetUpgradeStatus': b'\x00\x00\x31\x00'})
    getattr(ipmi, method)(*args)
    assert ipmi.requests[-1][0] == 'GetUpgradeStatusReq'


@pytest.mark.parametrize('method', ['activate_firmware_and_wait',
                                    'initiate_manual_rollback_and_wait'])
def test_and_wait_controller_in_reset(method):
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.interface.send_and_receive.side_effect = IpmiTimeoutError()
    getattr(ipmi, method)()


@pytest.mark.parametrize('kwargs, sleeps', [
    # the timeout is used for the wait
    ({'timeout': 1, 'interval': 0.25}, [0.25] * 4),
    # the default timeout is 60 seconds
    ({'interval': 10}, [10] * 6),
])
def test_initiate_manual_rollback_and_wait_timeout(fake_time, kwargs, sleeps):
    # the rollback stays in progress
    ipmi = create_ipmi({'InitiateManualRollback': b'\x80',
                        'GetUpgradeStatus': b'\x00\x00\x33\x80'})
    ipmi.initiate_manual_rollback_and_wait(**kwargs)
    assert fake_time.sleeps == sleeps


def test_wait_for_long_duration_command_timeout(fake_time):
    ipmi = create_ipmi(b'\x00\x00\x31\x80')
    ipmi.wait_for_long_duration_command(0x31, timeout=1, interval=0.25)
    assert fake_time.sleeps == [0.25] * 4


@pytest.mark.parametrize('error', [IpmiTimeoutError(), OSError()])
def test_wait_for_long_duration_command_not_reachable(fake_time, error):
    ipmi = create_ipmi(b'\x00\x00\x31\x00')
    respond = ipmi.interface.send_and_receive.side_effect
    errors = [error]

    def send_and_receive(req):
        # the controller is not reachable for the first request
        if errors:
            raise errors.pop()
        return respond(req)

    ipmi.interface.send_and_receive.side_effect = send_and_receive
    ipmi.wait_for_long_duration_command(0x31, timeout=1, interval=0.5)
    assert fake_time.sleeps == [0.5]


def test_upload_firmware_block():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.upload_firmware_block(3, 'ab')
    assert ipmi.requests == [('UploadFirmwareBlockReq', b'\x00\x03ab')]


def test_upload_binary():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.upload_binary(bytes(range(50)))
    assert ipmi.requests == [
        ('UploadFirmwareBlockReq', b'\x00\x00' + bytes(range(23))),
        ('UploadFirmwareBlockReq', b'\x00\x01' + bytes(range(23, 46))),
        ('UploadFirmwareBlockReq', b'\x00\x02' + bytes(range(46, 50))),
    ]


def test_upload_binary_long_duration(fake_time):
    ipmi = create_ipmi({'UploadFirmwareBlock': [b'\x80', b'\x00\x00'],
                        'GetUpgradeStatus': b'\x00\x00\x32\x00'})
    ipmi.upload_binary(bytes(30))
    assert [name for (name, _) in ipmi.requests] == [
        'UploadFirmwareBlockReq', 'GetUpgradeStatusReq',
        'UploadFirmwareBlockReq']


def test_upload_binary_error():
    ipmi = create_ipmi(b'\xcc')
    with pytest.raises(HpmError):
        ipmi.upload_binary(bytes(30))


def test_upload_binary_timeout():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.interface.send_and_receive.side_effect = IpmiTimeoutError()
    with pytest.raises(IpmiTimeoutError):
        ipmi.upload_binary(bytes(100), retry=2)
    # the first block is tried `retry` times
    assert ipmi.interface.send_and_receive.call_count == 2


def test_upload_binary_timeout_resends_block():
    ipmi = create_ipmi(b'\x00\x00')
    respond = ipmi.interface.send_and_receive.side_effect
    errors = [IpmiTimeoutError()]

    def send_and_receive(req):
        # the second block times out once
        if req.number == 1 and errors:
            raise errors.pop()
        return respond(req)

    ipmi.interface.send_and_receive.side_effect = send_and_receive
    ipmi.upload_binary(bytes(range(50)))
    assert ipmi.requests == [
        ('UploadFirmwareBlockReq', b'\x00\x00' + bytes(range(23))),
        ('UploadFirmwareBlockReq', b'\x00\x01' + bytes(range(23, 46))),
        ('UploadFirmwareBlockReq', b'\x00\x02' + bytes(range(46, 50))),
    ]


@pytest.mark.parametrize('max_request_data_size, routing, block_size', [
    # directly on the IPMB
    (None, None, 23),
    # LAN interface directly to the BMC
    (38, None, 36),
    # bridged once, the message is on the IPMB
    (38, [(0x81, 0x20, 0), (0x20, 0x88, None)], 23),
    # bridged twice, the message is in a Send Message on the IPMB
    (38, [(0x81, 0x20, 0), (0x20, 0x82, 7), (0x20, 0x72, None)], 15),
])
def test_determine_max_block_size(max_request_data_size, routing, block_size):
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.interface.MAX_REQUEST_DATA_SIZE = max_request_data_size
    ipmi.target = pyipmi.Target(0x88, routing=routing)
    assert ipmi._determine_max_block_size() == block_size


def test_upload_binary_reduces_block_size():
    ipmi = create_ipmi({'UploadFirmwareBlock': [
        b'\xc7', b'\xc8', b'\x00\x00', b'\x00\x00', b'\x00\x00']})
    ipmi.upload_binary(bytes(range(50)))
    assert ipmi.requests == [
        ('UploadFirmwareBlockReq', b'\x00\x00' + bytes(range(23))),
        ('UploadFirmwareBlockReq', b'\x00\x00' + bytes(range(22))),
        ('UploadFirmwareBlockReq', b'\x00\x00' + bytes(range(21))),
        ('UploadFirmwareBlockReq', b'\x00\x01' + bytes(range(21, 42))),
        ('UploadFirmwareBlockReq', b'\x00\x02' + bytes(range(42, 50))),
    ]


def test_upload_binary_length_error_after_accepted_block():
    ipmi = create_ipmi({'UploadFirmwareBlock': [b'\x00\x00', b'\xc7']})
    with pytest.raises(HpmError, match='CC=0xc7'):
        ipmi.upload_binary(bytes(50))


def test_finish_firmware_upload():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.finish_upload_and_wait(1, 0x12345)
    assert ipmi.requests == [('FinishFirmwareUploadReq',
                              b'\x00\x01\x45\x23\x01\x00')]


@pytest.mark.parametrize('rollback_override, data', [
    (None, b'\x00'),
    (1, b'\x00\x01'),
])
def test_activate_firmware(rollback_override, data):
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.activate_firmware(rollback_override)
    assert ipmi.requests == [('ActivateFirmwareReq', data)]


def test_get_upgrade_status():
    ipmi = create_ipmi(b'\x00\x00\x31\x80')
    status = ipmi.get_upgrade_status()
    assert (status.command_in_progress, status.last_completion_code) == \
        (0x31, 0x80)
    assert str(status) == 'cmd=0x31 cc=0x80'


def test_abort_firmware_upgrade():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.abort_firmware_upgrade()
    assert ipmi.requests == [('AbortFirmwareUpgradeReq', b'\x00')]


@pytest.mark.parametrize('result1, result2, failures', [
    (0x55, 0x00, {}),
    (0x57, 0xf5, {'fail_sdrr_empty': 0, 'fail_bmc_fru_interanl_area': 1,
                  'fail_bootblock': 0, 'fail_mc': 1}),
    (0x56, 0xf0, {'fail_sel': 1, 'fail_sdrr': 1, 'fail_bmc_fru': 1,
                  'fail_ipmb': 1}),
])
def test_query_selftest_results(result1, result2, failures):
    ipmi = create_ipmi(bytes([0, 0, result1, result2]))
    result = ipmi.query_selftest_results()
    assert result.status == result1
    for (name, value) in failures.items():
        assert getattr(result, name) == value
    if result1 == 0x57:
        assert not hasattr(result, 'fail_sel')


def test_query_rollback_status():
    ipmi = create_ipmi(b'\x00\x00\x01\x32')
    assert ipmi.query_rollback_status().percent_complete == 0x32


def test_initiate_manual_rollback():
    ipmi = create_ipmi(b'\x00\x00')
    status = ipmi.initiate_manual_rollback()
    assert not hasattr(status, 'percent_complete')


def test_get_upgrade_version_from_file():
    assert str(Hpm.get_upgrade_version_from_file(HPM_FILE)) == '4.50'
    assert isinstance(Hpm.open_upgrade_image(HPM_FILE), UpgradeImage)


def test_upgrade_image_header_str():
    image = UpgradeImage(HPM_FILE)
    s = str(image.header)
    assert 'Device ID:        4' in s
    assert 'Manufacturer:     15000 = Kontron\n' in s
    assert image.header.manufacturer_name == 'Kontron'
    assert str(image.actions[1]).startswith(
        'Action Record Type: 0x2 (Upload Firmware Image)')


def test_upgrade_image_header_unknown_manufacturer():
    with open(HPM_FILE, 'rb') as f:
        data = bytearray(f.read())
    # manufacturer ID 12345, which is not well known
    data[10:13] = b'\x39\x30\x00'
    header = UpgradeImageHeaderRecord(bytes(data))
    assert header.manufacturer_name is None
    assert 'Manufacturer:     12345\n' in str(header)


def test_upgrade_action_record_invalid():
    with pytest.raises(HpmError):
        UpgradeActionRecord.create_from_data(b'\x04\x00\x00')


@pytest.mark.parametrize('device_id, error', [
    (b'\x00\x05\x00\x01\x00\x02\x00\x98\x3a\x00\xa5\x06', 'Device ID'),
    (b'\x00\x04\x00\x01\x00\x02\x00\x99\x3a\x00\xa5\x06', 'Manufacturer ID'),
    (b'\x00\x04\x00\x01\x00\x02\x00\x98\x3a\x00\xa6\x06', 'Product ID'),
])
def test_preparation_stage_mismatch(device_id, error):
    ipmi = create_ipmi({'GetDeviceId': device_id})
    with pytest.raises(HpmError, match=error):
        ipmi.preparation_stage(UpgradeImage(HPM_FILE))


def test_preparation_stage_no_component():
    ipmi = create_ipmi({
        'GetDeviceId': DEVICE_ID_RSP,
        # only component 0 present, the image is for component 1
        'GetTargetUpgradeCapabilities': TARGET_CAPS_RSP[:-1] + b'\x01',
    })
    with pytest.raises(HpmError, match='no supported component'):
        ipmi.preparation_stage(UpgradeImage(HPM_FILE))


def test_install_component_from_file(fake_time):
    # waiting for the new firmware polls without sleeping
    fake_time.tick = 1
    ipmi = create_ipmi({
        'AbortFirmwareUpgrade': b'\x00\x00',
        'GetDeviceId': DEVICE_ID_RSP,
        'GetTargetUpgradeCapabilities': TARGET_CAPS_RSP,
        'InitiateUpgradeAction': b'\x00\x00',
        'UploadFirmwareBlock': b'\x00\x00',
        'FinishFirmwareUpload': b'\x00\x00',
        'ActivateFirmware': b'\x00\x00',
        'GetUpgradeStatus': b'\x00\x00\x00\x00',
    })
    ipmi.install_component_from_file(HPM_FILE, 1)

    names = [name for (name, _) in ipmi.requests]
    image = UpgradeImage(HPM_FILE)
    blocks = -(-image.actions[1].firmware_length // 23)
    assert names[:6] == [
        'AbortFirmwareUpgradeReq', 'GetDeviceIdReq',
        'GetTargetUpgradeCapabilitiesReq',
        'InitiateUpgradeActionReq',        # prepare
        'InitiateUpgradeActionReq',        # upload for upgrade
        'UploadFirmwareBlockReq']
    assert names.count('UploadFirmwareBlockReq') == blocks
    assert 'FinishFirmwareUploadReq' in names
    # the activation is requested without a rollback override policy
    assert ('ActivateFirmwareReq', b'\x00') in ipmi.requests


def test_activation_stage_waits_with_the_image_timeout():
    image = UpgradeImage(HPM_FILE)
    ipmi = create_ipmi(b'\x00\x00')
    with mock.patch.object(ipmi, 'activate_firmware_and_wait') as activate, \
            mock.patch.object(ipmi, 'wait_until_new_firmware_comes_up') as wait:
        ipmi.activation_stage(image, 1)
    timeout = image.header.inaccessibility_timeout
    activate.assert_called_once_with(timeout=timeout, interval=1)
    wait.assert_called_once_with(timeout, 1)


@pytest.mark.parametrize('method', ['install_component_from_image',
                                    'compare_component_from_image'])
def test_component_not_in_image(method):
    ipmi = create_ipmi(b'\x00\x00')
    with pytest.raises(HpmError, match=r'component=0 not in image '
                                       r'\(image components: \[1\]\)'):
        getattr(ipmi, method)(UpgradeImage(HPM_FILE), 0)
    # nothing is sent to the controller
    assert ipmi.requests == []


def test_wait_until_new_firmware_comes_up(fake_time):
    fake_time.tick = 1
    ipmi = create_ipmi({'GetUpgradeStatus': b'\x00\x00\x00\x00',
                        'GetDeviceId': DEVICE_ID_RSP})
    respond = ipmi.interface.send_and_receive.side_effect
    errors = [IpmiTimeoutError(), OSError()]

    def send_and_receive(req):
        # the controller is in reset for the first requests
        if errors:
            raise errors.pop()
        return respond(req)

    ipmi.interface.send_and_receive.side_effect = send_and_receive
    ipmi.wait_until_new_firmware_comes_up(timeout=50, interval=1)
    # returns when the controller answers again
    assert fake_time.sleeps == [1, 1, 5]


def test_wait_until_new_firmware_comes_up_without_reset(fake_time):
    ipmi = create_ipmi({'GetUpgradeStatus': b'\x00\x00\x00\x00',
                        'GetDeviceId': DEVICE_ID_RSP})
    ipmi.wait_until_new_firmware_comes_up(timeout=5, interval=1)
    # the answers may be from the old firmware, wait until the timeout
    assert fake_time.sleeps == [1] * 5 + [5]


def test_upgradeimageheaderrecord_invalid_signature():
    with pytest.raises(HpmError):
        UpgradeImageHeaderRecord(b'\x1f\x8b\x08\x00' + bytes(31))
