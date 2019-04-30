#!/usr/bin/env python

from array import array

from nose.tools import eq_

import pyipmi.msgs.device_messaging

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_setbmcglobalenables_encode_all_disabled_req():
    m = pyipmi.msgs.device_messaging.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, b'\x00')


def test_setbmcglobalenables_encode_enable_oem_2_req():
    m = pyipmi.msgs.device_messaging.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 1
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, b'\x80')


def test_setbmcglobalenables_encode_enable_oem_1_req():
    m = pyipmi.msgs.device_messaging.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 1
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, b'\x40')


def test_setbmcglobalenables_encode_enable_oem_0_req():
    m = pyipmi.msgs.device_messaging.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 1
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, b'\x20')


def test_setbmcglobalenables_encode_enable_receive_queue_interrupt_req():
    m = pyipmi.msgs.device_messaging.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 1
    data = encode_message(m)
    eq_(data, b'\x01')


def test_getbmcglobalenables_decode_all_disabled_rsp():
    m = pyipmi.msgs.device_messaging.GetBmcGlobalEnablesRsp()
    decode_message(m, b'\x00\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 0)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 0)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)


def test_getbmcglobalenables_decode_oem_2_enabled_rsp():
    m = pyipmi.msgs.device_messaging.GetBmcGlobalEnablesRsp()
    decode_message(m, b'\x00\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 1)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 0)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)


def test_getbmcglobalenables_decode_oem_0_enabled_rsp():
    m = pyipmi.msgs.device_messaging.GetBmcGlobalEnablesRsp()
    decode_message(m, b'\x00\x20')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 0)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 1)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)


def test_clearmessageflags_encode_clear_none_req():
    m = pyipmi.msgs.device_messaging.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, b'\x00')


def test_clearmessageflags_encode_clear_oem_2_req():
    m = pyipmi.msgs.device_messaging.ClearMessageFlagsReq()
    m.clear.oem_2 = 1
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, b'\x80')


def test_clearmessageflags_encode_clear_oem_0_req():
    m = pyipmi.msgs.device_messaging.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 1
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, b'\x20')


def test_clearmessageflags_encode_clear_receive_message_queue_req():
    m = pyipmi.msgs.device_messaging.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 1
    data = encode_message(m)
    eq_(data, b'\x01')


def test_getmessageflags_decode_not_flag_set_rsp():
    m = pyipmi.msgs.device_messaging.GetMessageFlagsRsp()
    decode_message(m, b'\x00\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 0)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 0)
    eq_(m.flag.receive_message_available, 0)


def test_getmessageflags_decode_oem_2_set_rsp():
    m = pyipmi.msgs.device_messaging.GetMessageFlagsRsp()
    decode_message(m, b'\x00\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 1)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 0)
    eq_(m.flag.receive_message_available, 0)


def test_getmessageflags_decode_event_message_full_set_rsp():
    m = pyipmi.msgs.device_messaging.GetMessageFlagsRsp()
    decode_message(m, b'\x00\x02')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 0)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 1)
    eq_(m.flag.receive_message_available, 0)


def test_enablemessagechannelreceive_encode_all_off_req():
    m = pyipmi.msgs.device_messaging.EnableMessageChannelReceiveReq()
    m.channel.number = 0
    m.channel.state = 0
    data = encode_message(m)
    eq_(data, b'\x00\x00')


def test_enablemessagechannelreceive_encode_channel1_enable_req():
    m = pyipmi.msgs.device_messaging.EnableMessageChannelReceiveReq()
    m.channel.number = 1
    m.channel.state = 1
    data = encode_message(m)
    eq_(data, b'\x01\x01')


def test_enablemessagechannelreceive_encode_channel2_enable_req():
    m = pyipmi.msgs.device_messaging.EnableMessageChannelReceiveReq()
    m.channel.number = 2
    m.channel.state = 1
    data = encode_message(m)
    eq_(data, b'\x02\x01')


def test_enablemessagechannelreceive_decode_channel1_enabled_rsp():
    m = pyipmi.msgs.device_messaging.EnableMessageChannelReceiveRsp()
    decode_message(m, b'\x00\x01\x01')
    eq_(m.completion_code, 0x00)
    eq_(m.channel.number, 1)
    eq_(m.channel.state, 1)


def test_getmessage_decode_no_data_rsp():
    m = pyipmi.msgs.device_messaging.GetMessageRsp()
    decode_message(m, b'\x00\x21')
    eq_(m.completion_code, 0x00)
    eq_(m.channel.number, 1)
    eq_(m.channel.privilege_level, 2)


def test_getmessage_decode_with_data_rsp():
    m = pyipmi.msgs.device_messaging.GetMessageRsp()
    decode_message(m, b'\x00\x21\xaa\xff\xff\xee')
    eq_(m.completion_code, 0x00)
    eq_(m.channel.number, 1)
    eq_(m.channel.privilege_level, 2)
    eq_(m.data, array('B', [0xaa, 0xff, 0xff, 0xee]))


def test_readeventmessagebuffer_decode_rsp():
    m = pyipmi.msgs.device_messaging.ReadEventMessageBufferRsp()
    decode_message(m, b'\x00\x00\x01\x02\x03\x04\x05\x06\x07'
                   b'\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
    eq_(m.completion_code, 0x00)
    eq_(m.event_data, array('B', b'\x00\x01\x02\x03\x04'
        b'\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'))


def test_masterwriteread_encode_req_all_zero_read():
    m = pyipmi.msgs.device_messaging.MasterWriteReadReq()
    m.bus_id.type = 0
    m.bus_id.id = 0
    m.bus_id.channel = 0
    m.bus_id.slave_address = 0
    m.read_count = 0
    data = encode_message(m)
    eq_(data, b'\x00\x00\x00')


def test_masterwriteread_encode_req_for_read():
    m = pyipmi.msgs.device_messaging.MasterWriteReadReq()
    m.bus_id.type = 1
    m.bus_id.id = 2
    m.bus_id.channel = 4
    m.bus_id.slave_address = 0x3a
    m.read_count = 5
    data = encode_message(m)
    eq_(data, b'\x45\x74\x05')


def test_masterwriteread_encode_req_for_write():
    m = pyipmi.msgs.device_messaging.MasterWriteReadReq()
    m.bus_id.type = 0
    m.bus_id.id = 0
    m.bus_id.channel = 0
    m.bus_id.slave_address = 0
    m.read_count = 0
    m.data = [1, 0x23, 0x45]
    data = encode_message(m)
    eq_(data, b'\x00\x00\x00\x01\x23\x45')


def test_masterwriteread_decode_rsp():
    m = pyipmi.msgs.device_messaging.MasterWriteReadRsp()
    decode_message(m, b'\x00\x11\x22\x33\x44')
    eq_(m.completion_code, 0x00)
    eq_(m.data, array('B', [0x11, 0x22, 0x33, 0x44]))


def test_get_channel_authentication_capabilities_req():
    m = pyipmi.msgs.device_messaging.GetChannelAuthenticationCapabilitiesReq()
    m.channel.number = 6
    m.channel.type = 1
    m.privilege_level.requested = 5
    data = encode_message(m)
    eq_(m.cmdid, 0x38)
    eq_(m.netfn, 6)
    eq_(data, b'\x86\x05')


def test_get_channel_authentication_capabilities_rsp():
    m = pyipmi.msgs.device_messaging.GetChannelAuthenticationCapabilitiesRsp()
    decode_message(m, b'\x00\x01\x15\x19\x44\x55\x66\x77\x88')
    eq_(m.cmdid, 0x38)
    eq_(m.netfn, 7)
    eq_(m.completion_code, 0x00)
    eq_(m.channel_number, 1)
    eq_(m.support.none, 1)
    eq_(m.support.md2, 0)
    eq_(m.support.md5, 1)
    eq_(m.support.straight, 1)
    eq_(m.support.oem_proprietary, 0)
    eq_(m.status.anonymous_login_enabled, 1)
    eq_(m.status.anonymous_login_null_user, 0)
    eq_(m.status.anonymous_login_non_null, 0)
    eq_(m.status.user_level, 1)
    eq_(m.status.per_message, 1)
    eq_(m.status.kg, 0)


def test_get_session_challenge_req():
    m = pyipmi.msgs.device_messaging.GetSessionChallengeReq()
    m.authentication.type = 1
#    m.user_name = "helloworld"
    data = encode_message(m)
    eq_(m.cmdid, 0x39)
    eq_(m.netfn, 6)
    eq_(data,
        b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    m.authentication.type = 1
    m.user_name = '0123456789abcdef'
    data = encode_message(m)
    eq_(m.cmdid, 0x39)
    eq_(m.netfn, 6)
    eq_(data, b'\x010123456789abcdef')


def test_get_username_rsp():
    m = pyipmi.msgs.device_messaging.GetUserNameRsp()
    decode_message(m, b'\x00\x72\x6f\x6f\x74\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    eq_(m.cmdid, 0x46)
    eq_(m.netfn, 7)
    eq_(m.completion_code, 0x00)
    eq_(m.user_name, b'root\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')


def test_get_username_req():
    m = pyipmi.msgs.device_messaging.GetUserNameReq()
    m.userid.userid = 2
    data = encode_message(m)
    eq_(m.cmdid, 0x46)
    eq_(m.netfn, 6)
    eq_(m.userid.userid, 2)