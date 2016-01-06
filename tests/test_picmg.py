#!/usr/bin/env python

from nose.tools import eq_
from pyipmi import picmg

import pyipmi.msgs.picmg

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

def test_to_request_function_on():
    req = pyipmi.msgs.picmg.SetFruLedStateReq()
    led = picmg.LedState()
    led.fru_id = 1
    led.led_id = 2
    led.override_color = led.COLOR_RED
    led.local_function = led.FUNCTION_ON
    led.to_request(req)

    eq_(req.fru_id, 1)
    eq_(req.led_id, 2)
    eq_(req.color, led.COLOR_RED)
    eq_(req.led_function, 0xff)
    eq_(req.on_duration, 0)

def test_to_request_function_off():
    req = pyipmi.msgs.picmg.SetFruLedStateReq()
    led = picmg.LedState()
    led.fru_id = 1
    led.led_id = 2
    led.override_color = led.COLOR_RED
    led.local_function = led.FUNCTION_OFF
    led.to_request(req)

    eq_(req.fru_id, 1)
    eq_(req.led_id, 2)
    eq_(req.color, led.COLOR_RED)
    eq_(req.led_function, 0)
    eq_(req.on_duration, 0)

def test_to_request_function_blinking():
    req = pyipmi.msgs.picmg.SetFruLedStateReq()
    led = picmg.LedState()
    led.fru_id = 1
    led.led_id = 2
    led.override_color = led.COLOR_RED
    led.local_function = led.FUNCTION_BLINKING
    led.override_off_duration = 3
    led.override_on_duration = 4
    led.to_request(req)

    eq_(req.fru_id, 1)
    eq_(req.led_id, 2)
    eq_(req.color, led.COLOR_RED)
    eq_(req.led_function, 3)
    eq_(req.on_duration, 4)

def test_to_request_function_lamp_test():
    req = pyipmi.msgs.picmg.SetFruLedStateReq()
    led = picmg.LedState()
    led.fru_id = 1
    led.led_id = 2
    led.override_color = led.COLOR_RED
    led.local_function = led.FUNCTION_LAMP_TEST
    led.lamp_test_duration = 3
    led.to_request(req)

    eq_(req.fru_id, 1)
    eq_(req.led_id, 2)
    eq_(req.color, led.COLOR_RED)
    eq_(req.led_function, 0xfb)
    eq_(req.on_duration, 3)
