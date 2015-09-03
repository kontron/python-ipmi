#!/usr/bin/env python

import unittest
from pyipmi import picmg

import pyipmi.msgs.picmg

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

class TestLedState(unittest.TestCase):
    def test_to_request_function_on(self):
        req = pyipmi.msgs.picmg.SetFruLedStateReq()
        led = picmg.LedState()
        led.fru_id = 1
        led.led_id = 2
        led.override_color = led.COLOR_RED
        led.local_function = led.FUNCTION_ON
        led.to_request(req)

        self.assertEqual(req.fru_id, 1)
        self.assertEqual(req.led_id, 2)
        self.assertEqual(req.color, led.COLOR_RED)
        self.assertEqual(req.led_function, 0xff)
        self.assertEqual(req.on_duration, 0)

    def test_to_request_function_off(self):
        req = pyipmi.msgs.picmg.SetFruLedStateReq()
        led = picmg.LedState()
        led.fru_id = 1
        led.led_id = 2
        led.override_color = led.COLOR_RED
        led.local_function = led.FUNCTION_OFF
        led.to_request(req)

        self.assertEqual(req.fru_id, 1)
        self.assertEqual(req.led_id, 2)
        self.assertEqual(req.color, led.COLOR_RED)
        self.assertEqual(req.led_function, 0)
        self.assertEqual(req.on_duration, 0)

    def test_to_request_function_blinking(self):
        req = pyipmi.msgs.picmg.SetFruLedStateReq()
        led = picmg.LedState()
        led.fru_id = 1
        led.led_id = 2
        led.override_color = led.COLOR_RED
        led.local_function = led.FUNCTION_BLINKING
        led.override_off_duration = 3
        led.override_on_duration = 4
        led.to_request(req)

        self.assertEqual(req.fru_id, 1)
        self.assertEqual(req.led_id, 2)
        self.assertEqual(req.color, led.COLOR_RED)
        self.assertEqual(req.led_function, 3)
        self.assertEqual(req.on_duration, 4)

    def test_to_request_function_lamp_test(self):
        req = pyipmi.msgs.picmg.SetFruLedStateReq()
        led = picmg.LedState()
        led.fru_id = 1
        led.led_id = 2
        led.override_color = led.COLOR_RED
        led.local_function = led.FUNCTION_LAMP_TEST
        led.lamp_test_duration = 3
        led.to_request(req)

        self.assertEqual(req.fru_id, 1)
        self.assertEqual(req.led_id, 2)
        self.assertEqual(req.color, led.COLOR_RED)
        self.assertEqual(req.led_function, 0xfb)
        self.assertEqual(req.on_duration, 3)
