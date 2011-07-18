import unittest
from array import array

import pyipmi.msgs.fru
import pyipmi.msgs.sel
from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

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
        self.assertEqual(m.data, array('c', '\x01\x02\x03\x04\x05'))

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
        m.data = array('c', '\x01\x02\x03\x04\x05')
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
        m.data = array('c', '\x01\x02')
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
        m.record_data = array('c', '\x01\x02\x03\x04')
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


class SetSensorThreshold(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
