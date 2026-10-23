#!/usr/bin/env python

import pyipmi.msgs.serial_modem

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_setserialmodemconfiguration_encode_req():
    m = pyipmi.msgs.serial_modem.SetSerialModemConfigurationReq()
    m.command.channel_number = 2
    m.parameter_selector = 3
    m.data = b'\x84'
    assert encode_message(m) == b'\x02\x03\x84'


def test_setserialmodemconfiguration_decode_rsp():
    m = pyipmi.msgs.serial_modem.SetSerialModemConfigurationRsp()
    decode_message(m, b'\x80')
    assert m.completion_code == 0x80


def test_getserialmodemconfiguration_encode_req():
    m = pyipmi.msgs.serial_modem.GetSerialModemConfigurationReq()
    m.command.channel_number = 2
    m.command.get_parameter_revision_only = 1
    m.parameter_selector = 3
    assert encode_message(m) == b'\x82\x03\x00\x00'


def test_getserialmodemconfiguration_decode_rsp():
    m = pyipmi.msgs.serial_modem.GetSerialModemConfigurationRsp()
    decode_message(m, b'\x00\x11\x84')
    assert m.parameter_revision == 0x11
    assert bytes(m.data) == b'\x84'


def test_serialmodemconnectionactive_encode_req():
    m = pyipmi.msgs.serial_modem.SerialModemConnectionActiveReq()
    m.session_state.state = m.SESSION_ACTIVE
    assert encode_message(m) == b'\x01\x51'


def test_serialmodemconnectionactive_decode_req():
    m = pyipmi.msgs.serial_modem.SerialModemConnectionActiveReq()
    decode_message(m, b'\x02\x02')
    assert m.session_state.state == m.SWITCHING_MUX_TO_SYSTEM
    assert m.ipmi_version == 0x02
