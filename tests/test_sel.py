#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, ok_

from pyipmi.msgs.registry import create_response_by_name
from pyipmi.sel import SelEntry, SelInfo


class TestSelInfo(object):
    rsp = create_response_by_name('GetSelInfo')
    rsp.version = 1
    rsp.entries = 1023
    rsp.free_bytes = 512
    info = SelInfo(rsp)

    eq_(info.version, 1)
    eq_(info.entries, 1023)
    eq_(info.free_bytes, 512)

    rsp.operation_support.get_sel_allocation_info = 1
    rsp.operation_support.reserve_sel = 0
    rsp.operation_support.partial_add_sel_entry = 0
    rsp.operation_support.delete_sel = 0
    rsp.operation_support.overflow_flag = 0
    info = SelInfo(rsp)
    ok_('get_sel_allocation_info' in info.operation_support)
    ok_('reserve_sel' not in info.operation_support)
    ok_('partial_add_sel_entry' not in info.operation_support)
    ok_('delete_sel' not in info.operation_support)
    ok_('overflow_flag' not in info.operation_support)

    rsp.operation_support.get_sel_allocation_info = 0
    rsp.operation_support.reserve_sel = 1
    rsp.operation_support.partial_add_sel_entry = 0
    rsp.operation_support.delete_sel = 0
    rsp.operation_support.overflow_flag = 0
    info = SelInfo(rsp)
    ok_('get_sel_allocation_info' not in info.operation_support)
    ok_('reserve_sel' in info.operation_support)
    ok_('partial_add_sel_entry' not in info.operation_support)
    ok_('delete_sel' not in info.operation_support)
    ok_('overflow_flag' not in info.operation_support)

    rsp.operation_support.get_sel_allocation_info = 0
    rsp.operation_support.reserve_sel = 0
    rsp.operation_support.partial_add_sel_entry = 1
    rsp.operation_support.delete_sel = 0
    rsp.operation_support.overflow_flag = 0
    info = SelInfo(rsp)
    ok_('get_sel_allocation_info' not in info.operation_support)
    ok_('reserve_sel' not in info.operation_support)
    ok_('partial_add_sel_entry' in info.operation_support)
    ok_('delete_sel' not in info.operation_support)
    ok_('overflow_flag' not in info.operation_support)

    rsp.operation_support.get_sel_allocation_info = 0
    rsp.operation_support.reserve_sel = 0
    rsp.operation_support.partial_add_sel_entry = 0
    rsp.operation_support.delete_sel = 1
    rsp.operation_support.overflow_flag = 0
    info = SelInfo(rsp)
    ok_('get_sel_allocation_info' not in info.operation_support)
    ok_('reserve_sel' not in info.operation_support)
    ok_('partial_add_sel_entry' not in info.operation_support)
    ok_('delete_sel' in info.operation_support)
    ok_('overflow_flag' not in info.operation_support)

    rsp.operation_support.get_sel_allocation_info = 0
    rsp.operation_support.reserve_sel = 0
    rsp.operation_support.partial_add_sel_entry = 0
    rsp.operation_support.delete_sel = 0
    rsp.operation_support.overflow_flag = 1
    info = SelInfo(rsp)
    ok_('get_sel_allocation_info' not in info.operation_support)
    ok_('reserve_sel' not in info.operation_support)
    ok_('partial_add_sel_entry' not in info.operation_support)
    ok_('delete_sel' not in info.operation_support)
    ok_('overflow_flag' in info.operation_support)


class TestSelEnty(object):

    def test_from_data(self):
        data = [0xff, 0x03, 0x02, 0xf7, 0x61, 0xef, 0x52, 0x7e,
                0x00, 0x04, 0xf2, 0x09, 0x7f, 0x00, 0xff, 0xff]
        entry = SelEntry(data)
        eq_(entry.type, 2)
        eq_(entry.sensor_type, 0xf2)

    def test_from_data_event_direction(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x7f, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        eq_(entry.event_direction, 0)

        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        eq_(entry.event_direction, 1)

    def test_from_data_event_type(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        eq_(entry.event_type, 0x7f)

        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00]
        entry = SelEntry(data)
        eq_(entry.event_type, 0x00)

    def test_from_data_event_data(self):
        data = [0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0xff, 0x11, 0x22, 0x33]
        entry = SelEntry(data)
        eq_(entry.event_data[0], 0x11)
        eq_(entry.event_data[1], 0x22)
        eq_(entry.event_data[2], 0x33)

    def test_type_to_string(self):
        eq_(SelEntry.type_to_string(0), None)
        eq_(SelEntry.type_to_string(0x02),
            'System Event')
        eq_(SelEntry.type_to_string(0xc0),
            'OEM timestamped (0xc0)')
        eq_(SelEntry.type_to_string(0xe0),
            'OEM non-timestamped (0xe0)')
