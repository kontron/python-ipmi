#!/usr/bin/env python

import pytest

import pyipmi.msgs.dcmi
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import create_response_by_name
from pyipmi.msgs import decode_message
from pyipmi.msgs import encode_message
from pyipmi.msgs.constants import NETFN_GROUP_EXTENSION


@pytest.mark.parametrize('name, cmdid', [
    ('GetDcmiCapabilities', 0x01),
    ('GetPowerReading', 0x02),
    ('GetPowerLimit', 0x03),
    ('SetPowerLimit', 0x04),
    ('ActivateDeactivatePowerLimit', 0x05),
    ('GetAssetTag', 0x06),
    ('GetDcmiSensorInfo', 0x07),
    ('SetAssetTag', 0x08),
    ('GetManagementControllerIdString', 0x09),
    ('SetManagementControllerIdString', 0x0a),
])
def test_message_ids(name, cmdid):
    req = create_request_by_name(name)
    rsp = create_response_by_name(name)
    assert req.netfn == NETFN_GROUP_EXTENSION
    assert rsp.netfn == NETFN_GROUP_EXTENSION | 1
    assert req.cmdid == rsp.cmdid == cmdid
    assert req.group_extension == rsp.group_extension == 0xdc


def test_getdcmicapabilities_encode_req():
    m = pyipmi.msgs.dcmi.GetDcmiCapabilitiesReq()
    m.parameter_selector = 1
    assert encode_message(m) == b'\xdc\x01'


def test_getdcmicapabilities_decode_rsp():
    m = pyipmi.msgs.dcmi.GetDcmiCapabilitiesRsp()
    decode_message(m, b'\x00\xdc\x01\x05\x02\x00\x01\x05')
    assert m.completion_code == 0
    assert m.specification_conformence.major == 1
    assert m.specification_conformence.minor == 5
    assert m.parameter_revision == 2
    assert m.parameter_data == bytearray(b'\x00\x01\x05')


def test_getpowerreading_encode_req():
    m = pyipmi.msgs.dcmi.GetPowerReadingReq()
    m.mode = 1
    assert encode_message(m) == b'\xdc\x01\x00\x00'


def test_getpowerreading_decode_rsp():
    m = pyipmi.msgs.dcmi.GetPowerReadingRsp()
    decode_message(m, b'\x00\xdc\x64\x00\x32\x00\xc8\x00\x78\x00'
                      b'\x10\x20\x30\x40\xe8\x03\x00\x00\x40')
    assert m.completion_code == 0
    assert m.current_power == 100
    assert m.minimum_power == 50
    assert m.maximum_power == 200
    assert m.average_power == 120
    assert m.timestamp == 0x40302010
    assert m.period == 1000
    assert m.reading_state == 0x40


def test_getpowerlimit_encode_req():
    m = pyipmi.msgs.dcmi.GetPowerLimitReq()
    assert encode_message(m) == b'\xdc\x00\x00'


def test_getpowerlimit_decode_rsp():
    m = pyipmi.msgs.dcmi.GetPowerLimitRsp()
    decode_message(m, b'\x00\xdc\x00\x00\x01\x2c\x01'
                      b'\xe8\x03\x00\x00\x00\x00\x05\x00')
    assert m.completion_code == 0
    assert m.exception_actions == 1
    assert m.power_limit == 300
    assert m.correction_time_limit == 1000
    assert m.statistics_sampling_period == 5


def test_getpowerlimit_decode_rsp_no_active_limit():
    m = pyipmi.msgs.dcmi.GetPowerLimitRsp()
    decode_message(m, b'\x80\xdc\x00\x00\x00\x00\x00'
                      b'\x00\x00\x00\x00\x00\x00\x00\x00')
    assert m.completion_code == 0x80


def test_setpowerlimit_encode_req():
    m = pyipmi.msgs.dcmi.SetPowerLimitReq()
    m.exception_actions = 1
    m.power_limit = 300
    m.correction_time_limit = 1000
    m.statistics_sampling_period = 5
    assert encode_message(m) == (b'\xdc\x00\x00\x00\x01\x2c\x01'
                                 b'\xe8\x03\x00\x00\x00\x00\x05\x00')


def test_setpowerlimit_decode_rsp():
    m = pyipmi.msgs.dcmi.SetPowerLimitRsp()
    decode_message(m, b'\x00\xdc')
    assert m.completion_code == 0


@pytest.mark.parametrize('activation', [0, 1])
def test_activatedeactivatepowerlimit_encode_req(activation):
    m = pyipmi.msgs.dcmi.ActivateDeactivatePowerLimitReq()
    m.activation = activation
    assert encode_message(m) == bytes([0xdc, activation, 0x00, 0x00])


def test_activatedeactivatepowerlimit_decode_rsp():
    m = pyipmi.msgs.dcmi.ActivateDeactivatePowerLimitRsp()
    decode_message(m, b'\x00\xdc')
    assert m.completion_code == 0


def test_getassettag_encode_req():
    m = pyipmi.msgs.dcmi.GetAssetTagReq()
    m.offset = 0
    m.number_of_bytes = 16
    assert encode_message(m) == b'\xdc\x00\x10'


def test_getassettag_decode_rsp():
    m = pyipmi.msgs.dcmi.GetAssetTagRsp()
    decode_message(m, b'\x00\xdc\x05asset')
    assert m.completion_code == 0
    assert m.total_length == 5
    assert m.data.tobytes() == b'asset'


def test_setassettag_encode_req():
    m = pyipmi.msgs.dcmi.SetAssetTagReq()
    m.offset = 2
    m.number_of_bytes = 3
    m.data = b'abc'
    assert encode_message(m) == b'\xdc\x02\x03abc'


def test_setassettag_decode_rsp():
    m = pyipmi.msgs.dcmi.SetAssetTagRsp()
    decode_message(m, b'\x00\xdc\x05')
    assert m.completion_code == 0
    assert m.total_length == 5


def test_getdcmisensorinfo_encode_req():
    m = pyipmi.msgs.dcmi.GetDcmiSensorInfoReq()
    m.sensor_type = 1
    m.entity_id = 0x40
    m.entity_instance = 0
    m.entity_instance_start = 8
    assert encode_message(m) == b'\xdc\x01\x40\x00\x08'


def test_getdcmisensorinfo_decode_rsp():
    m = pyipmi.msgs.dcmi.GetDcmiSensorInfoRsp()
    decode_message(m, b'\x00\xdc\x0a\x02\x01\x00\x34\x12')
    assert m.completion_code == 0
    assert m.total_number_of_instances == 10
    assert m.number_of_record_ids == 2
    assert m.record_ids.tobytes() == b'\x01\x00\x34\x12'


def test_getmanagementcontrolleridstring_encode_req():
    m = pyipmi.msgs.dcmi.GetManagementControllerIdStringReq()
    m.offset = 16
    m.number_of_bytes = 16
    assert encode_message(m) == b'\xdc\x10\x10'


def test_getmanagementcontrolleridstring_decode_rsp():
    m = pyipmi.msgs.dcmi.GetManagementControllerIdStringRsp()
    decode_message(m, b'\x00\xdc\x04bmc\x00')
    assert m.completion_code == 0
    assert m.total_length == 4
    assert m.data.tobytes() == b'bmc\x00'


def test_setmanagementcontrolleridstring_encode_req():
    m = pyipmi.msgs.dcmi.SetManagementControllerIdStringReq()
    m.offset = 0
    m.number_of_bytes = 4
    m.data = b'bmc\x00'
    assert encode_message(m) == b'\xdc\x00\x04bmc\x00'


def test_setmanagementcontrolleridstring_decode_rsp():
    m = pyipmi.msgs.dcmi.SetManagementControllerIdStringRsp()
    decode_message(m, b'\x00\xdc\x04')
    assert m.completion_code == 0
    assert m.total_length == 4
