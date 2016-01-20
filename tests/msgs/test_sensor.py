#!/usr/bin/env python

from array import array

from nose.tools import eq_, raises

import pyipmi.msgs.sensor

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getdevicesdrinfo_encode_req():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoReq()
    data = encode_message(m)
    eq_(data, '')

def test_getdevicesdrinfo_encode_rsp():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
    decode_message(m, '\x00\x03\x05')
    eq_(m.completion_code, 0x00)
    eq_(m.number_of_sensors, 3)
    eq_(m.flags.lun0_has_sensors, 1)
    eq_(m.flags.lun1_has_sensors, 0)
    eq_(m.flags.lun2_has_sensors, 1)
    eq_(m.flags.lun3_has_sensors, 0)
    eq_(m.flags.dynamic_population, 0)

def test_getdevicesdrinfo_encode_rsp_with_timestamp():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
    decode_message(m, '\x00\x12\x01\xaa\xbb\xcc\xdd')
    eq_(m.completion_code, 0x00)
    eq_(m.number_of_sensors, 0x12)
    eq_(m.flags.lun0_has_sensors, 1)
    eq_(m.flags.lun1_has_sensors, 0)
    eq_(m.flags.lun2_has_sensors, 0)
    eq_(m.flags.lun3_has_sensors, 0)
    eq_(m.flags.dynamic_population, 0)
    eq_(m.sensor_population_change, 0xddccbbaa)

def test_getdevicesdr_encode_req():
    m = pyipmi.msgs.sensor.GetDeviceSdrReq()
    m.reservation_id = 0x0123
    m.record_id = 0x4567
    m.offset = 0x89
    m.bytes_to_read = 0xab
    data = encode_message(m)
    eq_(data, '\x23\x01\x67\x45\x89\xab')

def test_getdevicesdr_decode_rsp():
    m = pyipmi.msgs.sensor.GetDeviceSdrRsp()
    decode_message(m, '\x00\x01\x23\xaa\xbb')
    eq_(m.completion_code, 0x00)
    eq_(m.next_record_id, 0x2301)
    eq_(m.record_data, array('B', [0xaa, 0xbb]) )

def test_setsensorhysteresis_encode_req():
    m = pyipmi.msgs.sensor.SetSensorHysteresisReq()
    m.sensor_number = 0xab
    m.positive_going_hysteresis = 0xaa
    m.negative_going_hysteresis = 0xbb
    data = encode_message(m)
    eq_(data, '\xab\xff\xaa\xbb')

def test_getsensorhysteresis_encode_req():
    m = pyipmi.msgs.sensor.GetSensorHysteresisReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    eq_(data, '\xab\xff')

def test_getsensorhysteresis_decode_rsp():
    m = pyipmi.msgs.sensor.GetSensorHysteresisRsp()
    decode_message(m, '\x00\xaa\xbb')
    eq_(m.completion_code, 0x00)
    eq_(m.positive_going_hysteresis, 0xaa)
    eq_(m.negative_going_hysteresis, 0xbb)

def test_setsensorthresholds_encode_req_set_unr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.unr = 1
    m.threshold.unr = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x20\x00\x00\x00\x00\x00\xaa')

def test_setsensorthresholds_encode_req_set_ucr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.ucr = 1
    m.threshold.ucr = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x10\x00\x00\x00\x00\xaa\x00')

def test_setsensorthresholds_encode_req_set_unc():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.unc = 1
    m.threshold.unc = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x08\x00\x00\x00\xaa\x00\x00')

def test_setsensorthresholds_encode_req_set_lnr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lnr = 1
    m.threshold.lnr = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x04\x00\x00\xaa\x00\x00\x00')

def test_setsensorthresholds_encode_req_set_lcr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lcr = 1
    m.threshold.lcr = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x02\x00\xaa\x00\x00\x00\x00')

def test_setsensorthresholds_encode_req_set_lnc():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lnc = 1
    m.threshold.lnc = 0xaa
    data = encode_message(m)
    eq_(data, '\x55\x01\xaa\x00\x00\x00\x00\x00')

def test_setsensoreventenable_encode_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    eq_(data, '\xab\x00')

def test_setsensoreventenable_encode_cfg_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 2
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    eq_(data, '\xab\x20')

def test_setsensoreventenable_encode_scanning_enabled_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 1
    data = encode_message(m)
    eq_(data, '\xab\x40')

def test_setsensoreventenable_encode_event_enabled_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 1
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    eq_(data, '\xab\x80')

def test_setsensoreventenable_encode_byte3_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    m.byte3 = 0xaa
    data = encode_message(m)
    eq_(data, '\xab\x00\xaa')

def test_setsensoreventenable_encode_byte34_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    m.byte3 = 0xaa
    m.byte4 = 0xbb
    data = encode_message(m)
    eq_(data, '\xab\x00\xaa\xbb')

def test_getsensoreventenable_encode_req():
    m = pyipmi.msgs.sensor.GetSensorEventEnableReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    eq_(data, '\xab')

def test_getsensoreventenable_decode_event_enabled_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, '\x00\x80')
    eq_(m.completion_code, 0x00)
    eq_(m.enabled.event_message, 1)
    eq_(m.enabled.sensor_scanning, 0)

def test_getsensoreventenable_decode_scanning_enabled_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, '\x00\x40')
    eq_(m.completion_code, 0x00)
    eq_(m.enabled.event_message, 0)
    eq_(m.enabled.sensor_scanning, 1)

def test_getsensoreventenable_decode_byte3_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, '\x00\xc0\xaa')
    eq_(m.completion_code, 0x00)
    eq_(m.enabled.event_message, 1)
    eq_(m.byte3, 0xaa)

def test_getsensoreventenable_decode_byte34_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, '\x00\xc0\xaa\xbb')
    eq_(m.completion_code, 0x00)
    eq_(m.enabled.event_message, 1)
    eq_(m.byte3, 0xaa)
    eq_(m.byte4, 0xbb)

def test_getsensoreventenable_decode_byte34_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, '\x00\xc0\xaa\xbb\xcc\xdd')
    eq_(m.completion_code, 0x00)
    eq_(m.enabled.event_message, 1)
    eq_(m.byte3, 0xaa)
    eq_(m.byte4, 0xbb)
    eq_(m.byte5, 0xcc)
    eq_(m.byte6, 0xdd)

def test_rearmsensorevents_encode_req():
    m = pyipmi.msgs.sensor.RearmSensorEventsReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    eq_(data, '\xab\x00\x00\x00\x00\x00')

def test_rearmsensorevents_decode_rsp():
    m = pyipmi.msgs.sensor.RearmSensorEventsRsp()
    decode_message(m, '\x00')
    eq_(m.completion_code, 0x00)
