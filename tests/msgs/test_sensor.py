#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.sensor

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


class TestGetDeviceSdrInfo(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.GetDeviceSdrInfoReq()
        data = encode_message(m)
        self.assertEqual(data, '')

    def test_encode_rsp(self):
        m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
        decode_message(m, '\x00\x03\x05')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.number_of_sensors, 3)
        self.assertEqual(m.flags.lun0_has_sensors, 1)
        self.assertEqual(m.flags.lun1_has_sensors, 0)
        self.assertEqual(m.flags.lun2_has_sensors, 1)
        self.assertEqual(m.flags.lun3_has_sensors, 0)
        self.assertEqual(m.flags.dynamic_population, 0)

    def test_encode_rsp_with_timestamp(self):
        m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
        decode_message(m, '\x00\x12\x01\xaa\xbb\xcc\xdd')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.number_of_sensors, 0x12)
        self.assertEqual(m.flags.lun0_has_sensors, 1)
        self.assertEqual(m.flags.lun1_has_sensors, 0)
        self.assertEqual(m.flags.lun2_has_sensors, 0)
        self.assertEqual(m.flags.lun3_has_sensors, 0)
        self.assertEqual(m.flags.dynamic_population, 0)
        self.assertEqual(m.sensor_population_change, 0xddccbbaa)


class TestGetDeviceSdr(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.GetDeviceSdrReq()
        m.reservation_id = 0x0123
        m.record_id = 0x4567
        m.offset = 0x89
        m.bytes_to_read = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\x23\x01\x67\x45\x89\xab')

    def test_decode_rsp(self):
        m = pyipmi.msgs.sensor.GetDeviceSdrRsp()
        decode_message(m, '\x00\x01\x23\xaa\xbb')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.next_record_id, 0x2301)
        self.assertEqual(m.record_data, array('B', [0xaa, 0xbb]) )


class TestSetSensorHysteresis(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.SetSensorHysteresisReq()
        m.sensor_number = 0xab
        m.positive_going_hysteresis = 0xaa
        m.negative_going_hysteresis = 0xbb
        data = encode_message(m)
        self.assertEqual(data, '\xab\xff\xaa\xbb')


class TestGetSensorHysteresis(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.GetSensorHysteresisReq()
        m.sensor_number = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\xab\xff')

    def test_decode_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorHysteresisRsp()
        decode_message(m, '\x00\xaa\xbb')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.positive_going_hysteresis, 0xaa)
        self.assertEqual(m.negative_going_hysteresis, 0xbb)


class TestSetSensorThresholds(unittest.TestCase):
    def test_encode_req_set_unr(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.unr = 1
        m.threshold.unr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x20\x00\x00\x00\x00\x00\xaa')

    def test_encode_req_set_ucr(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.ucr = 1
        m.threshold.ucr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x10\x00\x00\x00\x00\xaa\x00')

    def test_encode_req_set_unc(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.unc = 1
        m.threshold.unc = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x08\x00\x00\x00\xaa\x00\x00')

    def test_encode_req_set_lnr(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.lnr = 1
        m.threshold.lnr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x04\x00\x00\xaa\x00\x00\x00')

    def test_encode_req_set_lcr(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.lcr = 1
        m.threshold.lcr = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x02\x00\xaa\x00\x00\x00\x00')

    def test_encode_req_set_lnc(self):
        m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
        m.sensor_number = 0x55
        m.set_mask.lnc = 1
        m.threshold.lnc = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\x55\x01\xaa\x00\x00\x00\x00\x00')


class TestSetSensorEventEnable(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00')

    def test_encode_cfg_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 2
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x20')

    def test_encode_scanning_enabled_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 1
        data = encode_message(m)
        self.assertEqual(data, '\xab\x40')

    def test_encode_event_enabled_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 1
        m.enable.sensor_scanning = 0
        data = encode_message(m)
        self.assertEqual(data, '\xab\x80')

    def test_encode_byte3_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
        m.sensor_number = 0xab
        m.enable.config = 0
        m.enable.event_message = 0
        m.enable.sensor_scanning = 0
        m.byte3 = 0xaa
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00\xaa')

    def test_encode_byte34_req(self):
        m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
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
        m = pyipmi.msgs.sensor.GetSensorEventEnableReq()
        m.sensor_number = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\xab')

    def test_decode_event_enabled_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
        decode_message(m, '\x00\x80')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.enabled.sensor_scanning, 0)

    def test_decode_scanning_enabled_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
        decode_message(m, '\x00\x40')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 0)
        self.assertEqual(m.enabled.sensor_scanning, 1)

    def test_decode_byte3_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)

    def test_decode_byte34_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa\xbb')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)
        self.assertEqual(m.byte4, 0xbb)

    def test_decode_byte34_rsp(self):
        m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
        decode_message(m, '\x00\xc0\xaa\xbb\xcc\xdd')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.enabled.event_message, 1)
        self.assertEqual(m.byte3, 0xaa)
        self.assertEqual(m.byte4, 0xbb)
        self.assertEqual(m.byte5, 0xcc)
        self.assertEqual(m.byte6, 0xdd)


class TestRearmSensorEvents(unittest.TestCase):
    def test_encode_req(self):
        m = pyipmi.msgs.sensor.RearmSensorEventsReq()
        m.sensor_number = 0xab
        data = encode_message(m)
        self.assertEqual(data, '\xab\x00\x00\x00\x00\x00')

    def test_decode_rsp(self):
        m = pyipmi.msgs.sensor.RearmSensorEventsRsp()
        decode_message(m, '\x00')
        self.assertEqual(m.completion_code, 0x00)

if __name__ == '__main__':
    unittest.main()
