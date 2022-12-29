#!/usr/bin/env python

import pyipmi.msgs.hpm

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_uploadfirmwareblockreq_encode():
    m = pyipmi.msgs.hpm.UploadFirmwareBlockReq()
    m.number = 1
    m.data = [0, 1, 2, 3]
    data = encode_message(m)
    assert data == b'\x00\x01\x00\x01\x02\x03'


def test_activatefirmwarereq_decode_valid_req():
    m = pyipmi.msgs.hpm.ActivateFirmwareReq()
    decode_message(m, b'\x00\x01')
    assert m.picmg_identifier == 0
    assert m.rollback_override_policy == 1


def test_activatefirmwarereq_encode_valid_req():
    m = pyipmi.msgs.hpm.ActivateFirmwareReq()
    m.picmg_identifier = 0
    m.rollback_override_policy = 0x1
    data = encode_message(m)
    assert data == b'\x00\x01'


def test_activatefirmwarereq_decode_valid_req_wo_optional():
    m = pyipmi.msgs.hpm.ActivateFirmwareReq()
    decode_message(m, b'\x00')
    assert m.picmg_identifier == 0
    assert m.rollback_override_policy is None


def test_activatefirmwarereq_encode_valid_req_wo_optional():
    m = pyipmi.msgs.hpm.ActivateFirmwareReq()
    m.picmg_identifier = 0
    m.rollback_override_policy = None
    data = encode_message(m)
    assert data == b'\x00'
