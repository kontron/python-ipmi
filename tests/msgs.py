#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.bmc
import pyipmi.msgs.fru
import pyipmi.msgs.sel
import pyipmi.msgs.event
import pyipmi.msgs.hpm
import pyipmi.msgs.sdr

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

class TestPredicates(unittest.TestCase):
    def test_alias(self):
        m = pyipmi.msgs.sdr.GetSensorReadingRsp()
        raise NotImplementedError()

    def test_optional(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        raise NotImplementedError()

    def test_remaining_bytes(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        raise NotImplementedError()

    def test_conditional(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        raise NotImplementedError()


class TestFruActivationPolicy(unittest.TestCase):
    def test_clear_activation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.activation_locked = 1
        m.set.activation_locked = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x01\x00')

    def test_set_activation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.activation_locked = 1
        m.set.activation_locked = 1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x01\x01')

    def test_clear_deactivation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.deactivation_locked = 1
        m.set.deactivation_locked = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x02\x00')

    def test_set_deactivation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.deactivation_locked = 1
        m.set.deactivation_locked = 1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x02\x02')


class TestActivateFirmware(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        decode_message(m, '\x00\x01')
        self.assertEqual(m.picmg_identifier, 0)
        self.assertEqual(m.rollback_override_policy, 1)

    def test_encode_valid_req(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        m.picmg_identifier = 0
        m.rollback_override_policy = 0x1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01')

    def test_decode_valid_req_wo_optional(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        decode_message(m, '\x00')
        self.assertEqual(m.picmg_identifier, 0)
        self.assertEqual(m.rollback_override_policy, None)

    def test_encode_valid_req_wo_optional(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        m.picmg_identifier = 0
        m.rollback_override_policy = None
        data = encode_message(m)
        self.assertEqual(data, '\x00')


class TestWriteFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        decode_message(m, '\x01\x02\x03\x04\x05')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.data, array('B', '\x04\x05'))

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.data = array('B', '\x04\x05')
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03\x04\x05')

    def test_decode_valid_req_wo_data(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        decode_message(m, '\x01\x02\x03')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.data, array('B'))

    def test_encode_valid_req_wo_data(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.data = array('B')
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03')

    def test_decode_invalid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        self.assertRaises(DecodingError, decode_message, m, '\x01\x02')


class TestReadFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        decode_message(m, '\x01\x02\x03\x04')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.count, 4)

    def test_decode_short_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        self.assertRaises(DecodingError, decode_message, m, '\x01\x02\x03')

    def test_decode_long_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        self.assertRaises(DecodingError, decode_message, m,
                '\x01\x02\x03\04\x05')

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.count = 4
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03\x04')

    def test_decode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        decode_message(m, '\x00\x05\x01\x02\x03\x04\x05')
        self.assertEqual(m.completion_code, 0)
        self.assertEqual(m.count, 5)
        self.assertEqual(m.data, array('B', '\x01\x02\x03\x04\x05'))

    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        decode_message(m, '\xc0')
        self.assertEqual(m.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        self.assertRaises(DecodingError, decode_message, m, '\x00\x01\x01\x02')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        m.completion_code = 0
        m.count = 5
        m.data = array('B', '\x01\x02\x03\x04\x05')
        data = encode_message(m)
        self.assertEqual(data, '\x00\x05\x01\x02\x03\x04\x05')

    def test_encode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        m.completion_code = 0xc0
        data = encode_message(m)
        self.assertEqual(data, '\xc0')

    def test_encode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        m.completion_code = 0
        m.count = 1
        m.data = array('B', '\x01\x02')
        self.assertRaises(EncodingError, encode_message, m)


class TestGetDeviceId(unittest.TestCase):
    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.bmc.GetDeviceIdRsp()
        decode_message(m, '\xc0')
        self.assertEqual(m.completion_code, 0xc0)

    def test_decode_valid_res(self):
        m = pyipmi.msgs.bmc.GetDeviceIdRsp()
        decode_message(m, '\x00\x0c\x89\x00\x00\x02\x3d\x98'
                '\x3a\x00\xbe\x14\x04\x00\x02\x00')
        self.assertEqual(m.completion_code, 0)
        self.assertEqual(m.device_id, 0x0c)
        self.assertEqual(m.device_revision.device_revision, 9)
        self.assertEqual(m.device_revision.provides_device_sdrs, 1)
        self.assertEqual(m.firmware_revision.major, 0)
        self.assertEqual(m.firmware_revision.device_available, 0)
        self.assertEqual(m.firmware_revision.minor, 0)
        self.assertEqual(m.ipmi_version, 2)
        self.assertEqual(m.additional_support.sensor, 1)
        self.assertEqual(m.additional_support.sdr_repository, 0)
        self.assertEqual(m.additional_support.sel, 1)
        self.assertEqual(m.additional_support.fru_inventory, 1)
        self.assertEqual(m.additional_support.ipmb_event_receiver, 1)
        self.assertEqual(m.additional_support.ipmb_event_generator, 1)
        self.assertEqual(m.additional_support.bridge, 0)
        self.assertEqual(m.additional_support.chassis, 0)
        self.assertEqual(m.manufacturer_id, 15000)
        self.assertEqual(m.product_id, 5310)
        self.assertEqual(m.auxiliary, array('B', '\x04\x00\x02\x00'))

    def test_decode_valid_res_wo_aux(self):
        m = pyipmi.msgs.bmc.GetDeviceIdRsp()
        decode_message(m, '\x00\x0c\x89\x00\x00\x02\x3d\x98'
                '\x3a\x00\xbe\x14')
        self.assertEqual(m.completion_code, 0)
        self.assertEqual(m.device_id, 0x0c)
        self.assertEqual(m.device_revision.device_revision, 9)
        self.assertEqual(m.device_revision.provides_device_sdrs, 1)
        self.assertEqual(m.firmware_revision.major, 0)
        self.assertEqual(m.firmware_revision.device_available, 0)
        self.assertEqual(m.firmware_revision.minor, 0)
        self.assertEqual(m.ipmi_version, 2)
        self.assertEqual(m.additional_support.sensor, 1)
        self.assertEqual(m.additional_support.sdr_repository, 0)
        self.assertEqual(m.additional_support.sel, 1)
        self.assertEqual(m.additional_support.fru_inventory, 1)
        self.assertEqual(m.additional_support.ipmb_event_receiver, 1)
        self.assertEqual(m.additional_support.ipmb_event_generator, 1)
        self.assertEqual(m.additional_support.bridge, 0)
        self.assertEqual(m.additional_support.chassis, 0)
        self.assertEqual(m.manufacturer_id, 15000)
        self.assertEqual(m.product_id, 5310)


class TestGetSelftestResults(unittest.TestCase):
    def test_decode_selftest_passed_rsp(self):
        m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
        decode_message(m, '\x00\x55\x00')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.result, 0x55)
        self.assertEqual(m.status, 0x00)

    def test_decode_selftest_fail_not_implemented_rsp(self):
        m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
        decode_message(m, '\x00\x56\x00')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.result, 0x56)
        self.assertEqual(m.status, 0x00)

    def test_decode_selftest_fail_corrupted_sel_rsp(self):
        m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
        decode_message(m, '\x00\x57\x80')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.result, 0x57)
        self.assertEqual(m.status, 0x80)
        self.assertEqual(m.cannot_access_sel_device, 1)
        self.assertEqual(m.cannot_access_sdr_device, 0)
        self.assertEqual(m.cannot_access_bmc_fru_device, 0)
        self.assertEqual(m.ipmb_signal_lines_do_not_respond, 0)
        self.assertEqual(m.sdr_repository_empty, 0)
        self.assertEqual(m.internal_use_area_corrupted, 0)
        self.assertEqual(m.controller_bootblock_corrupted, 0)
        self.assertEqual(m.controller_firmware_corrupted, 0)

    def test_decode_selftest_fail_corrupted_sdr_rsp(self):
        m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
        decode_message(m, '\x00\x57\x40')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.result, 0x57)
        self.assertEqual(m.status, 0x40)
        self.assertEqual(m.cannot_access_sel_device, 0)
        self.assertEqual(m.cannot_access_sdr_device, 1)
        self.assertEqual(m.cannot_access_bmc_fru_device, 0)
        self.assertEqual(m.ipmb_signal_lines_do_not_respond, 0)
        self.assertEqual(m.sdr_repository_empty, 0)
        self.assertEqual(m.internal_use_area_corrupted, 0)
        self.assertEqual(m.controller_bootblock_corrupted, 0)
        self.assertEqual(m.controller_firmware_corrupted, 0)

    def test_decode_selftest_fail_corrupted_sdr_rsp(self):
        m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
        decode_message(m, '\x00\x57\x20')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.result, 0x57)
        self.assertEqual(m.status, 0x20)
        self.assertEqual(m.cannot_access_sel_device, 0)
        self.assertEqual(m.cannot_access_sdr_device, 0)
        self.assertEqual(m.cannot_access_bmc_fru_device, 1)
        self.assertEqual(m.ipmb_signal_lines_do_not_respond, 0)
        self.assertEqual(m.sdr_repository_empty, 0)
        self.assertEqual(m.internal_use_area_corrupted, 0)
        self.assertEqual(m.controller_bootblock_corrupted, 0)
        self.assertEqual(m.controller_firmware_corrupted, 0)


class TestSetBmcGlobalEnables(unittest.TestCase):
    def test_encode_all_disabled_req(self):
        m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
        m.enables.oem_2 = 0
        m.enables.oem_1 = 0
        m.enables.oem_0 = 0
        m.enables.system_event_logging = 0
        m.enables.event_message_buffer = 0
        m.enables.event_message_buffer_full_interrupt = 0
        m.enables.receive_message_queue_interrupt = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00')

    def test_encode_enable_oem_2_req(self):
        m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
        m.enables.oem_2 = 1
        m.enables.oem_1 = 0
        m.enables.oem_0 = 0
        m.enables.system_event_logging = 0
        m.enables.event_message_buffer = 0
        m.enables.event_message_buffer_full_interrupt = 0
        m.enables.receive_message_queue_interrupt = 0
        data = encode_message(m)
        self.assertEqual(data, '\x80')

    def test_encode_enable_oem_1_req(self):
        m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
        m.enables.oem_2 = 0
        m.enables.oem_1 = 1
        m.enables.oem_0 = 0
        m.enables.system_event_logging = 0
        m.enables.event_message_buffer = 0
        m.enables.event_message_buffer_full_interrupt = 0
        m.enables.receive_message_queue_interrupt = 0
        data = encode_message(m)
        self.assertEqual(data, '\x40')

    def test_encode_enable_oem_0_req(self):
        m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
        m.enables.oem_2 = 0
        m.enables.oem_1 = 0
        m.enables.oem_0 = 1
        m.enables.system_event_logging = 0
        m.enables.event_message_buffer = 0
        m.enables.event_message_buffer_full_interrupt = 0
        m.enables.receive_message_queue_interrupt = 0
        data = encode_message(m)
        self.assertEqual(data, '\x20')

    def test_encode_enable_receive_message_queue_interrupt_req(self):
        m = pyipmi.msgs.bmc.SetBmcGlobalEnablesReq()
        m.enables.oem_2 = 0
        m.enables.oem_1 = 0
        m.enables.oem_0 = 0
        m.enables.system_event_logging = 0
        m.enables.event_message_buffer = 0
        m.enables.event_message_buffer_full_interrupt = 0
        m.enables.receive_message_queue_interrupt = 1
        data = encode_message(m)
        self.assertEqual(data, '\x01')


class TestGetBmcGlobalEnables(unittest.TestCase):
    def test_decode_all_disabled_rsp(self):
        m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
        decode_message(m, '\x00\x00')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enables.oem_2, 0)
        self.assertEqual(m.enables.oem_1, 0)
        self.assertEqual(m.enables.oem_0, 0)
        self.assertEqual(m.enables.system_event_logging, 0)
        self.assertEqual(m.enables.event_message_buffer, 0)
        self.assertEqual(m.enables.event_message_buffer_full_interrupt, 0)
        self.assertEqual(m.enables.receive_message_queue_interrupt, 0)

    def test_decode_oem_2_enabled_rsp(self):
        m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
        decode_message(m, '\x00\x80')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enables.oem_2, 1)
        self.assertEqual(m.enables.oem_1, 0)
        self.assertEqual(m.enables.oem_0, 0)
        self.assertEqual(m.enables.system_event_logging, 0)
        self.assertEqual(m.enables.event_message_buffer, 0)
        self.assertEqual(m.enables.event_message_buffer_full_interrupt, 0)
        self.assertEqual(m.enables.receive_message_queue_interrupt, 0)

    def test_decode_oem_0_enabled_rsp(self):
        m = pyipmi.msgs.bmc.GetBmcGlobalEnablesRsp()
        decode_message(m, '\x00\x20')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enables.oem_2, 0)
        self.assertEqual(m.enables.oem_1, 0)
        self.assertEqual(m.enables.oem_0, 1)
        self.assertEqual(m.enables.system_event_logging, 0)
        self.assertEqual(m.enables.event_message_buffer, 0)
        self.assertEqual(m.enables.event_message_buffer_full_interrupt, 0)
        self.assertEqual(m.enables.receive_message_queue_interrupt, 0)


class TestClearMessageFlags(unittest.TestCase):
    def test_encode_clear_none_req(self):
        m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
        m.clear.oem_2 = 0
        m.clear.oem_1 = 0
        m.clear.oem_0 = 0
        m.clear.watchdog_pretimeout_interrupt_flag = 0
        m.clear.event_message_buffer = 0
        m.clear.receive_message_queue = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00')

    def test_encode_clear_oem_2_req(self):
        m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
        m.clear.oem_2 = 1
        m.clear.oem_1 = 0
        m.clear.oem_0 = 0
        m.clear.watchdog_pretimeout_interrupt_flag = 0
        m.clear.event_message_buffer = 0
        m.clear.receive_message_queue = 0
        data = encode_message(m)
        self.assertEqual(data, '\x80')

    def test_encode_clear_oem_0_req(self):
        m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
        m.clear.oem_2 = 0
        m.clear.oem_1 = 0
        m.clear.oem_0 = 1
        m.clear.watchdog_pretimeout_interrupt_flag = 0
        m.clear.event_message_buffer = 0
        m.clear.receive_message_queue = 0
        data = encode_message(m)
        self.assertEqual(data, '\x20')

    def test_encode_clear_receive_message_queue_req(self):
        m = pyipmi.msgs.bmc.ClearMessageFlagsReq()
        m.clear.oem_2 = 0
        m.clear.oem_1 = 0
        m.clear.oem_0 = 0
        m.clear.watchdog_pretimeout_interrupt_flag = 0
        m.clear.event_message_buffer = 0
        m.clear.receive_message_queue = 1
        data = encode_message(m)
        self.assertEqual(data, '\x01')


class TestGetMessageFlags(unittest.TestCase):
    def test_decode_not_flag_set_rsp(self):
        m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
        decode_message(m, '\x00\x00')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.flag.oem_2, 0)
        self.assertEqual(m.flag.oem_1, 0)
        self.assertEqual(m.flag.oem_0, 0)
        self.assertEqual(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
        self.assertEqual(m.flag.event_message_buffer_full, 0)
        self.assertEqual(m.flag.receive_message_available, 0)

    def test_decode_oem_2_set_rsp(self):
        m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
        decode_message(m, '\x00\x80')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.flag.oem_2, 1)
        self.assertEqual(m.flag.oem_1, 0)
        self.assertEqual(m.flag.oem_0, 0)
        self.assertEqual(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
        self.assertEqual(m.flag.event_message_buffer_full, 0)
        self.assertEqual(m.flag.receive_message_available, 0)

    def test_decode_event_message_full_set_rsp(self):
        m = pyipmi.msgs.bmc.GetMessageFlagsRsp()
        decode_message(m, '\x00\x02')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.flag.oem_2, 0)
        self.assertEqual(m.flag.oem_1, 0)
        self.assertEqual(m.flag.oem_0, 0)
        self.assertEqual(m.flag.watchdog_pretimeout_interrupt_occurred, 0)
        self.assertEqual(m.flag.event_message_buffer_full, 1)
        self.assertEqual(m.flag.receive_message_available, 0)


class TestEnableMessageChannelReceive(unittest.TestCase):
    def test_encode_all_off_req(self):
        m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
        m.channel.number = 0
        m.channel.state = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00\x00')

    def test_encode_channel1_enable_req(self):
        m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
        m.channel.number = 1
        m.channel.state = 1
        data = encode_message(m)
        self.assertEqual(data, '\x01\x01')

    def test_encode_channel2_enable_req(self):
        m = pyipmi.msgs.bmc.EnableMessageChannelReceiveReq()
        m.channel.number = 2
        m.channel.state = 1
        data = encode_message(m)
        self.assertEqual(data, '\x02\x01')

    def test_decode_channel1_enabled_rsp(self):
        m = pyipmi.msgs.bmc.EnableMessageChannelReceiveRsp()
        decode_message(m, '\x00\x01\x01')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.channel.number, 1)
        self.assertEqual(m.channel.state, 1)


class TestGetMessage(unittest.TestCase):
	def test_decode_no_data_rsp(self):
		m = pyipmi.msgs.bmc.GetMessageRsp()
		decode_message(m, '\x00\x21')
		self.assertEqual(m.completion_code, 0x00)
		self.assertEqual(m.channel_number.channel_number, 1)
		self.assertEqual(m.channel_number.privilege_level, 2)

	def test_decode_with_data_rsp(self):
		m = pyipmi.msgs.bmc.GetMessageRsp()
		decode_message(m, '\x00\x21\xaa\xff\xff\xee')
		self.assertEqual(m.completion_code, 0x00)
		self.assertEqual(m.channel_number.channel_number, 1)
		self.assertEqual(m.channel_number.privilege_level, 2)
		self.assertEqual(m.data, array('B', '\xaa\xff\xff\xee'))


class TestReadEventMessageBuffer(unittest.TestCase):
    def test_decode_rsp(self):
        m = pyipmi.msgs.bmc.ReadEventMessageBufferRsp()
        decode_message(m, '\x00\x00\x01\x02\x03\x04\x05\x06\x07'\
                '\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.event_data, array('B', '\x00\x01\x02\x03\x04'\
                '\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'))


class TestGetSelEntry(unittest.TestCase):
    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        decode_message(m, '\xc0')
        self.assertEqual(m.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        self.assertRaises(DecodingError, decode_message, m, '\x00\x01')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        decode_message(m, '\x00\x02\x01\x01\x02\x03\x04')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.next_record_id, 0x0102)
        self.assertEqual(m.record_data, '\x01\x02\x03\x04')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        m.completion_code = 0
        m.next_record_id = 0x0102
        m.record_data = array('B', '\x01\x02\x03\x04')
        data = encode_message(m)
        self.assertEqual(data, '\x00\x02\x01\x01\x02\x03\x04')


class TestGetFruLedState(unittest.TestCase):
    def test_decode_rsp_local_control_state(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x01\xff\x00\x02')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 2)

    def test_decode_rsp_override_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x03\xff\x00\x03\xff\x00\x03')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 3)
        self.assertEqual(m.led_states.override_en, 1)
        self.assertEqual(m.override_function, 0xff)
        self.assertEqual(m.override_on_duration, 0)
        self.assertEqual(m.override_color, 3)

    def test_decode_rsp_lamp_test_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x07\xff\x00\x02\xff\x00\x02\x7f')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 2)
        self.assertEqual(m.led_states.override_en, 1)
        self.assertEqual(m.override_function, 0xff)
        self.assertEqual(m.override_on_duration, 0)
        self.assertEqual(m.override_color, 2)
        self.assertEqual(m.led_states.lamp_test_en, 1)
        self.assertEqual(m.lamp_test_duration, 0x7f)


class TestGetDeviceSdrInfo(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sdr.GetDeviceSdrInfoReq()
        data = encode_message(m)
        self.assertEqual(data, '')

    def test_encode_rsp(self):
        m = pyipmi.msgs.sdr.GetDeviceSdrInfoRsp()
        decode_message(m, '\x00\x03\x05')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.number_of_sensors, 3)
        self.assertEqual(m.flags.lun0_has_sensors, 1)
        self.assertEqual(m.flags.lun1_has_sensors, 0)
        self.assertEqual(m.flags.lun2_has_sensors, 1)
        self.assertEqual(m.flags.lun3_has_sensors, 0)
        self.assertEqual(m.flags.dynamic_population, 0)

    def test_encode_rsp_with_timestamp(self):
        m = pyipmi.msgs.sdr.GetDeviceSdrInfoRsp()
        decode_message(m, '\x00\x12\x01\xaa\xbb\xcc\xdd')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.number_of_sensors, 0x12)
        self.assertEqual(m.flags.lun0_has_sensors, 1)
        self.assertEqual(m.flags.lun1_has_sensors, 0)
        self.assertEqual(m.flags.lun2_has_sensors, 0)
        self.assertEqual(m.flags.lun3_has_sensors, 0)
        self.assertEqual(m.flags.dynamic_population, 0)
        self.assertEqual(m.sensor_population_change, 0xddccbbaa)


class TestSetSensorHysteresis(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sdr.SetSensorHysteresisReq()
        m.sensor_number = 0xab
        m.positive_going_hysteresis = 0xaa
        m.negative_going_hysteresis = 0xbb
        data = encode_message(m)
        self.assertEqual(data, '\xab\xff\xaa\xbb')


class TestGetSensorHysteresis(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sdr.GetSensorHysteresisReq()
        m.sensor_number = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\xab')

    def test_decode_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorHysteresisRsp()
        decode_message(m, '\x00\xaa\xbb')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.positive_going_hysteresis, 0xaa)
        self.assertEqual(m.negative_going_hysteresis, 0xbb)


class TestSetSensorThreshold(unittest.TestCase):
    def test_encode_req_set_unr(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.unr = 1
        m.threshold.unr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x20\x00\x00\x00\x00\x00\xaa')

    def test_encode_req_set_ucr(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.ucr = 1
        m.threshold.ucr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x10\x00\x00\x00\x00\xaa\x00')

    def test_encode_req_set_unc(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.unc = 1
        m.threshold.unc = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x08\x00\x00\x00\xaa\x00\x00')

    def test_encode_req_set_lnr(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.lnr = 1
        m.threshold.lnr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x04\x00\x00\xaa\x00\x00\x00')

    def test_encode_req_set_lcr(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.lcr = 1
        m.threshold.lcr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x02\x00\xaa\x00\x00\x00\x00')

    def test_encode_req_set_lnc(self):
        m = pyipmi.msgs.sdr.SetSensorThresholdReq()
        m.sensor_number = 0x55
        m.set_mask.lnc = 1
        m.threshold.lnc = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x01\xaa\x00\x00\x00\x00\x00')


class TestSetSensorEventEnable(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00')

    def test_encode_cfg_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 2
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x20')

    def test_encode_scanning_enabled_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 1
        data = encode_message(m)
        self.assertEqual(data, '\xab\x40')

    def test_encode_event_enabled_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 1
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x80')

    def test_encode_byte3_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        m.byte3 = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00\xaa')

    def test_encode_byte34_req(self):
        m = pyipmi.msgs.sdr.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        m.byte3 = 0xaa
        m.byte4 = 0xbb
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00\xaa\xbb')

class TestGetSensorEventEnable(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableReq()
        m.sensor_number = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\xab')

    def test_decode_event_enabled_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableRsp()
        decode_message(m, '\x00\x80')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.enabled.sensor_scanning, 0)

    def test_decode_scanning_enabled_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableRsp()
        decode_message(m, '\x00\x40')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 0)
        self.assertEqual(m.enabled.sensor_scanning, 1)

    def test_decode_byte3_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)

    def test_decode_byte34_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa\xbb')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)
        self.assertEqual(m.byte4, 0xbb)

    def test_decode_byte34_rsp(self):
        m = pyipmi.msgs.sdr.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa\xbb\xcc\xdd')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)
        self.assertEqual(m.byte4, 0xbb)
        self.assertEqual(m.byte5, 0xcc)
        self.assertEqual(m.byte6, 0xdd)


class TestSetEventReceiver(unittest.TestCase):
    def test_encode_lun0_req(self):
        m = pyipmi.msgs.event.SetEventReceiverReq()
        m.event_receiver.ipmb_i2c_slave_address = 0x10
        m.event_receiver.lun = 0
        data = encode_message(m)
        self.assertEqual(data, '\x20\x00')

    def test_encode_lun3_req(self):
        m = pyipmi.msgs.event.SetEventReceiverReq()
        m.event_receiver.ipmb_i2c_slave_address = 0x10
        m.event_receiver.lun = 3
        data = encode_message(m)
        self.assertEqual(data, '\x20\x03')


class TestGetEventReceiver(unittest.TestCase):
    def test_decode_lun0_rsp(self):
        m = pyipmi.msgs.event.GetEventReceiverRsp()
        decode_message(m, '\x00\x20\x00')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.event_receiver.ipmb_i2c_slave_address, 0x10)
        self.assertEqual(m.event_receiver.lun, 0)

    def test_decode_lun3_rsp(self):
        m = pyipmi.msgs.event.GetEventReceiverRsp()
        decode_message(m, '\x00\x20\x03')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.event_receiver.ipmb_i2c_slave_address, 0x10)
        self.assertEqual(m.event_receiver.lun, 3)


if __name__ == '__main__':
    unittest.main()
