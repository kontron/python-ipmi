#!/usr/bin/env python

import pytest

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import create_request_by_name
from pyipmi.picmg import LedState, LinkDescriptor
from pyipmi.msgs.picmg import SetFruLedStateReq

from .ipmi_helper import create_ipmi


def test_to_request():
    req = SetFruLedStateReq()
    led = LedState(fru_id=1, led_id=2, color=LedState.COLOR_GREEN,
                   function=LedState.FUNCTION_ON)
    led.to_request(req)

    assert req.fru_id == 1
    assert req.led_id == 2
    assert req.color == led.COLOR_GREEN
    assert req.led_function == 0xff
    assert req.on_duration == 0


def test_to_request_function_on():
    req = SetFruLedStateReq()
    led = LedState(fru_id=1, led_id=2, color=LedState.COLOR_RED)
    led.override_function = led.FUNCTION_ON
    led.to_request(req)

    assert req.color == LedState.COLOR_RED
    assert req.led_function == 0xff
    assert req.on_duration == 0


def test_to_request_function_off():
    req = SetFruLedStateReq()
    led = LedState(fru_id=1, led_id=2, color=LedState.COLOR_RED)
    led.override_function = led.FUNCTION_OFF
    led.to_request(req)

    assert req.color == LedState.COLOR_RED
    assert req.led_function == 0
    assert req.on_duration == 0


def test_to_request_function_blinking():
    req = SetFruLedStateReq()
    led = LedState(fru_id=1, led_id=2, color=LedState.COLOR_RED)
    led.override_function = led.FUNCTION_BLINKING
    led.override_off_duration = 3
    led.override_on_duration = 4
    led.to_request(req)

    assert req.color == LedState.COLOR_RED
    assert req.led_function == 3
    assert req.on_duration == 4


def test_to_request_function_lamp_test():
    req = SetFruLedStateReq()
    led = LedState(fru_id=1, led_id=2, color=LedState.COLOR_RED)
    led.override_function = led.FUNCTION_LAMP_TEST
    led.lamp_test_duration = 3
    led.to_request(req)

    assert req.color == LedState.COLOR_RED
    assert req.led_function == 0xfb
    assert req.on_duration == 3


def test_get_picmg_properties():
    ipmi = create_ipmi(b'\x00\x00\x32\x05\x00')
    rsp = ipmi.get_picmg_properties()
    assert ipmi.requests == [('GetPicmgPropertiesReq', b'\x00')]
    assert rsp.extension_version == 0x32
    assert rsp.max_fru_device_id == 5


@pytest.mark.parametrize('method, option', [
    ('fru_control_cold_reset', 0),
    ('fru_control_warm_reset', 1),
    ('fru_control_graceful_reboot', 2),
    ('fru_control_diagnostic_interrupt', 3),
])
def test_fru_control(method, option):
    ipmi = create_ipmi(b'\x00\x00')
    getattr(ipmi, method)(fru_id=1)
    assert ipmi.requests == [('FruControlReq', bytes([0, 1, option]))]


def test_get_power_level():
    ipmi = create_ipmi(b'\x00\x00\x82\x05\x0a\x10\x20')
    level = ipmi.get_power_level(fru_id=1, power_type=0)
    assert ipmi.requests == [('GetPowerLevelReq', b'\x00\x01\x00')]
    assert level.power_level == 2
    assert level.dynamic_power_configuration == 1
    assert level.delay_to_stable == 5
    assert level.power_mulitplier == 10
    assert list(level.power_levels) == [0x10, 0x20]


def test_get_fan_speed_properties():
    ipmi = create_ipmi(b'\x00\x00\x01\x0f\x08\x80')
    props = ipmi.get_fan_speed_properties(fru_id=3)
    assert ipmi.requests == [('GetFanSpeedPropertiesReq', b'\x00\x03')]
    assert (props.minimum_speed_level, props.maximum_speed_level,
            props.normal_operation_level) == (1, 15, 8)
    assert props.local_control_supported == 1


def test_set_fan_level():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.set_fan_level(fru_id=3, fan_level=10)
    assert ipmi.requests[0][1][:3] == b'\x00\x03\x0a'


@pytest.mark.parametrize('rsp, levels', [
    (b'\x00\x00\x0a\x05', (10, 5)),
    (b'\x00\x00\x0a', (10, None)),
])
def test_get_fan_level(rsp, levels):
    ipmi = create_ipmi(rsp)
    assert ipmi.get_fan_level(fru_id=3) == levels


def test_get_led_state_local():
    # local state available: blinking 100ms off / 200ms on, red
    ipmi = create_ipmi(b'\x00\x00\x01\x0a\x14\x02')
    led = ipmi.get_led_state(fru_id=0, led_id=1)
    assert ipmi.requests == [('GetFruLedStateReq', b'\x00\x00\x01')]
    assert led.local_function == LedState.FUNCTION_BLINKING
    assert (led.local_off_duration, led.local_on_duration) == (100, 200)
    assert led.local_color == LedState.COLOR_RED
    assert str(led) == ('[flags  LOCAL_STATE local_function 2 '
                        'local_color 2]')


def test_get_led_state_override():
    # local off, override blinking 300ms off / 400ms on in green, lamp test
    ipmi = create_ipmi(b'\x00\x00\x07\x00\x00\x02\x1e\x28\x03\x05')
    led = ipmi.get_led_state(fru_id=0, led_id=1)
    assert led.local_function == LedState.FUNCTION_OFF
    assert led.override_function == LedState.FUNCTION_BLINKING
    assert led.override_off_duration == 300
    assert led.override_on_duration == 400
    assert led.override_color == LedState.COLOR_GREEN
    assert led.lamp_test_duration == 500
    assert 'OVR_EN' in str(led)
    assert 'LAMP_TEST_EN' in str(led)


def test_get_led_state_longest_blinking():
    # the longest blinking durations: 2500ms off (0xfa) / 2500ms on
    ipmi = create_ipmi(b'\x00\x00\x01\xfa\xfa\x02')
    led = ipmi.get_led_state(fru_id=0, led_id=1)
    assert led.local_function == LedState.FUNCTION_BLINKING
    assert (led.local_off_duration, led.local_on_duration) == (2500, 2500)


@pytest.mark.parametrize('rsp', [
    # invalid local function
    b'\x00\x00\x01\xfc\x00\x02',
    # blinking with invalid on duration
    b'\x00\x00\x01\x0a\xfc\x02',
    # invalid override function
    b'\x00\x00\x02\xff\x00\x02\xfc\x00\x03',
])
def test_get_led_state_invalid(rsp):
    ipmi = create_ipmi(rsp)
    with pytest.raises(DecodingError):
        ipmi.get_led_state(fru_id=0, led_id=1)


def test_led_state_str_no_flags():
    ipmi = create_ipmi(b'\x00\x00\x00\xff\x00\x02')
    assert str(ipmi.get_led_state(0, 1)) == '[flags  NONE]'


def test_set_led_state():
    ipmi = create_ipmi(b'\x00\x00')
    led = LedState(fru_id=0, led_id=1, color=LedState.COLOR_BLUE,
                   function=LedState.FUNCTION_ON)
    ipmi.set_led_state(led)
    assert ipmi.requests == [
        ('SetFruLedStateReq', b'\x00\x00\x01\xff\x00\x01')]


def test_led_state_to_request_invalid():
    led = LedState(fru_id=0, led_id=1, color=LedState.COLOR_BLUE,
                   function=LedState.FUNCTION_BLINKING)
    led.override_off_duration = 0xfc
    led.override_on_duration = 10
    with pytest.raises(EncodingError):
        led.to_request(create_request_by_name('SetFruLedState'))

    led.override_function = 99
    with pytest.raises(AssertionError):
        led.to_request(create_request_by_name('SetFruLedState'))


@pytest.mark.parametrize('method, control', [
    ('set_fru_activation', 1),
    ('set_fru_deactivation', 0),
])
def test_set_fru_activation(method, control):
    ipmi = create_ipmi(b'\x00\x00')
    getattr(ipmi, method)(2)
    assert ipmi.requests == [('SetFruActivationReq',
                              bytes([0, 2, control]))]


@pytest.mark.parametrize('method, mask, value', [
    ('set_fru_activation_lock', 0x01, 0x01),
    ('clear_fru_activation_lock', 0x01, 0x00),
    ('set_fru_deactivation_lock', 0x02, 0x02),
    ('clear_fru_deactivation_lock', 0x02, 0x00),
])
def test_set_fru_activation_policy(method, mask, value):
    ipmi = create_ipmi(b'\x00\x00')
    getattr(ipmi, method)(2)
    assert ipmi.requests == [('SetFruActivationPolicyReq',
                              bytes([0, 2, mask, value]))]


def test_set_port_state():
    ipmi = create_ipmi(b'\x00\x00')
    link = LinkDescriptor()
    link.channel = 1
    link.interface = LinkDescriptor.INTERFACE_FABRIC
    link.link_flags = LinkDescriptor.FLAGS_LANE0
    link.type = LinkDescriptor.TYPE_ETHERNET_FABRIC
    link.sig_class = LinkDescriptor.SIGNALING_CLASS_BASIC
    link.extension = LinkDescriptor.TYPE_EXT_ETHERNET_FIX1000_BX
    link.grouping_id = 0
    ipmi.set_port_state(link, LinkDescriptor.STATE_ENABLE)
    assert ipmi.requests == [('SetPortStateReq',
                              b'\x00\x41\x21\x00\x00\x01')]


def test_get_port_state():
    ipmi = create_ipmi(b'\x00\x00\x41\x21\x00\x00\x01')
    (link, state) = ipmi.get_port_state(1, LinkDescriptor.INTERFACE_FABRIC)
    assert ipmi.requests == [('GetPortStateReq', b'\x00\x41')]
    assert link.channel == 1
    assert link.interface == LinkDescriptor.INTERFACE_FABRIC
    assert link.link_flags == LinkDescriptor.FLAGS_LANE0
    assert link.type == LinkDescriptor.TYPE_ETHERNET_FABRIC
    assert state == LinkDescriptor.STATE_ENABLE


def test_get_port_state_no_link():
    ipmi = create_ipmi(b'\x00\x00')
    assert ipmi.get_port_state(1, LinkDescriptor.INTERFACE_FABRIC) == \
        (None, None)


def test_link_descriptor_strings():
    link = LinkDescriptor()
    assert link.get_interface_string(LinkDescriptor.INTERFACE_BASE) == 'Base'
    assert link.get_interface_string(99) == 'unknown'
    assert link.get_link_type_string(
        LinkDescriptor.TYPE_ETHERNET_FABRIC,
        LinkDescriptor.TYPE_EXT_ETHERNET_FIX10G_KR,
        LinkDescriptor.SIGNALING_CLASS_10_3125_GBD) == 'Fixed 10GBASE-KR'
    assert link.get_link_type_string(99, 0) == 'unknown'


def test_get_pm_global_status():
    ipmi = create_ipmi(b'\x00\x00\x10\x07\x00')
    status = ipmi.get_pm_global_status()
    assert ipmi.requests == [('GetPowerChannelStatusReq', b'\x00\x01\x01')]
    assert status.role == 1
    assert status.management_power_good
    assert status.payload_power_good
    assert not status.unidentified_fault


def test_get_power_channel_status():
    ipmi = create_ipmi(b'\x00\x00\x10\x00\x5b')
    status = ipmi.get_power_channel_status(3)
    assert ipmi.requests == [('GetPowerChannelStatusReq', b'\x00\x03\x01')]
    assert (status.present, status.management_power,
            status.management_power_overcurrent, status.enable,
            status.payload_power, status.payload_power_overcurrent,
            status.pwr_on) == (1, 1, 0, 1, 1, 0, 1)


@pytest.mark.parametrize('enable, control', [(True, 5), (False, 4)])
def test_send_channel_power(enable, control):
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.send_channel_power(2, enable, current_limit=1.5)
    assert ipmi.requests == [('SendPowerChannelControlReq',
                              bytes([0, 2, control, 15, 1, 0]))]


def test_send_pm_heartbeat():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.send_pm_heartbeat()
    assert ipmi.requests[0][0] == 'SendPmHeartbeatReq'


def test_set_signaling_class():
    ipmi = create_ipmi(b'\x00\x00')
    ipmi.set_signaling_class(interface=1, channel=2, signaling_class=4)
    assert ipmi.requests == [('SetSignalingClassReq', b'\x00\x42\x04')]


def test_get_signaling_class():
    ipmi = create_ipmi(b'\x00\x00\x42\x04')
    assert ipmi.get_signaling_class(interface=1, channel=2) == 4
    assert ipmi.requests == [('GetSignalingClassReq', b'\x00\x42')]
