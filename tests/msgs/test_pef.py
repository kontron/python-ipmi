#!/usr/bin/env python

import pyipmi.msgs.pef

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getpefcapabilities_decode_rsp():
    m = pyipmi.msgs.pef.GetPefCapabilitiesRsp()
    decode_message(m, b'\x00\x51\x01\x10')
    assert m.pef_version == 0x51
    assert m.action_support.alert == 1
    assert m.action_support.power_down == 0
    assert m.event_filter_table_entries == 16


def test_armpefpostponetimer():
    m = pyipmi.msgs.pef.ArmPefPostponeTimerReq()
    m.timeout = m.GET_COUNTDOWN
    assert encode_message(m) == b'\xff'
    rsp = pyipmi.msgs.pef.ArmPefPostponeTimerRsp()
    decode_message(rsp, b'\x00\x3c')
    assert rsp.countdown == 60


def test_setpefconfigurationparameters_encode_req():
    m = pyipmi.msgs.pef.SetPefConfigurationParametersReq()
    m.parameter.selector = 1
    m.data = b'\x01'
    assert encode_message(m) == b'\x01\x01'


def test_getpefconfigurationparameters():
    m = pyipmi.msgs.pef.GetPefConfigurationParametersReq()
    m.parameter.selector = 6
    m.set_selector = 2
    assert encode_message(m) == b'\x06\x02\x00'
    rsp = pyipmi.msgs.pef.GetPefConfigurationParametersRsp()
    decode_message(rsp, b'\x00\x11\x02\x80')
    assert rsp.parameter_revision == 0x11
    assert bytes(rsp.data) == b'\x02\x80'


def test_lastprocessedeventid():
    m = pyipmi.msgs.pef.SetLastProcessedEventIdReq()
    m.processor.bmc = m.BMC
    m.record_id = 0x1234
    assert encode_message(m) == b'\x01\x34\x12'
    rsp = pyipmi.msgs.pef.GetLastProcessedEventIdRsp()
    decode_message(rsp, b'\x00\x78\x56\x34\x12\x05\x00\x03\x00\x05\x00')
    assert rsp.most_recent_addition == 0x12345678
    assert (rsp.last_record_id, rsp.last_software_processed_id,
            rsp.last_bmc_processed_id) == (5, 3, 5)
