import unittest
from array import array

import pyipmi.msgs.fru
import pyipmi.msgs.sel
from pyipmi.errors import DecodingError, EncodingError

class TestFruActivationPolicy(unittest.TestCase):
    def test_clear_activation_lock(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicy()
        m.req.fru_id = 1
        m.req.mask.activation_locked = 1
        m.req.set.activation_locked = 0
        data = m.req.encode()
        self.assertEqual(data, '\x00\x01\x01\x00')

    def test_set_activation_lock(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicy()
        m.req.fru_id = 1
        m.req.mask.activation_locked = 1
        m.req.set.activation_locked = 1
        data = m.req.encode()
        self.assertEqual(data, '\x00\x01\x01\x01')

    def test_clear_deactivation_lock(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicy()
        m.req.fru_id = 1
        m.req.mask.deactivation_locked = 1
        m.req.set.deactivation_locked = 0
        data = m.req.encode()
        self.assertEqual(data, '\x00\x01\x02\x00')

    def test_set_deactivation_lock(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicy()
        m.req.fru_id = 1
        m.req.mask.deactivation_locked = 1
        m.req.set.deactivation_locked = 1
        data = m.req.encode()
        self.assertEqual(data, '\x00\x01\x02\x02')

class TestReadFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.req.decode('\x01\x02\x03\x04')
        self.assertEqual(m.req.fru_id, 1)
        self.assertEqual(m.req.offset, 0x302)
        self.assertEqual(m.req.count, 4)

    def test_decode_short_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.req.decode, '\x01\x02\x03')

    def test_decode_long_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.req.decode, '\x01\x02\x03\04\x05')

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.req.fru_id = 1
        m.req.offset = 0x302
        m.req.count = 4
        data = m.req.encode()
        self.assertEqual(data, '\x01\x02\x03\x04')

    def test_decode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.decode('\x00\x05\x01\x02\x03\x04\x05')
        self.assertEqual(m.rsp.completion_code, 0)
        self.assertEqual(m.rsp.count, 5)
        self.assertEqual(m.rsp.data, array('c', '\x01\x02\x03\x04\x05'))

    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.decode('\xc0')
        self.assertEqual(m.rsp.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.rsp.decode, '\x00\x01\x01\x02')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0
        m.rsp.count = 5
        m.rsp.data = array('c', '\x01\x02\x03\x04\x05')
        data = m.rsp.encode()
        self.assertEqual(data, '\x00\x05\x01\x02\x03\x04\x05')

    def test_encode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0xc0
        data = m.rsp.encode()
        self.assertEqual(data, '\xc0')

    def test_encode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0
        m.rsp.count = 1
        m.rsp.data = array('c', '\x01\x02')
        self.assertRaises(EncodingError, m.rsp.encode)


class TestGetDeviceId(unittest.TestCase):
    def test_decode_valid_res(self):
        m = pyipmi.msgs.bmc.GetDeviceId()
        m.rsp.decode('\x00\x0c\x89\x00\x00\x02\x3d\x98'
                '\x3a\x00\xbe\x14\x04\x00\x02\x00')
        self.assertEqual(m.rsp.completion_code, 0)
        self.assertEqual(m.rsp.device_id, 0x0c)
        self.assertEqual(m.rsp.device_revision.device_revision, 9)
        self.assertEqual(m.rsp.device_revision.provides_device_sdrs, 1)
        self.assertEqual(m.rsp.firmware_revision.major, 0)
        self.assertEqual(m.rsp.firmware_revision.device_available, 0)
        self.assertEqual(m.rsp.firmware_revision.minor, 0)
        self.assertEqual(m.rsp.ipmi_version, 2)
        self.assertEqual(m.rsp.additional_support.sensor, 1)
        self.assertEqual(m.rsp.additional_support.sdr_repository, 0)
        self.assertEqual(m.rsp.additional_support.sel, 1)
        self.assertEqual(m.rsp.additional_support.fru_inventory, 1)
        self.assertEqual(m.rsp.additional_support.ipmb_event_receiver, 1)
        self.assertEqual(m.rsp.additional_support.ipmb_event_generator, 1)
        self.assertEqual(m.rsp.additional_support.bridge, 0)
        self.assertEqual(m.rsp.additional_support.chassis, 0)
        self.assertEqual(m.rsp.manufacturer_id, 15000)
        self.assertEqual(m.rsp.product_id, 5310)
        self.assertEqual(m.rsp.auxiliary, array('B', [4, 0, 2, 0]))


class TestGetSelEntry(unittest.TestCase):
    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.sel.GetSelEntry()
        m.rsp.decode('\xc0')
        self.assertEqual(m.rsp.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntry()
        self.assertRaises(DecodingError, m.rsp.decode, '\x00\x01')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntry()
        m.rsp.encode('\x00\x02\x01\x01\x02\x03\x04')
        self.assertEqual(m.rsp.completion_code, 0x00)
        self.assertEqual(m.rsp.next_record_id, 0x0102)
        self.assertEqual(m.rsp.record_data, '\x01\x02\x03\x04')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntry()
        m.rsp.completion_code = 0
        m.rsp.next_record_id = 0x0102
        m.rsp.record_data = array('c', '\x01\x02\x03\x04')
        data = m.rsp.encode()
        self.assertEqual(data, '\x00\x02\x01\x01\x02\x03\x04')


class TestGetFruLedState(unittest.TestCase):
    def test_decode_local_control_state(self):
        m = pyipmi.msgs.picmg.GetFruLedState()
        m.rsp.decode('\x00\x00\x01\xff\x00\x02')
        self.assertEqual(m.rsp.completion_code, 0x00)
        self.assertEqual(m.rsp.led_states.local_avail, 1)
        self.assertEqual(m.rsp.local_function, 0xff)
        self.assertEqual(m.rsp.local_on_duration, 0)
        self.assertEqual(m.rsp.local_color, 2)

    def test_decode_override_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedState()
        m.rsp.decode('\x00\x00\x03\xff\x00\x03\xff\x00\x03')
        self.assertEqual(m.rsp.completion_code, 0x00)
        self.assertEqual(m.rsp.led_states.local_avail, 1)
        self.assertEqual(m.rsp.local_function, 0xff)
        self.assertEqual(m.rsp.local_on_duration, 0)
        self.assertEqual(m.rsp.local_color, 3)
        self.assertEqual(m.rsp.led_states.override_en, 1)
        self.assertEqual(m.rsp.override_function, 0xff)
        self.assertEqual(m.rsp.override_on_duration, 0)
        self.assertEqual(m.rsp.override_color, 3)

    def test_decode_lamp_test_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedState()
        m.rsp.decode('\x00\x00\x07\xff\x00\x02\xff\x00\x02\x7f')
        self.assertEqual(m.rsp.completion_code, 0x00)
        self.assertEqual(m.rsp.led_states.local_avail, 1)
        self.assertEqual(m.rsp.local_function, 0xff)
        self.assertEqual(m.rsp.local_on_duration, 0)
        self.assertEqual(m.rsp.local_color, 2)
        self.assertEqual(m.rsp.led_states.override_en, 1)
        self.assertEqual(m.rsp.override_function, 0xff)
        self.assertEqual(m.rsp.override_on_duration, 0)
        self.assertEqual(m.rsp.override_color, 2)
        self.assertEqual(m.rsp.led_states.lamp_test_en, 1)
        self.assertEqual(m.rsp.lamp_test_duration, 0x7f)


class SetSensorThreshold(unittest.TestCase):
    def test_encode_req_set_unr(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.unr = 1
        m.req.threshold.unr = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x20\x00\x00\x00\x00\x00\xaa')

    def test_encode_req_set_ucr(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.ucr = 1
        m.req.threshold.ucr = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x10\x00\x00\x00\x00\xaa\x00')

    def test_encode_req_set_unc(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.unc = 1
        m.req.threshold.unc = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x08\x00\x00\x00\xaa\x00\x00')

    def test_encode_req_set_lnr(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.lnr = 1
        m.req.threshold.lnr = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x04\x00\x00\xaa\x00\x00\x00')

    def test_encode_req_set_lcr(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.lcr = 1
        m.req.threshold.lcr = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x02\x00\xaa\x00\x00\x00\x00')

    def test_encode_req_set_lnc(self):
        m = pyipmi.msgs.sdr.SetSensorThreshold()
        m.req.sensor_number = 0x55
        m.req.set_mask.lnc = 1
        m.req.threshold.lnc = 0xaa
        data = m.req.encode()
        self.assertEqual(data, '\x55\x01\xaa\x00\x00\x00\x00\x00')


if __name__ == '__main__':
    unittest.main()
