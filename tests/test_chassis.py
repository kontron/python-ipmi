#!/usr/bin/env python

import pytest

from array import array

from pyipmi.chassis import (ChassisStatus, data_to_boot_device,
                            data_to_boot_mode, data_to_boot_persistency,
                            boot_options_to_data, BootDevice,
                            ChassisCapabilities,
                            POWER_RESTORE_POLICY_ALWAYS_OFF,
                            POWER_RESTORE_POLICY_RESTORE_PREVIOUS,
                            POWER_RESTORE_POLICY_ALWAYS_ON,
                            RESTART_CAUSE_CHASSIS_CONTROL,
                            RESTART_CAUSE_WATCHDOG, RESTART_CAUSE_RTC_WAKEUP)
import pyipmi.msgs.chassis
from pyipmi.errors import CompletionCodeError
from pyipmi.msgs import decode_message

from .ipmi_helper import create_ipmi


def test_chassisstatus_object():
    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\xff\xff\xff')

    status = ChassisStatus(msg)

    assert status.power_on
    assert status.overload
    assert status.interlock
    assert status.fault
    assert status.control_fault
    assert status.restore_policy == 3

    assert 'ac_failed' in status.last_event
    assert 'overload' in status.last_event
    assert 'interlock' in status.last_event
    assert 'fault' in status.last_event
    assert 'power_on_via_ipmi' in status.last_event

    assert 'intrusion' in status.chassis_state
    assert 'front_panel_lockout' in status.chassis_state
    assert 'drive_fault' in status.chassis_state
    assert 'cooling_fault' in status.chassis_state


def test_datatobootmode():
    assert data_to_boot_mode(array('B', [0, 0, 0, 0, 0])) == "legacy"
    assert data_to_boot_mode(array('B', [0b10100000, 0, 0, 0, 0])) == "efi"


def test_datatobootpersistency():
    assert data_to_boot_persistency(array('B', [0b11000000, 0, 0, 0, 0]))
    assert not data_to_boot_persistency(array('B', [0b10000000, 0, 0, 0, 0]))


def test_datatobootdevice():
    assert data_to_boot_device(array('B', [0b11000000, 0b00001000, 0, 0, 0])) == BootDevice.DEFAULT_HDD
    assert data_to_boot_device(array('B', [0b11000000, 0b00000100, 0, 0, 0])) == BootDevice.PXE


@pytest.mark.parametrize('raw, device', [
    (0b1000, BootDevice.REMOTE_CD),
    (0b1001, BootDevice.PRIMARY_REMOTE),
])
def test_datatobootdevice_remote_media(raw, device):
    assert data_to_boot_device(array('B', [0b10000000, raw << 2, 0, 0, 0])) \
        == device


@pytest.mark.parametrize('device', list(BootDevice))
def test_bootdevice_round_trip(device):
    data = boot_options_to_data(device, 'efi', False)
    assert data_to_boot_device(data.array) == device


def test_bootoptionstodata():
    assert boot_options_to_data("bios setup", "efi", True).array == array('B', [0b11100000, 0b00011000, 0, 0, 0])


def test_bootoptionstodata_raise_typeerror():
    with pytest.raises(TypeError):
        boot_options_to_data("pxe", "efi", 1)


def test_bootoptionstodata_raise_valueerror_bootmode():
    with pytest.raises(ValueError):
        boot_options_to_data("pxe", "wrong boot mode", True)


def test_bootoptionstodata_raise_valueerror_bootdevice():
    with pytest.raises(ValueError):
        boot_options_to_data("wrong boot device", "efi", True)


def test_chassisstatus_objects_are_independent():
    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\xff\xff\xff')
    ChassisStatus(msg)

    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\x00\x00\x00')
    status = ChassisStatus(msg)
    assert status.last_event == []
    assert status.chassis_state == []


def test_get_chassis_status():
    ipmi = create_ipmi(b'\x00\x01\x00\x00\x0f')
    status = ipmi.get_chassis_status()
    assert ipmi.requests == [('GetChassisStatusReq', b'')]
    assert status.power_on
    assert not status.fault
    assert status.front_panel_button_capabilities == 0x0f


@pytest.mark.parametrize('method, option', [
    ('chassis_control_power_down', 0),
    ('chassis_control_power_up', 1),
    ('chassis_control_power_cycle', 2),
    ('chassis_control_hard_reset', 3),
    ('chassis_control_diagnostic_interrupt', 4),
    ('chassis_control_soft_shutdown', 5),
])
def test_chassis_control(method, option):
    ipmi = create_ipmi(b'\x00')
    getattr(ipmi, method)()
    assert ipmi.requests == [('ChassisControlReq', bytes([option]))]


def test_chassis_reset():
    ipmi = create_ipmi(b'\x00')
    ipmi.chassis_reset()
    assert ipmi.requests == [('ChassisResetReq', b'')]


@pytest.mark.parametrize('kwargs, data', [
    ({}, b''),
    ({'interval': 30}, b'\x1e'),
    ({'interval': 0}, b'\x00'),
    # the force byte needs the interval byte before it
    ({'force_on': True}, b'\x00\x01'),
    ({'interval': 10, 'force_on': True}, b'\x0a\x01'),
])
def test_chassis_identify(kwargs, data):
    ipmi = create_ipmi(b'\x00')
    ipmi.chassis_identify(**kwargs)
    assert ipmi.requests == [('ChassisIdentifyReq', data)]


@pytest.mark.parametrize('interval', [-1, 256])
def test_chassis_identify_invalid_interval(interval):
    ipmi = create_ipmi(b'\x00')
    with pytest.raises(ValueError):
        ipmi.chassis_identify(interval)
    assert ipmi.requests == []


@pytest.mark.parametrize('method', ['chassis_reset', 'chassis_identify'])
def test_chassis_reset_identify_error(method):
    ipmi = create_ipmi(b'\xc1')
    with pytest.raises(CompletionCodeError):
        getattr(ipmi, method)()


# intrusion sensor and power interlock, the device addresses and the bridge
CHASSIS_CAPABILITIES_RSP = b'\x00\x09\x20\x22\x24\x26\x28'


def test_get_chassis_capabilities():
    ipmi = create_ipmi(CHASSIS_CAPABILITIES_RSP)
    caps = ipmi.get_chassis_capabilities()
    assert ipmi.requests == [('GetChassisCapabilitiesReq', b'')]
    assert caps.intrusion_sensor
    assert not caps.frontpanel_lockout
    assert not caps.diagnostic_interrupt
    assert caps.power_interlock
    assert caps.fru_info_device_address == 0x20
    assert caps.sdr_device_address == 0x22
    assert caps.sel_device_address == 0x24
    assert caps.system_management_device_address == 0x26
    assert caps.bridge_device_address == 0x28


def test_get_chassis_capabilities_without_bridge():
    ipmi = create_ipmi(CHASSIS_CAPABILITIES_RSP[:-1])
    assert ipmi.get_chassis_capabilities().bridge_device_address is None


def test_set_chassis_capabilities():
    ipmi = create_ipmi({'GetChassisCapabilities': CHASSIS_CAPABILITIES_RSP,
                        'SetChassisCapabilities': b'\x00'})
    caps = ipmi.get_chassis_capabilities()
    caps.frontpanel_lockout = True
    caps.sel_device_address = 0x30
    ipmi.set_chassis_capabilities(caps)
    # the read-only power interlock is not set
    assert ipmi.requests[1] == ('SetChassisCapabilitiesReq',
                                b'\x03\x20\x22\x30\x26\x28')


def test_set_chassis_capabilities_without_bridge():
    ipmi = create_ipmi(b'\x00')
    caps = ChassisCapabilities()
    caps.intrusion_sensor = False
    caps.frontpanel_lockout = False
    caps.fru_info_device_address = 0x20
    caps.sdr_device_address = 0x20
    caps.sel_device_address = 0x20
    caps.system_management_device_address = 0x20
    ipmi.set_chassis_capabilities(caps)
    assert ipmi.requests == [('SetChassisCapabilitiesReq',
                              b'\x00\x20\x20\x20\x20')]


@pytest.mark.parametrize('policy', [
    POWER_RESTORE_POLICY_ALWAYS_OFF,
    POWER_RESTORE_POLICY_RESTORE_PREVIOUS,
    POWER_RESTORE_POLICY_ALWAYS_ON,
])
def test_set_power_restore_policy(policy):
    ipmi = create_ipmi(b'\x00\x07')
    supported = ipmi.set_power_restore_policy(policy)
    assert ipmi.requests == [('SetPowerRestorePolicyReq', bytes([policy]))]
    assert supported == [POWER_RESTORE_POLICY_ALWAYS_OFF,
                         POWER_RESTORE_POLICY_RESTORE_PREVIOUS,
                         POWER_RESTORE_POLICY_ALWAYS_ON]


def test_get_supported_power_restore_policies():
    ipmi = create_ipmi(b'\x00\x05')
    supported = ipmi.get_supported_power_restore_policies()
    # the policy is not changed
    assert ipmi.requests == [('SetPowerRestorePolicyReq', b'\x03')]
    assert supported == [POWER_RESTORE_POLICY_ALWAYS_OFF,
                         POWER_RESTORE_POLICY_ALWAYS_ON]


@pytest.mark.parametrize('policy', [-1, 4])
def test_set_power_restore_policy_invalid(policy):
    ipmi = create_ipmi(b'\x00\x07')
    with pytest.raises(ValueError):
        ipmi.set_power_restore_policy(policy)
    assert ipmi.requests == []


@pytest.mark.parametrize('data, cause, channel_number, string', [
    (b'\x00\x01\x01', RESTART_CAUSE_CHASSIS_CONTROL, 1,
     'Chassis Control command'),
    (b'\x00\x04\x00', RESTART_CAUSE_WATCHDOG, 0, 'watchdog expiration'),
    (b'\x00\x0b', RESTART_CAUSE_RTC_WAKEUP, None, 'power-up via RTC wakeup'),
    (b'\x00\x0f\x00', 0xf, 0, 'reserved (0xf)'),
])
def test_get_system_restart_cause(data, cause, channel_number, string):
    ipmi = create_ipmi(data)
    restart = ipmi.get_system_restart_cause()
    assert ipmi.requests == [('GetSystemRestartCauseReq', b'')]
    assert restart.cause == cause
    assert restart.channel_number == channel_number
    assert str(restart) == string


def test_get_poh_counter():
    # 60 minutes per count, 1000 counts
    ipmi = create_ipmi(b'\x00\x3c\xe8\x03\x00\x00')
    poh = ipmi.get_poh_counter()
    assert ipmi.requests == [('GetPohCounterReq', b'')]
    assert poh.minutes_per_count == 60
    assert poh.counter == 1000
    assert poh.minutes == 60000


@pytest.mark.parametrize('kwargs, data', [
    ({}, b'\x00'),
    ({'power_off': False}, b'\x01'),
    ({'reset': False}, b'\x02'),
    ({'diagnostic_interrupt': False}, b'\x04'),
    ({'standby': False}, b'\x08'),
    ({'power_off': False, 'reset': False, 'diagnostic_interrupt': False,
      'standby': False}, b'\x0f'),
])
def test_set_front_panel_button_enables(kwargs, data):
    ipmi = create_ipmi(b'\x00')
    ipmi.set_front_panel_button_enables(**kwargs)
    assert ipmi.requests == [('SetFrontPanelButtonEnablesReq', data)]


def test_set_power_cycle_interval():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_power_cycle_interval(10)
    assert ipmi.requests == [('SetPowerCycleIntervalReq', b'\x0a')]


@pytest.mark.parametrize('interval', [-1, 256])
def test_set_power_cycle_interval_invalid(interval):
    ipmi = create_ipmi(b'\x00')
    with pytest.raises(ValueError):
        ipmi.set_power_cycle_interval(interval)
    assert ipmi.requests == []


@pytest.mark.parametrize('method, args', [
    ('get_chassis_capabilities', ()),
    ('set_power_restore_policy', (POWER_RESTORE_POLICY_ALWAYS_ON,)),
    ('get_system_restart_cause', ()),
    ('get_poh_counter', ()),
    ('set_front_panel_button_enables', ()),
    ('set_power_cycle_interval', (10,)),
])
def test_chassis_commands_error(method, args):
    ipmi = create_ipmi(b'\xc1')
    with pytest.raises(CompletionCodeError):
        getattr(ipmi, method)(*args)


# boot flags: valid, persistent, EFI; boot device: PXE
BOOT_OPTIONS_RSP = b'\x00\x01\x05\xe0\x04\x00\x00\x00'


def test_get_system_boot_options():
    ipmi = create_ipmi(BOOT_OPTIONS_RSP)
    data = ipmi.get_system_boot_options(5)
    assert ipmi.requests == [('GetSystemBootOptionsReq', b'\x05\x00\x00')]
    assert list(data) == [0xe0, 0x04, 0, 0, 0]


def test_get_boot_options():
    ipmi = create_ipmi(BOOT_OPTIONS_RSP)
    assert ipmi.get_boot_mode() == 'efi'
    assert ipmi.get_boot_persistency() is True
    assert ipmi.get_boot_device() == BootDevice.PXE


def test_set_boot_options():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_boot_options(BootDevice.PXE, 'efi', True)
    assert ipmi.requests == [
        ('SetSystemBootOptionsReq', b'\x05\xe0\x04\x00\x00\x00')]
