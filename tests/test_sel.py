#!/usr/bin/env python

from unittest.mock import MagicMock

import pytest

from pyipmi import interfaces, create_connection
from pyipmi.errors import CompletionCodeError, DecodingError
from pyipmi.msgs.registry import create_response_by_name
from pyipmi.sel import SelEntry, SelInfo
from pyipmi.utils import ByteBuffer

from .ipmi_helper import create_ipmi


class TestSel:

    def test_get_sel_entries(self):
        rsps = list()
        rsp = create_response_by_name('GetSelInfo')
        rsp .entries = 1
        rsps.append(rsp)
        rsp = create_response_by_name('ReserveSel')
        rsps.append(rsp)
        rsp = create_response_by_name('GetSelEntry')
        rsp.record_data = [0, 0, SelEntry.TYPE_SYSTEM_EVENT, 0, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        rsps.append(rsp)
        rsp = create_response_by_name('GetSelEntry')
        rsp.record_data = [0, 0, SelEntry.TYPE_SYSTEM_EVENT, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        rsp.next_record_id = 0xffff
        rsps.append(rsp)

        mock_send_message = MagicMock(side_effect=rsps)
        interface = interfaces.create_interface('mock')
        ipmi = create_connection(interface)
        ipmi.send_message = mock_send_message

        entries = ipmi.get_sel_entries()
        assert len(entries) == 2


class TestSelInfo:

    def test_sel_info(self):
        rsp = create_response_by_name('GetSelInfo')
        rsp.version = 1
        rsp.entries = 1023
        rsp.free_bytes = 512
        info = SelInfo(rsp)

        assert info.version == 1
        assert info.entries == 1023
        assert info.free_bytes == 512

        rsp.operation_support.get_sel_allocation_info = 1
        rsp.operation_support.reserve_sel = 0
        rsp.operation_support.partial_add_sel_entry = 0
        rsp.operation_support.delete_sel = 0
        rsp.operation_support.overflow_flag = 0
        info = SelInfo(rsp)
        assert 'get_sel_allocation_info' in info.operation_support
        assert 'reserve_sel' not in info.operation_support
        assert 'partial_add_sel_entry' not in info.operation_support
        assert 'delete_sel' not in info.operation_support
        assert 'overflow_flag' not in info.operation_support

        rsp.operation_support.get_sel_allocation_info = 0
        rsp.operation_support.reserve_sel = 1
        rsp.operation_support.partial_add_sel_entry = 0
        rsp.operation_support.delete_sel = 0
        rsp.operation_support.overflow_flag = 0
        info = SelInfo(rsp)
        assert 'get_sel_allocation_info' not in info.operation_support
        assert 'reserve_sel' in info.operation_support
        assert 'partial_add_sel_entry' not in info.operation_support
        assert 'delete_sel' not in info.operation_support
        assert 'overflow_flag' not in info.operation_support

        rsp.operation_support.get_sel_allocation_info = 0
        rsp.operation_support.reserve_sel = 0
        rsp.operation_support.partial_add_sel_entry = 1
        rsp.operation_support.delete_sel = 0
        rsp.operation_support.overflow_flag = 0
        info = SelInfo(rsp)
        assert 'get_sel_allocation_info' not in info.operation_support
        assert 'reserve_sel' not in info.operation_support
        assert 'partial_add_sel_entry' in info.operation_support
        assert 'delete_sel' not in info.operation_support
        assert 'overflow_flag' not in info.operation_support

        rsp.operation_support.get_sel_allocation_info = 0
        rsp.operation_support.reserve_sel = 0
        rsp.operation_support.partial_add_sel_entry = 0
        rsp.operation_support.delete_sel = 1
        rsp.operation_support.overflow_flag = 0
        info = SelInfo(rsp)
        assert 'get_sel_allocation_info' not in info.operation_support
        assert 'reserve_sel' not in info.operation_support
        assert 'partial_add_sel_entry' not in info.operation_support
        assert 'delete_sel' in info.operation_support
        assert 'overflow_flag' not in info.operation_support

        rsp.operation_support.get_sel_allocation_info = 0
        rsp.operation_support.reserve_sel = 0
        rsp.operation_support.partial_add_sel_entry = 0
        rsp.operation_support.delete_sel = 0
        rsp.operation_support.overflow_flag = 1
        info = SelInfo(rsp)
        assert 'get_sel_allocation_info' not in info.operation_support
        assert 'reserve_sel' not in info.operation_support
        assert 'partial_add_sel_entry' not in info.operation_support
        assert 'delete_sel' not in info.operation_support
        assert 'overflow_flag' in info.operation_support


class TestSelEnty:

    def test_from_data(self):
        data = [0xff, 0x03, 0x02, 0xf7, 0x61, 0xef, 0x52, 0x7e,
                0x00, 0x04, 0xf2, 0x09, 0x7f, 0x00, 0xff, 0xff]
        entry = SelEntry(data)
        assert entry.type == 2
        assert entry.sensor_type == 0xf2

    def test_from_data_event_direction(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x7f, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        assert entry.event_direction == 0

        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        assert entry.event_direction == 1

    def test_from_data_event_type(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        assert entry.event_type == 0x7f

        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        assert entry.event_type == 0x00

    def test_from_data_event_data(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x11, 0x22, 0x33]
        entry = SelEntry(data)
        assert entry.event_data[0] == 0x11
        assert entry.event_data[1] == 0x22
        assert entry.event_data[2] == 0x33

    def test_type_to_string(self):
        assert SelEntry.type_to_string(0) is None
        assert SelEntry.type_to_string(0x02) == 'System Event'
        assert SelEntry.type_to_string(0xc0) == 'OEM timestamped (0xc0)'
        assert SelEntry.type_to_string(0xe0) == 'OEM non-timestamped (0xe0)'


# system event record 0x0001: timestamp 0x12345678, generator 0x0020,
# sensor type 0x01 (temperature) number 4, assertion, threshold event
SEL_RECORD = (b'\x01\x00\x02\x78\x56\x34\x12\x20'
              b'\x00\x04\x01\x04\x01\x52\x00\x00')


def test_sel_entry_str():
    entry = SelEntry(ByteBuffer(SEL_RECORD))
    assert entry.record_id == 1
    assert entry.timestamp == 0x12345678
    s = str(entry)
    assert 'SEL Record ID 0x0001' in s
    assert 'Sensor Type: 0x01' in s
    assert 'Sensor Number: 4' in s


@pytest.mark.parametrize('entry_type, string', [
    (0x02, 'System Event'),
    (0xc0, 'OEM timestamped (0xc0)'),
    (0xe0, 'OEM non-timestamped (0xe0)'),
    (0x10, None),
])
def test_sel_entry_type_to_string(entry_type, string):
    assert SelEntry.type_to_string(entry_type) == string


@pytest.mark.parametrize('data', [SEL_RECORD[:15],
                                  SEL_RECORD[:2] + b'\x10' + SEL_RECORD[3:]])
def test_sel_entry_invalid(data):
    with pytest.raises(DecodingError):
        SelEntry(ByteBuffer(data))


def test_get_sel_entry():
    ipmi = create_ipmi({'GetSelEntry': b'\x00\xff\xff' + SEL_RECORD})
    (entry, next_id) = ipmi.get_sel_entry(1, reservation=0x1234)
    assert ipmi.requests == [('GetSelEntryReq', b'\x34\x12\x01\x00\x00\xff')]
    assert entry.record_id == 1
    assert next_id == 0xffff


def test_get_sel_entry_partial_reads():
    # the device can't return the entire record, it is read in pieces
    ipmi = create_ipmi({'GetSelEntry': [
        b'\xca',
        b'\xca',
        b'\x00\xff\xff' + SEL_RECORD[:15],
        b'\x00\xff\xff' + SEL_RECORD[15:],
    ]})
    (entry, _) = ipmi.get_sel_entry(1)
    assert bytes(entry.data) == SEL_RECORD
    # entire record (0xff), then 16 bytes, then 15 bytes and the last one
    assert [data[-2:] for (_, data) in ipmi.requests] == [
        b'\x00\xff', b'\x00\x10', b'\x00\x0f', b'\x0f\x01']


def test_delete_sel_entry():
    ipmi = create_ipmi({'DeleteSelEntry': b'\x00\x01\x00'})
    assert ipmi.delete_sel_entry(1, reservation=0x1234) == 1
    assert ipmi.requests == [('DeleteSelEntryReq', b'\x34\x12\x01\x00')]


def test_get_and_clear_sel_entry():
    ipmi = create_ipmi({
        'ReserveSel': [b'\x00\x01\x00', b'\x00\x02\x00', b'\x00\x03\x00'],
        # the reservation is canceled while reading and while deleting
        'GetSelEntry': [b'\xc5', b'\x00\xff\xff' + SEL_RECORD,
                        b'\x00\xff\xff' + SEL_RECORD],
        'DeleteSelEntry': [b'\xc5', b'\x00\x01\x00'],
    })
    entry = ipmi.get_and_clear_sel_entry(1)
    assert entry.record_id == 1
    assert ipmi.requests[-1] == ('DeleteSelEntryReq', b'\x03\x00\x01\x00')


@pytest.mark.parametrize('command', ['GetSelEntry', 'DeleteSelEntry'])
def test_get_and_clear_sel_entry_error(command):
    rsp = {'ReserveSel': b'\x00\x01\x00',
           'GetSelEntry': b'\x00\xff\xff' + SEL_RECORD,
           'DeleteSelEntry': b'\x00\x01\x00'}
    rsp[command] = b'\xcb'
    ipmi = create_ipmi(rsp)
    with pytest.raises(CompletionCodeError):
        ipmi.get_and_clear_sel_entry(1)


def test_clear_sel(monkeypatch):
    monkeypatch.setattr('pyipmi.helper.time.sleep', lambda t: None)
    ipmi = create_ipmi({'ReserveSel': b'\x00\x34\x12',
                        'ClearSel': [b'\x00\x01', b'\x00\x00',
                                     b'\x00\x01']})
    ipmi.clear_sel()
    # 'CLR' with initiate erase, then get erase status until completed
    assert ipmi.requests[1:] == [
        ('ClearSelReq', b'\x34\x12CLR\xaa'),
        ('ClearSelReq', b'\x34\x12CLR\x00'),
        ('ClearSelReq', b'\x34\x12CLR\x00')]


def sel_entry(record_type=0x02, timestamp=0x12345678, generator_id=0x0020,
              sensor_type=0x01, sensor_number=4, event_desc=0x01,
              event_data=(0x52, 0x00, 0x00)):
    data = (b'\x01\x00' + bytes([record_type])
            + timestamp.to_bytes(4, 'little')
            + generator_id.to_bytes(2, 'little')
            + bytes([0x04, sensor_type, sensor_number, event_desc])
            + bytes(event_data))
    return SelEntry(ByteBuffer(data))


@pytest.mark.parametrize('sensor_type, string', [
    (0x01, 'Temperature'),
    (0x2c, 'FRU State'),
    (0xf0, 'FRU Hot Swap'),
    (0xc5, 'OEM (0xc5)'),
    (0x00, 'Unknown (0x00)'),
])
def test_sel_entry_sensor_type_to_string(sensor_type, string):
    assert SelEntry.sensor_type_to_string(sensor_type) == string


@pytest.mark.parametrize('record_type, timestamp, string', [
    (0x02, 0x68201000, '2025-05-11 02:48:32'),
    (0x02, 0x10, 'Pre-Init 16s'),
    (0x02, 0x20000000, 'Pre-Init 536870912s'),
    (0x02, 0xffffffff, 'Unspecified'),
    (0xc0, 0x68201000, '2025-05-11 02:48:32'),
    (0xe0, 0x68201000, 'Unspecified'),
])
def test_sel_entry_timestamp_to_string(record_type, timestamp, string):
    entry = sel_entry(record_type=record_type, timestamp=timestamp)
    assert entry.timestamp_to_string() == string


@pytest.mark.parametrize('generator_id, string', [
    (0x0020, 'IPMB 0x20 LUN 0'),
    (0x0282, 'IPMB 0x82 LUN 2'),
    (0x0041, 'Software 0x20'),
    (0x7020, 'IPMB 0x20 LUN 0 channel 7'),
])
def test_sel_entry_generator_to_string(generator_id, string):
    entry = sel_entry(generator_id=generator_id)
    assert entry.generator_to_string() == string


@pytest.mark.parametrize('sensor_type, event_desc, event_data, string', [
    # generic threshold event
    (0x01, 0x01, (0x59, 0, 0), 'Upper Critical going high'),
    # generic discrete event
    (0x25, 0x08, (0x01, 0, 0), 'Device Present'),
    # sensor-specific events
    (0x08, 0x6f, (0x01, 0, 0), 'Power Supply Failure Detected'),
    (0xf0, 0x6f, (0x04, 0, 0), 'M4 - FRU Active'),
    # the direction is not part of the event type
    (0x2c, 0xef, (0x04, 0, 0), 'FRU Active'),
    # unknown offsets and types
    (0x01, 0x01, (0x0c, 0, 0), 'Event Type 0x01 Offset 0x0c'),
    (0x23, 0x6f, (0x04, 0, 0), 'Event Type 0x6f Offset 0x04'),
    (0xc0, 0x6f, (0x01, 0, 0), 'Event Type 0x6f Offset 0x01'),
    (0xc0, 0x70, (0x01, 0, 0), 'OEM Event Type 0x70 Offset 0x01'),
])
def test_sel_entry_event_to_string(sensor_type, event_desc, event_data,
                                   string):
    entry = sel_entry(sensor_type=sensor_type, event_desc=event_desc,
                      event_data=event_data)
    assert entry.event_to_string() == string


def test_sel_entry_direction_to_string():
    assert sel_entry(event_desc=0x01).direction_to_string() == 'Asserted'
    assert sel_entry(event_desc=0x81).direction_to_string() == 'Deasserted'


@pytest.mark.parametrize('event_desc, event_data, values', [
    (0x01, (0x59, 0x55, 0x50), (0x55, 0x50)),
    (0x01, (0x49, 0x55, 0x50), (0x55, None)),
    (0x01, (0x19, 0x55, 0x50), (None, 0x50)),
    (0x01, (0x09, 0x55, 0x50), (None, None)),
    (0x6f, (0x59, 0x55, 0x50), (None, None)),
])
def test_sel_entry_threshold_event_values(event_desc, event_data, values):
    entry = sel_entry(event_desc=event_desc, event_data=event_data)
    assert entry.threshold_event_values() == values
