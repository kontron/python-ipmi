#!/usr/bin/env python

from types import SimpleNamespace

import pytest

from pyipmi.bmc import DeviceId, DeviceGuid, Watchdog
import pyipmi.msgs.bmc
from pyipmi.msgs import decode_message

from .ipmi_helper import create_ipmi


def test_watchdog_object():
    msg = pyipmi.msgs.bmc.GetWatchdogTimerRsp()
    decode_message(msg, b'\x00\x41\x42\x33\x44\x55\x66\x77\x88')

    wdt = Watchdog(msg)
    assert wdt.timer_use == 1
    assert wdt.is_running == 1
    assert wdt.dont_log == 0
    assert wdt.timeout_action == 2
    assert wdt.pre_timeout_interrupt == 4
    assert wdt.pre_timeout_interval == 0x33

    assert wdt.timer_use_expiration_flags == 0x44
    assert wdt.initial_countdown == 0x6655
    assert wdt.present_countdown == 0x8877


def test_deviceid_object():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(rsp, b'\x00\x12\x84\x05\x67\x51\x55\x12\x34\x56\x44\x55')

    dev = DeviceId(rsp)
    assert dev.device_id == 18
    assert dev.revision == 4
    assert dev.provides_sdrs
    assert str(dev.fw_revision) == '5.67'
    assert str(dev.ipmi_version) == '1.5'
    assert dev.manufacturer_id == 5649426
    # not a well known manufacturer
    assert dev.manufacturer_name is None
    assert dev.product_id == 21828

    assert dev.aux is None


def test_deviceid_manufacturer_name():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    # manufacturer ID 15000
    decode_message(rsp, b'\x00\x04\x00\x01\x00\x02\x00\x98\x3a\x00\xa5\x06')
    assert DeviceId(rsp).manufacturer_name == 'Kontron'


def test_deviceid_object_with_aux():
    msg = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(msg,
                   b'\x00\x00\x00\x00\x00\x00\x00\x00'
                   b'\x00\x00\x00\x00\x01\x02\x03\x04')

    device_id = DeviceId(msg)
    assert device_id.aux == [1, 2, 3, 4]


def test_deviceguid_object():
    m = pyipmi.msgs.bmc.GetDeviceGuidRsp()
    decode_message(m, b'\x00\xff\xee\xdd\xcc\xbb\xaa'
                      b'\x99\x88\x77\x66\x55\x44\x33\x22\x11\x00')
    guid = DeviceGuid(m)
    assert guid.device_guid_string == '00112233-4455-6677-8899-aabbccddeeff'


def test_deviceid_str_and_functions():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(rsp, b'\x00\x20\x01\x04\x00\x02\xbf\x7c\x2a\x00\x69\x09')
    dev = DeviceId(rsp)
    assert dev.supports_function('SENSOR')
    assert dev.supports_function('chassis')
    assert not dev.supports_function('bridge')
    assert str(dev) == (
        'Device ID: 32 revision: 1 available: 0 fw version: 4.0 ipmi: 2.0 '
        'manufacturer: 10876 product: 2409 functions: sensor,'
        'sdr_repository,sel,fru_inventory,ipmb_event_receiver,'
        'ipmb_event_generator,chassis')


def test_get_device_guid():
    ipmi = create_ipmi(b'\x00' + bytes(range(16)))
    guid = ipmi.get_device_guid()
    assert ipmi.requests == [('GetDeviceGuidReq', b'')]
    assert list(guid.device_guid) == list(range(16))
    assert str(guid).startswith('Device GUID: ')


@pytest.mark.parametrize('method, name', [
    ('cold_reset', 'ColdResetReq'),
    ('warm_reset', 'WarmResetReq'),
    ('reset_watchdog_timer', 'ResetWatchdogTimerReq'),
])
def test_commands_without_data(method, name):
    ipmi = create_ipmi(b'\x00')
    getattr(ipmi, method)()
    assert ipmi.requests == [(name, b'')]


def test_set_watchdog_timer():
    ipmi = create_ipmi(b'\x00')
    config = SimpleNamespace(
        timer_use=Watchdog.TIMER_USE_SMS_OS, dont_stop=True, dont_log=False,
        timeout_action=Watchdog.TIMEOUT_ACTION_HARD_RESET,
        pre_timeout_interrupt=2, pre_timeout_interval=10,
        timer_use_expiration_flags=0x10, initial_countdown=600)
    ipmi.set_watchdog_timer(config)
    assert ipmi.requests == [
        ('SetWatchdogTimerReq', b'\x44\x21\x0a\x10\x58\x02')]


def test_get_watchdog_timer():
    ipmi = create_ipmi(b'\x00\x41\x42\x33\x44\x55\x66\x77\x88')
    wdt = ipmi.get_watchdog_timer()
    assert wdt.timer_use == 1
    assert wdt.present_countdown == 0x8877


def test_i2c_write_read():
    ipmi = create_ipmi(b'\x00\xaa\xbb')
    data = ipmi.i2c_write_read(bus_type=1, bus_id=0, channel=2,
                               address=0x50, count=2, data=b'\x10')
    assert ipmi.requests == [('MasterWriteReadReq', b'\x21\xa0\x02\x10')]
    assert list(data) == [0xaa, 0xbb]


def test_i2c_read():
    ipmi = create_ipmi(b'\x00\xaa')
    assert list(ipmi.i2c_read(1, 0, 2, 0x50, 1)) == [0xaa]
    assert ipmi.requests == [('MasterWriteReadReq', b'\x21\xa0\x01')]


def test_i2c_write():
    ipmi = create_ipmi(b'\x00')
    ipmi.i2c_write(1, 0, 2, 0x50, b'\x10\x20')
    assert ipmi.requests == [('MasterWriteReadReq', b'\x21\xa0\x00\x10\x20')]
