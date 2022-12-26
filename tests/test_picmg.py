#!/usr/bin/env python

from pyipmi.picmg import LedState
from pyipmi.msgs.picmg import SetFruLedStateReq


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
