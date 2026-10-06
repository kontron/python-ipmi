# Copyright (c) 2026  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

"""VITA 46.11 (VSO) commands."""

from __future__ import annotations

from .msgs import create_request_by_name, Message
from .utils import check_completion_code
from .mixin import IpmiMixin
from .msgs.vita import (VITA_FRU_CONTROL_COLD_RESET,  # noqa: F401
                        VITA_FRU_CONTROL_WARM_RESET,
                        VITA_FRU_CONTROL_GRACEFUL_REBOOT,
                        VITA_FRU_CONTROL_DIAGNOSTIC_INTERRUPT)

VITA_FRU_DEACTIVATE = 0x00
VITA_FRU_ACTIVATE = 0x01

# FRU state policy bits, for mask and value of set_vita_fru_state_policy()
VITA_POLICY_ACTIVATION_LOCKED = 0x01
VITA_POLICY_DEACTIVATION_LOCKED = 0x02
VITA_POLICY_COMMANDED_DEACTIVATION_IGNORED = 0x04
VITA_POLICY_DEFAULT_ACTIVATION_LOCKED = 0x08

# LED functions of set_vita_led_state(), 1 - 250 is blinking (off duration)
VITA_LED_FUNCTION_OFF = 0x00
VITA_LED_FUNCTION_LAMP_TEST = 0xfb
VITA_LED_FUNCTION_LOCAL_CONTROL = 0xfc
VITA_LED_FUNCTION_ON = 0xff

VITA_LED_COLOR_BLUE = 0x01
VITA_LED_COLOR_RED = 0x02
VITA_LED_COLOR_GREEN = 0x03
VITA_LED_COLOR_AMBER = 0x04
VITA_LED_COLOR_ORANGE = 0x05
VITA_LED_COLOR_WHITE = 0x06
VITA_LED_COLOR_NO_CHANGE = 0x0e
VITA_LED_COLOR_DEFAULT = 0x0f

VITA_LED_ALL = 0xff

VITA_SITE_TYPES = {
    0x00: 'Front Loading VPX Plug-In Module',
    0x01: 'Power Entry Module',
    0x02: 'Chassis FRU Information Module',
    0x03: 'Dedicated Chassis Manager',
    0x04: 'Fan Tray',
    0x05: 'Fan Tray Filter',
    0x06: 'Alarm Panel',
    0x07: 'XMC',
    0x09: 'VPX Rear Transition Module',
    0x0a: 'Front Loading VME Plug-In Module',
    0x0b: 'Front Loading VXS Plug-In Module',
    0x0c: 'Power Supply',
    0x0d: 'Front Loading VITA 62 Module',
    0x0e: 'VITA 71 Module',
    0x0f: 'FMC',
}


class Vita(IpmiMixin):
    """VITA 46.11 commands of a VSO (VITA Standards Organization) IPMC."""

    def get_vita_vso_capabilities(self) -> Message:
        return self.send_message_with_name('VitaGetVsoCapabilities')

    def get_vita_fru_address_info(self, fru_id: int = 0) -> Message:
        return self.send_message_with_name('VitaGetFruAddressInfo',
                                           fru_id=fru_id)

    def vita_fru_control(self, fru_id: int, option: int) -> None:
        self.send_message_with_name('VitaFruControl', fru_id=fru_id,
                                    option=option)

    def set_vita_fru_activation(self, fru_id: int) -> None:
        self.send_message_with_name('VitaSetFruActivation', fru_id=fru_id,
                                    control=VITA_FRU_ACTIVATE)

    def set_vita_fru_deactivation(self, fru_id: int) -> None:
        self.send_message_with_name('VitaSetFruActivation', fru_id=fru_id,
                                    control=VITA_FRU_DEACTIVATE)

    def get_vita_fru_state_policy(self, fru_id: int) -> Message:
        return self.send_message_with_name('VitaGetFruStatePolicy',
                                           fru_id=fru_id)

    def set_vita_fru_state_policy(self, fru_id: int, mask: int,
                                  value: int) -> None:
        """Set the FRU state policy bits selected by mask to value.

        mask, value: VITA_POLICY_* bits
        """
        req = create_request_by_name('VitaSetFruStatePolicy')
        req.fru_id = fru_id
        req.activation_policy_mask._value = mask
        req.activation_policy_set._value = value
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_vita_led_properties(self, fru_id: int) -> Message:
        return self.send_message_with_name('VitaGetFruLedProperties',
                                           fru_id=fru_id)

    def get_vita_led_color_capabilities(self, fru_id: int,
                                        led_id: int) -> Message:
        return self.send_message_with_name('VitaGetFruLedCapabilities',
                                           fru_id=fru_id, led_id=led_id)

    def get_vita_led_state(self, fru_id: int, led_id: int) -> Message:
        return self.send_message_with_name('VitaGetFruLedState',
                                           fru_id=fru_id, led_id=led_id)

    def set_vita_led_state(self, fru_id: int, led_id: int, function: int,
                           on_duration: int = 0,
                           color: int = VITA_LED_COLOR_DEFAULT) -> None:
        """Set the state of a FRU LED.

        function: VITA_LED_FUNCTION_*, or 1 - 250 for blinking (off duration)
        on_duration: on duration of blinking or lamp test duration
        color: VITA_LED_COLOR_*
        """
        self.send_message_with_name('VitaSetFruLedState', fru_id=fru_id,
                                    led_id=led_id, function=function,
                                    on_duration=on_duration, color=color)
