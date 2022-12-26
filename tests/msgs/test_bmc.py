#!/usr/bin/env python

from array import array

import pyipmi.msgs.bmc

from pyipmi.msgs import decode_message


def test_getdeviceid_decode_req():
    m = pyipmi.msgs.bmc.GetDeviceIdReq()
    decode_message(m, b'')


def test_getdeviceid_decode_rsp_with_cc():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\xc0')
    assert m.completion_code == 0xc0


def test_getdeviceid_decode_valid_rsp():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                      b'\x3a\x00\xbe\x14\x04\x00\x02\x00')
    assert m.completion_code == 0
    assert m.device_id == 0x0c
    assert m.device_revision.device_revision == 9
    assert m.device_revision.provides_device_sdrs == 1
    assert m.firmware_revision.major == 0
    assert m.firmware_revision.device_available == 0
    assert m.firmware_revision.minor == 0
    assert m.ipmi_version == 2
    assert m.additional_support.sensor == 1
    assert m.additional_support.sdr_repository == 0
    assert m.additional_support.sel == 1
    assert m.additional_support.fru_inventory == 1
    assert m.additional_support.ipmb_event_receiver == 1
    assert m.additional_support.ipmb_event_generator == 1
    assert m.additional_support.bridge == 0
    assert m.additional_support.chassis == 0
    assert m.manufacturer_id == 15000
    assert m.product_id == 5310
    assert m.auxiliary == array('B', [4, 0, 2, 0])


def test_getdeviceid_decode_valid_rsp_wo_aux():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                      b'\x3a\x00\xbe\x14')
    assert m.completion_code == 0
    assert m.device_id == 0x0c
    assert m.device_revision.device_revision == 9
    assert m.device_revision.provides_device_sdrs == 1
    assert m.firmware_revision.major == 0
    assert m.firmware_revision.device_available == 0
    assert m.firmware_revision.minor == 0
    assert m.ipmi_version == 2
    assert m.additional_support.sensor == 1
    assert m.additional_support.sdr_repository == 0
    assert m.additional_support.sel == 1
    assert m.additional_support.fru_inventory == 1
    assert m.additional_support.ipmb_event_receiver == 1
    assert m.additional_support.ipmb_event_generator == 1
    assert m.additional_support.bridge == 0
    assert m.additional_support.chassis == 0
    assert m.manufacturer_id == 15000
    assert m.product_id == 5310


def test_getselftestresults_decode_test_passed_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x55\x00')
    assert m.completion_code == 0x00
    assert m.result == 0x55
    assert int(m.status) == 0x00


def test_getselftestresults_decode_test_fail_not_implemented_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x56\x00')
    assert m.completion_code == 0x00
    assert m.result == 0x56
    assert int(m.status) == 0x00


def test_getselftestresults_decode_test_fail_corrupted_sel_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x57\x80')
    assert m.completion_code == 0x00
    assert m.result == 0x57
    assert int(m.status) == 0x80
    assert m.status.cannot_access_sel_device == 1
    assert m.status.cannot_access_sdr_device == 0
    assert m.status.cannot_access_bmc_fru_device == 0
    assert m.status.ipmb_signal_lines_do_not_respond == 0
    assert m.status.sdr_repository_empty == 0
    assert m.status.internal_use_area_corrupted == 0
    assert m.status.controller_bootblock_corrupted == 0
    assert m.status.controller_firmware_corrupted == 0


def test_getselftestresults_decode_test_fail_corrupted_sdr_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x57\x40')
    assert m.completion_code == 0x00
    assert m.result == 0x57
    assert int(m.status) == 0x40
    assert m.status.cannot_access_sel_device == 0
    assert m.status.cannot_access_sdr_device == 1
    assert m.status.cannot_access_bmc_fru_device == 0
    assert m.status.ipmb_signal_lines_do_not_respond == 0
    assert m.status.sdr_repository_empty == 0
    assert m.status.internal_use_area_corrupted == 0
    assert m.status.controller_bootblock_corrupted == 0
    assert m.status.controller_firmware_corrupted == 0


def test_getselftestresults_decode_test_fail_corrupted_fru_rsp():
    m = pyipmi.msgs.bmc.GetSelftestResultsRsp()
    decode_message(m, b'\x00\x57\x20')
    assert m.completion_code == 0x00
    assert m.result == 0x57
    assert int(m.status) == 0x20
    assert m.status.cannot_access_sel_device == 0
    assert m.status.cannot_access_sdr_device == 0
    assert m.status.cannot_access_bmc_fru_device == 1
    assert m.status.ipmb_signal_lines_do_not_respond == 0
    assert m.status.sdr_repository_empty == 0
    assert m.status.internal_use_area_corrupted == 0
    assert m.status.controller_bootblock_corrupted == 0
    assert m.status.controller_firmware_corrupted == 0
