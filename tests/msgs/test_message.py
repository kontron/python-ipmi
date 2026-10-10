#!/usr/bin/env python

from array import array

import pytest

import pyipmi.msgs.bmc
import pyipmi.msgs.fru

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import (create_request_by_name, create_response_by_name,
                         decode_message, encode_message)
from pyipmi.utils import ByteBuffer
from pyipmi.msgs.message import (Bitfield, Message, UnsignedInt,
                                 RemainingBytes, String)


class TMessage:
    def __init__(self, field):
        setattr(self, field.name, field.create())
        self.field = field

    def encode(self):
        data = ByteBuffer()
        self.field.encode(self, data)
        return data

    def decode(self, data):
        data = ByteBuffer(data)
        self.field.decode(self, data)


def test_bitfield_encode():
    t = TMessage(Bitfield('status', 1,
                          Bitfield.Bit('erase_in_progress', 4),
                          Bitfield.ReservedBit(4, 0),))
    t.status.erase_in_progress = 1
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x1])


@pytest.mark.parametrize('value', [16, 0xff, -1])
def test_bitfield_encode_out_of_range(value):
    # the value must not be truncated silently
    t = TMessage(Bitfield('status', 1,
                          Bitfield.Bit('erase_in_progress', 4),
                          Bitfield.ReservedBit(4, 0),))
    t.status.erase_in_progress = value
    with pytest.raises(EncodingError):
        t.encode()


def test_unsignedint_encode_out_of_range():
    t = TMessage(UnsignedInt('test', 2))
    t.test = 70000
    with pytest.raises(EncodingError):
        t.encode()


def test_unsignedint_encode():
    t = TMessage(UnsignedInt('test', 4))
    t.test = 0x12345678
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x78, 0x56, 0x34, 0x12])

    t = TMessage(UnsignedInt('test', 8))
    t.test = 0x12345678
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0x78, 0x56, 0x34, 0x12, 0, 0, 0, 0])


def test_unsignedint_decode():
    t = TMessage(UnsignedInt('test', 1))
    t.decode(b'\x12')
    assert t.test == 0x12

    t.decode(b'\xd7')
    assert t.test == 0xd7


def test_string_encode():
    # padded with NUL bytes to the length of the field
    t = TMessage(String('test', 10))
    t.test = '1234'
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', b'1234' + b'\x00' * 6)

    t.test = b'0123456789'
    assert t.encode().array == array('B', b'0123456789')


def test_string_encode_too_long():
    t = TMessage(String('test', 10))
    t.test = '01234567890'
    with pytest.raises(EncodingError):
        t.encode()


def test_string_decode():
    t = TMessage(String('test', 10))
    t.decode(b'abcdefghij')
    assert t.test == b'abcdefghij'


def test_string_decode_too_short():
    t = TMessage(String('test', 10))
    with pytest.raises(DecodingError):
        t.decode(b'abcdef')


def test_session_challenge_truncated():
    # a truncated challenge string must not be used for the session
    rsp = create_response_by_name('GetSessionChallenge')
    with pytest.raises(DecodingError):
        decode_message(rsp, b'\x00\x01\x02\x03\x04abc')


def test_remainingbytes_encode():
    t = TMessage(RemainingBytes('test'))
    t.test = [0xb4, 1]
    byte_buffer = t.encode()
    assert byte_buffer.array == array('B', [0xb4, 0x01])


def test_message():
    msg = Message()
    msg.__netfn__ = 0x1
    msg.__cmdid__ = 0x2

    assert msg.lun == 0
    assert msg.netfn == 1
    assert msg.cmdid == 2


def test_message_encode_out_of_range():
    # channel 16 was sent as channel 0, a power limit of 70000 W as 4464 W
    req = create_request_by_name('GetChannelInfo')
    req.channel.number = 16
    with pytest.raises(EncodingError):
        encode_message(req)

    req = create_request_by_name('SetPowerLimit')
    req.power_limit = 70000
    with pytest.raises(EncodingError):
        encode_message(req)


def test_message_kwargs():
    req = create_request_by_name('GetSdr', reservation_id=0x1234,
                                 record_id=1, offset=5, bytes_to_read=16)
    assert encode_message(req) == b'\x34\x12\x01\x00\x05\x10'

    # a bitfield from its value as integer
    req = create_request_by_name('GetChannelInfo', channel=7)
    assert req.channel.number == 7
    assert encode_message(req) == b'\x07'

    # a field named 'data'
    req = create_request_by_name('WriteFruData', fru_id=1, offset=2,
                                 data=array('B', b'\xaa'))
    assert encode_message(req) == b'\x01\x02\x00\xaa'


def test_message_kwargs_unknown_field():
    with pytest.raises(TypeError, match='no field'):
        create_request_by_name('GetSdr', recordid=1)


def test_message_data_field_not_replaced():
    # the field 'data' keeps its default value, it is not replaced by ''
    req = create_request_by_name('ManufacturingTestOn')
    assert not isinstance(req.data, str)
    req.data.extend(b'\x01')


def test_field_values():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    pyipmi.msgs.decode_message(
        rsp, bytes.fromhex('00 0c 89 00 00 02 3d 98 3a 00 be 14'))
    values = rsp.field_values()
    assert list(values)[:3] == ['completion_code', 'device_id',
                                'device_revision']
    assert values['device_id'] == 0x0c
    # a bitfield as dict of its bits, without the reserved bits
    assert values['device_revision'] == {'device_revision': 9,
                                         'provides_device_sdrs': 1}
    # the optional auxiliary field is not in the message
    assert 'auxiliary' not in values


def test_field_values_without_fields():
    assert pyipmi.msgs.bmc.GetDeviceIdReq().field_values() == {}


def test_format_fields():
    rsp = pyipmi.msgs.fru.ReadFruDataRsp()
    pyipmi.msgs.decode_message(rsp, bytes.fromhex('00 03 01 02 ff'))
    assert rsp.format_fields() == [('completion_code', '0x00 (0)'),
                                   ('count', '0x03 (3)'),
                                   ('data', '01 02 ff')]

    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    pyipmi.msgs.decode_message(
        rsp, bytes.fromhex('00 0c 89 00 00 02 3d 98 3a 00 be 14'))
    fields = dict(rsp.format_fields())
    # the raw value first, in hex with the length of the field
    assert fields['device_id'] == '0x0c (12)'
    assert fields['manufacturer_id'] == '0x003a98 (15000)'
    assert fields['device_revision'] == ('[0x89] device_revision=9, '
                                         'provides_device_sdrs=1')
