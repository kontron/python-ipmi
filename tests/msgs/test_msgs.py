#!/usr/bin/env python

from array import array

from nose.tools import eq_, raises

import pyipmi.msgs.bmc
import pyipmi.msgs.event

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getdeviceid_decode_rsp_with_cc():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, '\xc0')
    eq_(m.completion_code, 0xc0)

def test_getdeviceid_decode_valid_res():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, '\x00\x0c\x89\x00\x00\x02\x3d\x98'
            '\x3a\x00\xbe\x14\x04\x00\x02\x00')
    eq_(m.completion_code, 0)
    eq_(m.device_id, 0x0c)
    eq_(m.device_revision.device_revision, 9)
    eq_(m.device_revision.provides_device_sdrs, 1)
    eq_(m.firmware_revision.major, 0)
    eq_(m.firmware_revision.device_available, 0)
    eq_(m.firmware_revision.minor, 0)
    eq_(m.ipmi_version, 2)
    eq_(m.additional_support.sensor, 1)
    eq_(m.additional_support.sdr_repository, 0)
    eq_(m.additional_support.sel, 1)
    eq_(m.additional_support.fru_inventory, 1)
    eq_(m.additional_support.ipmb_event_receiver, 1)
    eq_(m.additional_support.ipmb_event_generator, 1)
    eq_(m.additional_support.bridge, 0)
    eq_(m.additional_support.chassis, 0)
    eq_(m.manufacturer_id, 15000)
    eq_(m.product_id, 5310)
    eq_(m.auxiliary, array('B', b'\x04\x00\x02\x00'))

def test_getdeviceid_decode_valid_res_wo_aux():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, '\x00\x0c\x89\x00\x00\x02\x3d\x98'
            '\x3a\x00\xbe\x14')
    eq_(m.completion_code, 0)
    eq_(m.device_id, 0x0c)
    eq_(m.device_revision.device_revision, 9)
    eq_(m.device_revision.provides_device_sdrs, 1)
    eq_(m.firmware_revision.major, 0)
    eq_(m.firmware_revision.device_available, 0)
    eq_(m.firmware_revision.minor, 0)
    eq_(m.ipmi_version, 2)
    eq_(m.additional_support.sensor, 1)
    eq_(m.additional_support.sdr_repository, 0)
    eq_(m.additional_support.sel, 1)
    eq_(m.additional_support.fru_inventory, 1)
    eq_(m.additional_support.ipmb_event_receiver, 1)
    eq_(m.additional_support.ipmb_event_generator, 1)
    eq_(m.additional_support.bridge, 0)
    eq_(m.additional_support.chassis, 0)
    eq_(m.manufacturer_id, 15000)
    eq_(m.product_id, 5310)

def test_getselftestresults_decode_test_passed_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, '\x00\x55\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x55)
    eq_(int(m.status), 0x00)

def test_getselftestresults_decode_test_fail_not_implemented_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, '\x00\x56\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x56)
    eq_(int(m.status), 0x00)

def test_getselftestresults_decode_test_fail_corrupted_sel_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, '\x00\x57\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x57)
    eq_(int(m.status), 0x80)
    eq_(m.status.cannot_access_sel_device, 1)
    eq_(m.status.cannot_access_sdr_device, 0)
    eq_(m.status.cannot_access_bmc_fru_device, 0)
    eq_(m.status.ipmb_signal_lines_do_not_respond, 0)
    eq_(m.status.sdr_repository_empty, 0)
    eq_(m.status.internal_use_area_corrupted, 0)
    eq_(m.status.controller_bootblock_corrupted, 0)
    eq_(m.status.controller_firmware_corrupted, 0)

def test_getselftestresults_decode_test_fail_corrupted_sdr_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, '\x00\x57\x40')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x57)
    eq_(int(m.status), 0x40)
    eq_(m.status.cannot_access_sel_device, 0)
    eq_(m.status.cannot_access_sdr_device, 1)
    eq_(m.status.cannot_access_bmc_fru_device, 0)
    eq_(m.status.ipmb_signal_lines_do_not_respond, 0)
    eq_(m.status.sdr_repository_empty, 0)
    eq_(m.status.internal_use_area_corrupted, 0)
    eq_(m.status.controller_bootblock_corrupted, 0)
    eq_(m.status.controller_firmware_corrupted, 0)

def test_getselftestresults_decode_test_fail_corrupted_sdr_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, '\x00\x57\x20')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x57)
    eq_(int(m.status), 0x20)
    eq_(m.status.cannot_access_sel_device, 0)
    eq_(m.status.cannot_access_sdr_device, 0)
    eq_(m.status.cannot_access_bmc_fru_device, 1)
    eq_(m.status.ipmb_signal_lines_do_not_respond, 0)
    eq_(m.status.sdr_repository_empty, 0)
    eq_(m.status.internal_use_area_corrupted, 0)
    eq_(m.status.controller_bootblock_corrupted, 0)
    eq_(m.status.controller_firmware_corrupted, 0)

def test_setbmcglobalenables_encode_all_disabled_req():
    m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, '\x00')

def test_setbmcglobalenables_encode_enable_oem_2_req():
    m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 1
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, '\x80')

def test_setbmcglobalenables_encode_enable_oem_1_req():
    m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 1
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, '\x40')

def test_setbmcglobalenables_encode_enable_oem_0_req():
    m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 1
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 0
    data = encode_message(m)
    eq_(data, '\x20')

def test_setbmcglobalenables_encode_enable_receive_message_queue_interrupt_req():
    m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
    m.enables.oem_2 = 0
    m.enables.oem_1 = 0
    m.enables.oem_0 = 0
    m.enables.system_event_logging = 0
    m.enables.event_message_buffer = 0
    m.enables.event_message_buffer_full_interrupt = 0
    m.enables.receive_message_queue_interrupt = 1
    data = encode_message(m)
    eq_(data, '\x01')

def test_getbmcglobalenables_decode_all_disabled_rsp():
    m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
    decode_message(m, '\x00\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 0)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 0)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)

def test_getbmcglobalenables_decode_oem_2_enabled_rsp():
    m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
    decode_message(m, '\x00\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 1)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 0)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)

def test_getbmcglobalenables_decode_oem_0_enabled_rsp():
    m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
    decode_message(m, '\x00\x20')
    eq_(m.completion_code, 0x00)
    eq_(m.enables.oem_2, 0)
    eq_(m.enables.oem_1, 0)
    eq_(m.enables.oem_0, 1)
    eq_(m.enables.system_event_logging, 0)
    eq_(m.enables.event_message_buffer, 0)
    eq_(m.enables.event_message_buffer_full_interrupt, 0)
    eq_(m.enables.receive_message_queue_interrupt, 0)

def test_clearmessageflags_encode_clear_none_req():
    m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, '\x00')

def test_clearmessageflags_encode_clear_oem_2_req():
    m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
    m.clear.oem_2 = 1
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, '\x80')

def test_clearmessageflags_encode_clear_oem_0_req():
    m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 1
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 0
    data = encode_message(m)
    eq_(data, '\x20')

def test_clearmessageflags_encode_clear_receive_message_queue_req():
    m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
    m.clear.oem_2 = 0
    m.clear.oem_1 = 0
    m.clear.oem_0 = 0
    m.clear.watchdog_pretimeout_interrupt_flag = 0
    m.clear.event_message_buffer = 0
    m.clear.receive_message_queue = 1
    data = encode_message(m)
    eq_(data, '\x01')

def test_getmessageflags_decode_not_flag_set_rsp():
    m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
    decode_message(m, '\x00\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 0)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 0)
    eq_(m.flag.receive_message_available, 0)

def test_getmessageflags_decode_oem_2_set_rsp():
    m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
    decode_message(m, '\x00\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 1)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 0)
    eq_(m.flag.receive_message_available, 0)

def test_getmessageflags_decode_event_message_full_set_rsp():
    m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
    decode_message(m, '\x00\x02')
    eq_(m.completion_code, 0x00)
    eq_(m.flag.oem_2, 0)
    eq_(m.flag.oem_1, 0)
    eq_(m.flag.oem_0, 0)
    eq_(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
    eq_(m.flag.event_message_buffer_full, 1)
    eq_(m.flag.receive_message_available, 0)

def test_enablemessagechannelreceive_encode_all_off_req():
    m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
    m.channel.number = 0
    m.channel.state = 0
    data = encode_message(m)
    eq_(data, '\x00\x00')

def test_enablemessagechannelreceive_encode_channel1_enable_req():
    m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
    m.channel.number = 1
    m.channel.state = 1
    data = encode_message(m)
    eq_(data, '\x01\x01')

def test_enablemessagechannelreceive_encode_channel2_enable_req():
    m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
    m.channel.number = 2
    m.channel.state = 1
    data = encode_message(m)
    eq_(data, '\x02\x01')

def test_enablemessagechannelreceive_decode_channel1_enabled_rsp():
    m = pyipmi.msgs.bmc.EnableMessageChannelReceiveRsp()
    decode_message(m, '\x00\x01\x01')
    eq_(m.completion_code, 0x00)
    eq_(m.channel.number, 1)
    eq_(m.channel.state, 1)

def test_getmessage_decode_no_data_rsp():
        m = pyipmi.msgs.bmc.GetMessageRsp()
        decode_message(m, '\x00\x21')
        eq_(m.completion_code, 0x00)
        eq_(m.channel_number.channel_number, 1)
        eq_(m.channel_number.privilege_level, 2)

def test_getmessage_decode_with_data_rsp():
        m = pyipmi.msgs.bmc.GetMessageRsp()
        decode_message(m, '\x00\x21\xaa\xff\xff\xee')
        eq_(m.completion_code, 0x00)
        eq_(m.channel_number.channel_number, 1)
        eq_(m.channel_number.privilege_level, 2)
        eq_(m.data, array('B', b'\xaa\xff\xff\xee'))

def test_readeventmessagebuffer_decode_rsp():
    m = pyipmi.msgs.bmc.ReadEventMessageBufferRsp()
    decode_message(m, '\x00\x00\x01\x02\x03\x04\x05\x06\x07'\
            '\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
    eq_(m.completion_code, 0x00)
    eq_(m.event_data, array('B', b'\x00\x01\x02\x03\x04'\
            b'\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'))

def test_masterwriteread_encode_req_all_zero_read():
    m = pyipmi.msgs.bmc.MasterWriteReadReq()
    m.bus_id.type = 0
    m.bus_id.id = 0
    m.bus_id.channel = 0
    m.bus_id.slave_address = 0
    m.read_count = 0
    data = encode_message(m)
    eq_(data,'\x00\x00\x00')

def test_masterwriteread_encode_req_for_read():
    m = pyipmi.msgs.bmc.MasterWriteReadReq()
    m.bus_id.type = 1
    m.bus_id.id = 2
    m.bus_id.channel = 4
    m.bus_id.slave_address = 0x3a
    m.read_count = 5
    data = encode_message(m)
    eq_(data,'\x45\x74\x05')

def test_masterwriteread_encode_req_for_read():
    m = pyipmi.msgs.bmc.MasterWriteReadReq()
    m.bus_id.type = 0
    m.bus_id.id = 0
    m.bus_id.channel = 0
    m.bus_id.slave_address = 0
    m.read_count = 0
    m.data = '\x01\x23\x45'
    data = encode_message(m)
    eq_(data,'\x00\x00\x00\x01\x23\x45')

def test_masterwriteread_decode_rsp():
    m = pyipmi.msgs.bmc.MasterWriteReadRsp()
    decode_message(m, '\x00\x11\x22\x33\x44')
    eq_(m.completion_code, 0x00)
    eq_(m.data, array('B', b'\x11\x22\x33\x44'))

def test_seteventreceiver_encode_lun0_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 0
    data = encode_message(m)
    eq_(data, '\x20\x00')

def test_seteventreceiver_encode_lun3_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 3
    data = encode_message(m)
    eq_(data, '\x20\x03')

def test_geteventreceiver_decode_lun0_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, '\x00\x20\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.event_receiver.ipmb_i2c_slave_address, 0x10)
    eq_(m.event_receiver.lun, 0)

def test_geteventreceiver_decode_lun3_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, '\x00\x20\x03')
    eq_(m.completion_code, 0x00)
    eq_(m.event_receiver.ipmb_i2c_slave_address, 0x10)
    eq_(m.event_receiver.lun, 3)
