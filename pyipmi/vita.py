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

"""VITA 46.11 (VSO) commands.

VITA 46.11 defines the system management of VPX systems by IPM controllers
(IPMCs). The commands are a group extension of IPMI, the VITA Standards
Organization (VSO) group extension.

The commands are the methods of :class:`Vita`, which are available on
:class:`pyipmi.Ipmi`. The constants of this module are the values of the
arguments:

- ``VITA_FRU_CONTROL_*``: the options of :meth:`Vita.vita_fru_control`
- ``VITA_POLICY_*``: the FRU state policy bits of
  :meth:`Vita.set_vita_fru_state_policy`
- ``VITA_LED_FUNCTION_*`` and ``VITA_LED_COLOR_*``: the functions and
  colors of :meth:`Vita.set_vita_led_state`
- ``VITA_SITE_TYPES``: the names of the site types returned by
  :meth:`Vita.get_vita_fru_address_info`

Example:
    Let the first LED of FRU 0 blink green::

        from pyipmi.vita import VITA_LED_COLOR_GREEN

        # 500 ms off, 500 ms on
        ipmi.set_vita_led_state(0, 0, function=50, on_duration=50,
                                color=VITA_LED_COLOR_GREEN)
"""

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
    """VITA 46.11 commands of a VSO IPMC, available on :class:`pyipmi.Ipmi`.

    Most commands return the response message, its fields are listed in the
    description of the command. Bit fields are objects with an attribute
    per bit and can be converted to their value with ``int()``.
    """

    def get_vita_vso_capabilities(self) -> Message:
        """Get the VSO capabilities of the IPMC.

        Returns:
            The response with the fields ``vita_identifier``,
            ``ipmc_identifier`` (bits ``tier_functionality`` and
            ``layer_functionality``), ``ipmb_capabilities`` (bits
            ``number_ipmbs`` and ``max_frequency``), ``vso_standard`` (bit
            ``standard``), ``specification_revision``, ``max_fru_id`` and
            ``ipmc_fru_device_id``.
        """
        return self.send_message_with_name('VitaGetVsoCapabilities')

    def get_vita_fru_address_info(self, fru_id: int = 0) -> Message:
        """Get the address information of a FRU.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The response with the fields ``hardware_address``,
            ``ipmb_0_address``, ``fru_id``, ``site_id``, ``site_type`` (see
            ``VITA_SITE_TYPES``) and ``address_on_channel_7``, which is
            None if the IPMC does not report it.
        """
        return self.send_message_with_name('VitaGetFruAddressInfo',
                                           fru_id=fru_id)

    def vita_fru_control(self, fru_id: int, option: int) -> None:
        """Control a FRU, e.g. reset it.

        Args:
            fru_id: The FRU device ID.
            option: One of ``VITA_FRU_CONTROL_COLD_RESET``,
                ``VITA_FRU_CONTROL_WARM_RESET``,
                ``VITA_FRU_CONTROL_GRACEFUL_REBOOT`` or
                ``VITA_FRU_CONTROL_DIAGNOSTIC_INTERRUPT``.

        Raises:
            CompletionCodeError: The IPMC rejected the request, e.g. for an
                option the FRU does not support.
        """
        self.send_message_with_name('VitaFruControl', fru_id=fru_id,
                                    option=option)

    def set_vita_fru_activation(self, fru_id: int) -> None:
        """Activate a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.send_message_with_name('VitaSetFruActivation', fru_id=fru_id,
                                    control=VITA_FRU_ACTIVATE)

    def set_vita_fru_deactivation(self, fru_id: int) -> None:
        """Deactivate a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.send_message_with_name('VitaSetFruActivation', fru_id=fru_id,
                                    control=VITA_FRU_DEACTIVATE)

    def get_vita_fru_state_policy(self, fru_id: int) -> Message:
        """Get the FRU state policy bits of a FRU.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The response with the field ``activation_policies`` and its
            bits ``activation_lock``, ``deactivation_lock``,
            ``commanded_deactivation_ignored`` and
            ``default_activation_locked``.
        """
        return self.send_message_with_name('VitaGetFruStatePolicy',
                                           fru_id=fru_id)

    def set_vita_fru_state_policy(self, fru_id: int, mask: int,
                                  value: int) -> None:
        """Set the FRU state policy bits selected by a mask.

        Args:
            fru_id: The FRU device ID.
            mask: The ``VITA_POLICY_*`` bits to change.
            value: The new values of the bits selected by ``mask``.

        Example:
            Lock the activation and unlock the deactivation::

                ipmi.set_vita_fru_state_policy(
                    0,
                    mask=VITA_POLICY_ACTIVATION_LOCKED
                    | VITA_POLICY_DEACTIVATION_LOCKED,
                    value=VITA_POLICY_ACTIVATION_LOCKED)
        """
        req = create_request_by_name('VitaSetFruStatePolicy')
        req.fru_id = fru_id
        req.activation_policy_mask._value = mask
        req.activation_policy_set._value = value
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_vita_led_properties(self, fru_id: int) -> Message:
        """Get the LED properties of a FRU.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The response with the field ``led_count``, the number of LEDs
            of the FRU.
        """
        return self.send_message_with_name('VitaGetFruLedProperties',
                                           fru_id=fru_id)

    def get_vita_led_color_capabilities(self, fru_id: int,
                                        led_id: int) -> Message:
        """Get the color capabilities of a LED.

        Args:
            fru_id: The FRU device ID.
            led_id: The LED ID.

        Returns:
            The response with the fields ``color_capabilities`` (bits
            ``blue``, ``red``, ``green``, ``amber``, ``orange`` and
            ``white``), ``default_color_local_control`` and
            ``default_color_override_control`` (bit ``value``, a
            ``VITA_LED_COLOR_*`` value) and ``flags``, which is None if the
            IPMC does not report it.
        """
        return self.send_message_with_name('VitaGetFruLedCapabilities',
                                           fru_id=fru_id, led_id=led_id)

    def get_vita_led_state(self, fru_id: int, led_id: int) -> Message:
        """Get the state of a LED.

        Args:
            fru_id: The FRU device ID.
            led_id: The LED ID.

        Returns:
            The response with the fields ``state`` (bits ``ipmc_control``,
            ``override``, ``lamp_test`` and ``hardware_restrict``),
            ``local_control_function``, ``local_control_on_duration`` and
            ``local_control_color``. The fields ``override_state``,
            ``override_on_duration``, ``override_color`` and
            ``lamp_test_duration`` are None if the IPMC does not report
            them.
        """
        return self.send_message_with_name('VitaGetFruLedState',
                                           fru_id=fru_id, led_id=led_id)

    def set_vita_led_state(self, fru_id: int, led_id: int, function: int,
                           on_duration: int = 0,
                           color: int = VITA_LED_COLOR_DEFAULT) -> None:
        """Set the state of a LED.

        Args:
            fru_id: The FRU device ID.
            led_id: The LED ID, ``VITA_LED_ALL`` for all LEDs of the FRU.
            function: ``VITA_LED_FUNCTION_OFF``, ``VITA_LED_FUNCTION_ON``,
                ``VITA_LED_FUNCTION_LAMP_TEST``,
                ``VITA_LED_FUNCTION_LOCAL_CONTROL``, or 1 - 250 to let the
                LED blink with this off duration in tens of milliseconds.
            on_duration: The on duration of a blinking LED in tens of
                milliseconds, or the lamp test duration in hundreds of
                milliseconds.
            color: One of the ``VITA_LED_COLOR_*`` values.
        """
        self.send_message_with_name('VitaSetFruLedState', fru_id=fru_id,
                                    led_id=led_id, function=function,
                                    on_duration=on_duration, color=color)
