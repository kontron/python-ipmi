import unittest
from array import array

import pyipmi.msgs.fru
from pyipmi.errors import DecodingError, EncodingError

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

if __name__ == '__main__':
    unittest.main()
