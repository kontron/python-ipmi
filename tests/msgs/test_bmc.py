#!/usr/bin/env python

from array import array

from nose.tools import eq_

import pyipmi.msgs.bmc

from pyipmi.msgs import decode_message


def test_getdeviceid_decode_rsp_with_cc():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\xc0')
    eq_(m.completion_code, 0xc0)


def test_getdeviceid_decode_valid_res():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                      b'\x3a\x00\xbe\x14\x04\x00\x02\x00')
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
    eq_(m.auxiliary, array('B', [4, 0, 2, 0]))


def test_getdeviceid_decode_valid_res_wo_aux():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                      b'\x3a\x00\xbe\x14')
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
    decode_message(m, b'\x00\x55\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x55)
    eq_(int(m.status), 0x00)


def test_getselftestresults_decode_test_fail_not_implemented_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x56\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.result, 0x56)
    eq_(int(m.status), 0x00)


def test_getselftestresults_decode_test_fail_corrupted_sel_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x57\x80')
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
    decode_message(m, b'\x00\x57\x40')
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


def test_getselftestresults_decode_test_fail_corrupted_fru_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x57\x20')
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
