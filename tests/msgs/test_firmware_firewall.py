#!/usr/bin/env python

import pyipmi.msgs.firmware_firewall

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

MASK = bytes(range(16))


def test_getnetfnsupport_encode_req():
    m = pyipmi.msgs.firmware_firewall.GetNetFnSupportReq()
    m.channel.number = 0xe
    assert encode_message(m) == b'\x0e'


def test_getnetfnsupport_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetNetFnSupportRsp()
    decode_message(m, b'\x00\x21' + MASK)
    assert m.lun_support.lun0 == m.BASE_SPECIFICATION
    assert m.lun_support.lun1 == m.NOT_SUPPORTED
    assert m.lun_support.lun2 == m.RESTRICTED_BY_FIREWALL
    assert m.lun_support.lun3 == m.NOT_SUPPORTED
    assert bytes(m.netfn_support) == MASK


def test_getcommandsupport_encode_req():
    m = pyipmi.msgs.firmware_firewall.GetCommandSupportReq()
    m.channel.number = 0xe
    m.net_function.code = 0x06
    assert encode_message(m) == b'\x0e\x06\x00'
    # the group extension commands 80h-FFh of VITA on LUN 1
    m.net_function.code = 0x2c
    m.net_function.operation = m.COMMANDS_80_FF
    m.lun_number = 1
    m.group = b'\x03'
    assert encode_message(m) == b'\x0e\x6c\x01\x03'


def test_getcommandsupport_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetCommandSupportRsp()
    decode_message(m, b'\x00' + MASK)
    assert bytes(m.support_mask) == MASK


def test_getcommandsubfunctionsupport_encode_req():
    m = pyipmi.msgs.firmware_firewall.GetCommandSubFunctionSupportReq()
    m.net_function.code = 0x06
    m.command = 0x24
    assert encode_message(m) == b'\x00\x06\x00\x24'
    m.net_function.code = 0x2e
    m.group = b'\x98\x3a\x00'
    assert encode_message(m) == b'\x00\x2e\x00\x24\x98\x3a\x00'


def test_getcommandsubfunctionsupport_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetCommandSubFunctionSupportRsp()
    decode_message(m, b'\x00\x03\x20\x10')
    assert m.specification.type == m.IPMI
    assert m.specification.errata == 3
    assert m.version == 0x20
    assert m.revision == 0x10
    assert m.support_mask is None
    decode_message(m, b'\x00\x13\x10\x00\x02\x00\x00\x00')
    assert m.specification.type == m.IPMB
    assert m.support_mask == 2


def test_getconfigurablecommands_encode_req():
    m = pyipmi.msgs.firmware_firewall.GetConfigurableCommandsReq()
    m.net_function.code = 0x0a
    m.net_function.operation = m.COMMANDS_00_7F
    assert encode_message(m) == b'\x00\x0a\x00'


def test_getconfigurablecommands_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetConfigurableCommandsRsp()
    decode_message(m, b'\x00' + MASK)
    assert bytes(m.configurable_mask) == MASK


def test_getconfigurablecommandsubfunctions_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetConfigurableCommandSubFunctionsRsp()
    decode_message(m, b'\x00\x0f\x00\x00\x00')
    assert m.configurable_mask == 0x0f
    assert m.additional_configurable_mask is None
    decode_message(m, b'\x00\x0f\x00\x00\x00\x01\x00\x00\x00')
    assert m.additional_configurable_mask == 1


def test_setcommandenables_encode_req():
    m = pyipmi.msgs.firmware_firewall.SetCommandEnablesReq()
    m.channel.number = 1
    m.net_function.code = 0x06
    m.enables = MASK
    assert encode_message(m) == b'\x01\x06\x00' + MASK


def test_setcommandenables_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.SetCommandEnablesRsp()
    decode_message(m, b'\x80')
    assert m.completion_code == 0x80


def test_getcommandenables_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetCommandEnablesRsp()
    decode_message(m, b'\x00' + MASK)
    assert bytes(m.enables) == MASK


def test_setcommandsubfunctionenables_encode_req():
    m = pyipmi.msgs.firmware_firewall.SetCommandSubFunctionEnablesReq()
    m.net_function.code = 0x06
    m.command = 0x24
    m.data = b'\x0f\x00\x00\x00'
    assert encode_message(m) == b'\x00\x06\x00\x24\x0f\x00\x00\x00'


def test_getcommandsubfunctionenables_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetCommandSubFunctionEnablesRsp()
    decode_message(m, b'\x00\x01\x00\x00\x80')
    assert m.enables == 0x80000001
    assert m.additional_enables is None


def test_getoemnetfnianasupport_encode_req():
    m = pyipmi.msgs.firmware_firewall.GetOemNetFnIanaSupportReq()
    m.net_function.code = 0x2e
    m.list.index = 2
    assert encode_message(m) == b'\x00\x2e\x02'


def test_getoemnetfnianasupport_decode_rsp():
    m = pyipmi.msgs.firmware_firewall.GetOemNetFnIanaSupportRsp()
    decode_message(m, b'\x00\x80\x01\x98\x3a\x00')
    assert m.list.last == 1
    assert m.lun_support.lun0 == m.BASE_SPECIFICATION
    assert bytes(m.group) == b'\x98\x3a\x00'
