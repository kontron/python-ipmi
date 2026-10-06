# Copyright (c) 2014  Kontron Europe GmbH
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

"""PICMG commands of AdvancedTCA and MicroTCA systems.

The PICMG 3.0 (AdvancedTCA) and MTCA.0 (MicroTCA) specifications define
IPMI commands of the PICMG group extension: FRU control and activation,
power levels, fans, LEDs, E-Keying of the backplane ports and the power
channels of a MicroTCA power module.

The commands are the methods of :class:`Picmg`, which are available on
:class:`pyipmi.Ipmi`.

Example:
    Read the port state of fabric channel 1::

        from pyipmi.picmg import LinkDescriptor

        link, state = ipmi.get_port_state(1, LinkDescriptor.INTERFACE_FABRIC)
        if link is not None:
            print(link.get_link_type_string(link.type, link.extension,
                                            link.sig_class), state)
"""

from __future__ import annotations

from .errors import DecodingError, EncodingError
from .msgs import create_request_by_name, Message
from .msgs import picmg
from .utils import check_completion_code
from .state import State
from .mixin import IpmiMixin

from .msgs.picmg import \
        FRU_CONTROL_COLD_RESET, FRU_CONTROL_WARM_RESET, \
        FRU_CONTROL_GRACEFUL_REBOOT, FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT, \
        FRU_ACTIVATION_FRU_ACTIVATE, FRU_ACTIVATION_FRU_DEACTIVATE


class Picmg(IpmiMixin):
    """PICMG commands, available on :class:`pyipmi.Ipmi`.

    The ``*_LOCK_*`` constants are the controls of
    :meth:`set_fru_activation_policy`.
    """
    def get_picmg_properties(self) -> Message:
        """Get the PICMG properties of the IPM controller.

        Returns:
            The response with the fields ``extension_version`` (the PICMG
            extension version), ``max_fru_device_id`` and ``fru_device_id``
            (the FRU device ID of the IPM controller).
        """
        return self.send_message_with_name('GetPicmgProperties')

    def fru_control(self, fru_id: int, option: int) -> bytes:
        """Control a FRU, e.g. reset it.

        Args:
            fru_id: The FRU device ID.
            option: One of the ``FRU_CONTROL_*`` constants of
                ``pyipmi.msgs.picmg``.

        Returns:
            The remaining response data after the PICMG identifier.

        Raises:
            CompletionCodeError: The controller rejected the request, e.g. for
                an option the FRU does not support.
        """
        rsp = self.send_message_with_name('FruControl', fru_id=fru_id,
                                          option=option)
        return rsp.rsp_data

    def fru_control_cold_reset(self, fru_id: int = 0) -> None:
        """Cold reset a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.fru_control(fru_id, FRU_CONTROL_COLD_RESET)

    def fru_control_warm_reset(self, fru_id: int = 0) -> None:
        """Warm reset a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.fru_control(fru_id, FRU_CONTROL_WARM_RESET)

    def fru_control_graceful_reboot(self, fru_id: int = 0) -> None:
        """Gracefully reboot a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.fru_control(fru_id, FRU_CONTROL_GRACEFUL_REBOOT)

    def fru_control_diagnostic_interrupt(self, fru_id: int = 0) -> bytes:
        """Issue a diagnostic interrupt to a FRU.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The remaining response data after the PICMG identifier.
        """
        return self.fru_control(fru_id, FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT)

    def get_power_level(self, fru_id: int, power_type: int) -> PowerLevel:
        """Get the power levels of a FRU.

        Args:
            fru_id: The FRU device ID.
            power_type: The power type, 0 for the steady state power draw
                levels, 1 for the desired steady state draw levels, 2 for the
                early power draw levels and 3 for the desired early levels.

        Returns:
            The power levels.
        """
        rsp = self.send_message_with_name('GetPowerLevel',
                                          fru_id=fru_id,
                                          power_type=power_type)
        return PowerLevel(rsp)

    def get_fan_speed_properties(self, fru_id: int) -> FanSpeedProperties:
        """Get the fan speed properties of a fan tray.

        Args:
            fru_id: The FRU device ID of the fan tray.

        Returns:
            The fan speed properties.
        """
        rsp = self.send_message_with_name('GetFanSpeedProperties',
                                          fru_id=fru_id)
        return FanSpeedProperties(rsp)

    def set_fan_level(self, fru_id: int, fan_level: int) -> None:
        """Set the fan level of a fan tray.

        Args:
            fru_id: The FRU device ID of the fan tray.
            fan_level: The fan level, between the minimum and maximum speed
                level of :meth:`get_fan_speed_properties`.
        """
        self.send_message_with_name('SetFanLevel',
                                    fru_id=fru_id,
                                    fan_level=fan_level)

    def get_fan_level(self, fru_id: int) -> tuple:
        """Get the fan level of a fan tray.

        Args:
            fru_id: The FRU device ID of the fan tray.

        Returns:
            A tuple of the override fan level and the local control fan level,
            which is None if the fan tray does not report it.
        """
        rsp = self.send_message_with_name('GetFanLevel', fru_id=fru_id)
        local_control_fan_level = None
        if rsp.data:
            local_control_fan_level = rsp.data[0]
        return (rsp.override_fan_level, local_control_fan_level)

    def get_led_state(self, fru_id: int, led_id: int) -> LedState:
        """Get the state of a FRU LED.

        Args:
            fru_id: The FRU device ID.
            led_id: The LED ID.

        Returns:
            The LED state, the durations are in milliseconds.

        Raises:
            DecodingError: The LED function in the response is invalid.
        """
        rsp = self.send_message_with_name('GetFruLedState',
                                          fru_id=fru_id,
                                          led_id=led_id)
        return LedState(rsp)

    def set_led_state(self, led: LedState) -> None:
        """Set the state of a FRU LED.

        Args:
            led: The LED state with ``fru_id``, ``led_id``,
                ``override_color`` and ``override_function``. A blinking LED
                needs ``override_off_duration`` and ``override_on_duration``,
                a lamp test ``lamp_test_duration``, all in milliseconds. See
                :meth:`LedState.to_request` for their ranges.

        Raises:
            EncodingError: A duration is not set, out of range or not a
                multiple of its step.

        Example:
            Switch on the blue LED of FRU 0::

                from pyipmi.picmg import LedState

                ipmi.set_led_state(LedState(fru_id=0, led_id=0,
                                            color=LedState.COLOR_BLUE,
                                            function=LedState.FUNCTION_ON))
        """
        req = create_request_by_name('SetFruLedState')
        req = led.to_request(req)
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def _set_fru_activation(self, fru_id: int, control: int) -> None:
        self.send_message_with_name('SetFruActivation',
                                    fru_id=fru_id,
                                    control=control)

    def set_fru_activation(self, fru_id: int) -> None:
        """Activate a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self._set_fru_activation(fru_id, FRU_ACTIVATION_FRU_ACTIVATE)

    def set_fru_deactivation(self, fru_id: int) -> None:
        """Deactivate a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self._set_fru_activation(fru_id, FRU_ACTIVATION_FRU_DEACTIVATE)

    ACTIVATION_LOCK_SET = 0
    ACTIVATION_LOCK_CLEAR = 1
    DEACTIVATION_LOCK_SET = 2
    DEACTIVATION_LOCK_CLEAR = 3

    def set_fru_activation_policy(self, fru_id: int, ctrl: int) -> None:
        """Set or clear the activation or deactivation lock of a FRU.

        Args:
            fru_id: The FRU device ID.
            ctrl: One of ``ACTIVATION_LOCK_SET``, ``ACTIVATION_LOCK_CLEAR``,
                ``DEACTIVATION_LOCK_SET`` or ``DEACTIVATION_LOCK_CLEAR``. For
                other values the request changes nothing.
        """
        req = create_request_by_name('SetFruActivationPolicy')
        req.fru_id = fru_id

        if ctrl == self.ACTIVATION_LOCK_SET:
            req.mask.activation_locked = 1
            req.set.activation_locked = 1
        elif ctrl == self.ACTIVATION_LOCK_CLEAR:
            req.mask.activation_locked = 1
            req.set.activation_locked = 0
        elif ctrl == self.DEACTIVATION_LOCK_SET:
            req.mask.deactivation_locked = 1
            req.set.deactivation_locked = 1
        elif ctrl == self.DEACTIVATION_LOCK_CLEAR:
            req.mask.deactivation_locked = 1
            req.set.deactivation_locked = 0

        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_fru_activation_lock(self, fru_id: int) -> None:
        """Set the activation lock of a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.set_fru_activation_policy(fru_id, self.ACTIVATION_LOCK_SET)

    def clear_fru_activation_lock(self, fru_id: int) -> None:
        """Clear the activation lock of a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.set_fru_activation_policy(fru_id, self.ACTIVATION_LOCK_CLEAR)

    def set_fru_deactivation_lock(self, fru_id: int) -> None:
        """Set the deactivation lock of a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.set_fru_activation_policy(fru_id, self.DEACTIVATION_LOCK_SET)

    def clear_fru_deactivation_lock(self, fru_id: int) -> None:
        """Clear the deactivation lock of a FRU.

        Args:
            fru_id: The FRU device ID.
        """
        self.set_fru_activation_policy(fru_id, self.DEACTIVATION_LOCK_CLEAR)

    def set_port_state(self, link_descr: LinkDescriptor, state: int) -> None:
        """Enable or disable a link of a backplane port (E-Keying).

        Args:
            link_descr: The link.
            state: ``LinkDescriptor.STATE_ENABLE`` or
                ``LinkDescriptor.STATE_DISABLE``.
        """
        req = create_request_by_name('SetPortState')
        req.link_info.channel = link_descr.channel
        req.link_info.interface = link_descr.interface
        req.link_info.port_0 = (link_descr.link_flags >> 0) & 1
        req.link_info.port_1 = (link_descr.link_flags >> 1) & 1
        req.link_info.port_2 = (link_descr.link_flags >> 2) & 1
        req.link_info.port_3 = (link_descr.link_flags >> 3) & 1
        req.link_info.type = link_descr.type
        req.link_info.sig_class = link_descr.sig_class
        req.link_info.type_extension = link_descr.extension
        req.link_info.grouping_id = link_descr.grouping_id
        req.state = state
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_port_state(self, channel_number: int, channel_interface: int,
                       ) -> tuple[LinkDescriptor | None, int | None]:
        """Get the state of a link of a backplane port (E-Keying).

        Args:
            channel_number: The channel number.
            channel_interface: The interface, one of the ``INTERFACE_*``
                constants of :class:`LinkDescriptor`.

        Returns:
            A tuple of the link and its state (``LinkDescriptor.STATE_*``),
            both None if the port is not supported.
        """
        req = create_request_by_name('GetPortState')
        req.channel.number = channel_number
        req.channel.interface = channel_interface
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

        # no link information if the port is not supported
        link = None
        state = None
        if len(rsp.data) > 4:
            link = LinkDescriptor()
            link.channel = rsp.data[0] & 0x3F
            link.interface = rsp.data[0] >> 6 & 0x3
            link.link_flags = rsp.data[1] & 0xf
            link.type = rsp.data[1] >> 4 & 0xf
            link.sig_class = rsp.data[2] & 0xf
            link.extension = rsp.data[2] >> 4 & 0xf
            link.grouping_id = rsp.data[3]
            state = rsp.data[4]

        return (link, state)

    def get_pm_global_status(self) -> GlobalStatus:
        """Get the global status of a MicroTCA power module.

        Returns:
            The global status.
        """
        rsp = self.send_message_with_name('GetPowerChannelStatus',
                                          starting_power_channel_number=1,
                                          power_channel_count=1)
        return GlobalStatus(rsp)

    def get_power_channel_status(self, start: int) -> PowerChannelStatus:
        """Get the status of a power channel of a MicroTCA power module.

        Args:
            start: The power channel number.

        Returns:
            The status of the power channel.
        """
        rsp = self.send_message_with_name('GetPowerChannelStatus',
                                          starting_power_channel_number=start,
                                          power_channel_count=1)
        return PowerChannelStatus(rsp)

    def send_channel_power(self, channel: int, enable: bool,
                           current_limit: float, primary_pm: int = 1,
                           backup_pm: int = 0) -> Message:
        """Enable or disable a power channel of a MicroTCA power module.

        Args:
            channel: The power channel number.
            enable: True to enable the power channel, False to disable it.
            current_limit: The current limit in amperes, it is sent in units
                of 0.1 A.
            primary_pm: The primary power module of the channel.
            backup_pm: The backup power module of the channel.

        Returns:
            The response of the power module.
        """
        rsp = self.send_message_with_name('SendPowerChannelControl',
                                          channel=channel,
                                          control=5 if enable else 4,
                                          current_limit=int(current_limit * 10),
                                          primary_pm=primary_pm,
                                          backup_pm=backup_pm
                                          )
        return rsp

    def send_pm_heartbeat(self) -> Message:
        """Send a heartbeat to a MicroTCA power module.

        Returns:
            The response of the power module.
        """
        rsp = self.send_message_with_name('SendPmHeartbeat')
        return rsp

    def set_signaling_class(self, interface: int, channel: int,
                            signaling_class: int) -> None:
        """Set the signaling class of a channel.

        Args:
            interface: The interface, one of the ``INTERFACE_*`` constants of
                :class:`LinkDescriptor`.
            channel: The channel number.
            signaling_class: The signaling class, one of the
                ``SIGNALING_CLASS_*`` constants of :class:`LinkDescriptor`.
        """
        req = create_request_by_name('SetSignalingClass')
        req.channel_info.channel_number = channel
        req.channel_info.interface = interface
        req.channel_signaling.class_capability = signaling_class
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_signaling_class(self, interface: int, channel: int) -> int:
        """Get the signaling class of a channel.

        Args:
            interface: The interface, one of the ``INTERFACE_*`` constants of
                :class:`LinkDescriptor`.
            channel: The channel number.

        Returns:
            The signaling class, one of the ``SIGNALING_CLASS_*`` constants of
            :class:`LinkDescriptor`.
        """
        req = create_request_by_name('GetSignalingClass')
        req.channel_info.channel_number = channel
        req.channel_info.interface = interface
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.channel_signaling.class_capability


class LinkDescriptor(State):
    """A link of a backplane port, used for E-Keying.

    The class constants are the values of the attributes: ``INTERFACE_*``,
    ``TYPE_*`` and ``TYPE_EXT_*`` (link type and extension),
    ``SIGNALING_CLASS_*``, ``FLAGS_*`` (link flags) and ``STATE_*`` (port
    state).
    """

    # TODO dont duplicate exports, import them instead
    INTERFACE_BASE = picmg.LINK_INTERFACE_BASE
    INTERFACE_FABRIC = picmg.LINK_INTERFACE_FABRIC
    INTERFACE_UPDATE_CHANNEL = picmg.LINK_INTERFACE_UPDATE_CHANNEL

    TYPE_BASE = picmg.LINK_TYPE_BASE
    TYPE_ETHERNET_FABRIC = picmg.LINK_TYPE_ETHERNET_FABRIC
    TYPE_INFINIBAND_FABRIC = picmg.LINK_TYPE_INFINIBAND_FABRIC
    TYPE_STARFABRIC_FABRIC = picmg.LINK_TYPE_STARFABRIC_FABRIC
    TYPE_PCIEXPRESS_FABRIC = picmg.LINK_TYPE_PCIEXPRESS_FABRIC
    TYPE_OEM0 = picmg.LINK_TYPE_OEM0
    TYPE_OEM1 = picmg.LINK_TYPE_OEM1
    TYPE_OEM2 = picmg.LINK_TYPE_OEM2
    TYPE_OEM3 = picmg.LINK_TYPE_OEM3

    TYPE_EXT_BASE0 = picmg.LINK_TYPE_EXT_BASE0
    TYPE_EXT_BASE1 = picmg.LINK_TYPE_EXT_BASE1

    SIGNALING_CLASS_BASIC = picmg.LINK_SIGNALING_CLASS_BASIC
    SIGNALING_CLASS_10_3125_GBD = picmg.LINK_SIGNALING_CLASS_10_3125_GBD

    TYPE_EXT_ETHERNET_FIX1000_BX = picmg.LINK_TYPE_EXT_ETHERNET_FIX1000_BX
    TYPE_EXT_ETHERNET_FIX10G_BX4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX10G_BX4
    TYPE_EXT_ETHERNET_FCPI = picmg.LINK_TYPE_EXT_ETHERNET_FCPI
    TYPE_EXT_ETHERNET_FIX1000_KX = picmg.LINK_TYPE_EXT_ETHERNET_FIX1000_KX
    TYPE_EXT_ETHERNET_FIX10G_KX4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX10G_KX4

    TYPE_EXT_ETHERNET_FIX10G_KR = picmg.LINK_TYPE_EXT_ETHERNET_FIX10G_KR
    TYPE_EXT_ETHERNET_FIX40G_KR4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX40G_KR4

    TYPE_EXT_OEM_LINK_TYPE_EXT_0 = picmg.LINK_TYPE_EXT_OEM_LINK_TYPE_EXT_0

    FLAGS_LANE0 = picmg.LINK_FLAGS_LANE0
    FLAGS_LANE0123 = picmg.LINK_FLAGS_LANE0123

    STATE_DISABLE = picmg.LINK_STATE_DISABLE
    STATE_ENABLE = picmg.LINK_STATE_ENABLE

    #: The channel number.
    channel: int
    #: The interface, one of the ``INTERFACE_*`` constants.
    interface: int
    #: The ports of the channel that are part of the link, one bit per
    #: port, see the ``FLAGS_*`` constants.
    link_flags: int
    #: The link type, one of the ``TYPE_*`` constants.
    type: int
    #: The signaling class, one of the ``SIGNALING_CLASS_*`` constants.
    sig_class: int
    #: The link type extension, one of the ``TYPE_EXT_*`` constants.
    extension: int
    #: The link grouping ID.
    grouping_id: int

    __properties__ = [
        # (property, description)
        ('channel', ''),
        ('interface', ''),
        ('link_flags', ''),
        ('type', ''),
        ('sig_class', ''),
        ('extension', ''),
        ('grouping_id', ''),
    ]

    INTERFACE_DESCR_STRING = [
        # Interface, 'STRING'
        (INTERFACE_BASE, 'Base'),
        (INTERFACE_FABRIC, 'Fabric'),
        (INTERFACE_UPDATE_CHANNEL, 'Update Channel'),
    ]

    def get_interface_string(self, interf: int) -> str:
        """Return the name of an interface.

        Args:
            interf: The interface, one of the ``INTERFACE_*`` constants.

        Returns:
            The name of the interface, 'unknown' for an unknown interface.
        """
        for desc in self.INTERFACE_DESCR_STRING:
            if desc[0] == interf:
                return desc[1]
        return 'unknown'

    LINK_TYPE_DESCR_STRING = [
        # Type, Extension, class, 'STRING'
        (TYPE_BASE,
         TYPE_EXT_BASE0,
         SIGNALING_CLASS_BASIC,
         '10/100/1000 BASE-T'),
        (TYPE_BASE,
         TYPE_EXT_BASE1,
         SIGNALING_CLASS_BASIC,
         '10/100 BASE-T ShMC Cross-connect'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX1000_BX,
         SIGNALING_CLASS_BASIC,
         'Fixed 1000BASE-BX'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX10G_BX4,
         SIGNALING_CLASS_BASIC,
         'Fixed 10GBASE-BX4 (XAUI)'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FCPI,
         SIGNALING_CLASS_BASIC,
         'FC-PI'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX1000_KX,
         SIGNALING_CLASS_BASIC,
         'Fixed 1000BASE-KX'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX10G_KX4,
         SIGNALING_CLASS_BASIC,
         'Fixed 10GBASE-KX4'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX10G_KR,
         SIGNALING_CLASS_10_3125_GBD,
         'Fixed 10GBASE-KR'),
        (TYPE_ETHERNET_FABRIC,
         TYPE_EXT_ETHERNET_FIX40G_KR4,
         SIGNALING_CLASS_10_3125_GBD,
         'Fixed 40GBASE-KR4'),
    ]

    def get_link_type_string(self, link_type: int, ext: int, cls: int = 0) -> str:
        """Return the name of a link type.

        Args:
            link_type: The link type, one of the ``TYPE_*`` constants.
            ext: The link type extension, one of the ``TYPE_EXT_*`` constants.
            cls: The signaling class, one of the ``SIGNALING_CLASS_*``
                constants.

        Returns:
            The name of the link type, 'unknown' for an unknown link type.
        """
        for desc in self.LINK_TYPE_DESCR_STRING:
            if desc[0] == link_type and desc[1] == ext and desc[2] == cls:
                return desc[3]
        return 'unknown'


class PowerLevel(State):
    """The power levels of a FRU.

    The power draw of a level is its value times ``power_mulitplier``
    tenths of a watt.

    Attributes:
        dynamic_power_configuration (int): 1 if the FRU supports dynamic
            power configuration.
        power_level (int): The current power level, 0 if the FRU has no
            power.
        delay_to_stable (int): The delay to stable power in tenths of a
            second.
        power_mulitplier (int): The power multiplier in tenths of a watt.
        power_levels (Sequence[int]): The power draw values of the levels.
    """

    def _from_response(self, rsp: Message) -> None:
        self.dynamic_power_configuration = \
                rsp.properties.dynamic_power_configuration
        self.power_level = rsp.properties.power_level
        self.delay_to_stable = rsp.delay_to_stable_power
        self.power_mulitplier = rsp.power_multiplier
        self.power_levels = rsp.power_draw


class FanSpeedProperties(State):
    """The fan speed properties of a fan tray.

    Attributes:
        minimum_speed_level (int): The minimum fan level.
        maximum_speed_level (int): The maximum fan level.
        normal_operation_level (int): The fan level of the normal
            operation.
        local_control_supported (int): 1 if the fan tray supports local
            control of the fan level.
    """

    def _from_response(self, rsp: Message) -> None:
        self.minimum_speed_level = rsp.minimum_speed_level
        self.maximum_speed_level = rsp.maximum_speed_level
        self.normal_operation_level = rsp.normal_operation_level
        self.local_control_supported = rsp.properties.local_control_supported


def _led_duration(duration: int | None, unit: int, minimum: int,
                  maximum: int) -> int:
    """Convert a LED duration in milliseconds to the unit of the request.

    Args:
        duration: The duration in milliseconds.
        unit: The unit of the request in milliseconds.
        minimum: The minimum value in the unit of the request.
        maximum: The maximum value in the unit of the request.

    Returns:
        The duration in the unit of the request.

    Raises:
        EncodingError: The duration is not set, not a multiple of the unit
            or out of range.
    """
    if duration is None or duration % unit \
            or not minimum <= duration // unit <= maximum:
        raise EncodingError(f'LED duration {duration} ms is not a multiple '
                            f'of {unit} ms between {minimum * unit} and '
                            f'{maximum * unit} ms')
    return duration // unit


class LedState(State):
    """The state of a FRU LED.

    The state is returned by :meth:`Picmg.get_led_state` and passed to
    :meth:`Picmg.set_led_state`. The ``FUNCTION_*`` constants are the LED
    functions, the ``COLOR_*`` constants the colors. All durations are in
    milliseconds.

    Attributes:
        fru_id (int): The FRU device ID.
        led_id (int): The LED ID.
        local_state_available (bool): The LED has a local control state.
        override_enabled (bool): The override state is active.
        lamp_test_enabled (bool): A lamp test is active.
        local_function (int): The function of the local control state.
        local_off_duration (int): The off duration of the blinking local
            control state.
        local_on_duration (int): The on duration of the blinking local
            control state.
        local_color (int): The color of the local control state.
        override_function (int): The function of the override state.
        override_off_duration (int): The off duration of the blinking
            override state.
        override_on_duration (int): The on duration of the blinking
            override state.
        override_color (int): The color of the override state.
        lamp_test_duration (int): The duration of the lamp test.
    """

    COLOR_BLUE = picmg.LED_COLOR_BLUE
    COLOR_RED = picmg.LED_COLOR_RED
    COLOR_GREEN = picmg.LED_COLOR_GREEN
    COLOR_AMBER = picmg.LED_COLOR_AMBER
    COLOR_ORANGE = picmg.LED_COLOR_ORANGE
    COLOR_WHITE = picmg.LED_COLOR_WHITE

    FUNCTION_OFF = 1
    FUNCTION_BLINKING = 2
    FUNCTION_ON = 3
    FUNCTION_LAMP_TEST = 4

    __properties__ = [
        # (property, description)
        ('fru_id', ''),
        ('led_id', ''),
        ('local_state_available', ''),
        ('override_enabled', ''),
        ('lamp_test_enabled', ''),
        ('local_function', ''),
        ('local_off_duration', ''),
        ('local_on_duration', ''),
        ('local_color', ''),
        ('override_function', ''),
        ('override_off_duration', ''),
        ('override_on_duration', ''),
        ('override_color', ''),
        ('lamp_test_duration', ''),
    ]

    def __init__(self, rsp: Message | None = None, fru_id: int | None = None,
                 led_id: int | None = None, color: int | None = None,
                 function: int | None = None) -> None:
        """Create the LED state, from a response or from the arguments.

        Args:
            rsp: The response of Get FRU LED State, it is decoded if it is
                not None.
            fru_id: The FRU device ID.
            led_id: The LED ID.
            color: The color of the override state, one of the ``COLOR_*``
                constants.
            function: The function of the override state, one of the
                ``FUNCTION_*`` constants.

        Raises:
            DecodingError: The LED function in the response is invalid.
        """
        super().__init__(rsp)
        if fru_id is not None:
            self.fru_id = fru_id
        if led_id is not None:
            self.led_id = led_id
        if color is not None:
            self.override_color = color
        if function is not None:
            self.override_function = function

    def __str__(self) -> str:
        """Return the flags, functions and colors of the LED state."""
        string = '[flags '
        string += self.local_state_available and ' LOCAL_STATE' or ''
        string += self.override_enabled and ' OVR_EN' or ''
        string += self.lamp_test_enabled and ' LAMP_TEST_EN' or ''
        if not self.local_state_available and not self.override_enabled \
                and not self.lamp_test_enabled:
            string += ' NONE'
        if self.local_state_available:
            string += ' local_function %s local_color %s' % (
                self.local_function, self.local_color)
        if self.override_enabled:
            string += ' override_function %s override_color %s' % (
                self.override_function, self.override_color)
        string += ']'
        return string

    def _from_response(self, res: Message) -> None:
        self.local_state_available = bool(res.led_states.local_avail)
        self.override_enabled = bool(res.led_states.override_en)
        self.lamp_test_enabled = bool(res.led_states.lamp_test_en)

        if res.local_function == picmg.LED_FUNCTION_OFF:
            self.local_function = self.FUNCTION_OFF
        elif res.local_function == picmg.LED_FUNCTION_ON:
            self.local_function = self.FUNCTION_ON
        elif res.local_function in picmg.LED_FUNCTION_BLINKING_RANGE:
            self.local_function = self.FUNCTION_BLINKING
            self.local_off_duration = res.local_function * 10
            if res.local_on_duration not in picmg.LED_FUNCTION_BLINKING_RANGE:
                raise DecodingError()
            self.local_on_duration = res.local_on_duration * 10
        else:
            raise DecodingError()

        self.local_color = res.local_color

        if self.override_enabled:
            if res.override_function == picmg.LED_FUNCTION_OFF:
                self.override_function = self.FUNCTION_OFF
            elif res.override_function == picmg.LED_FUNCTION_ON:
                self.override_function = self.FUNCTION_ON
            elif res.override_function in picmg.LED_FUNCTION_BLINKING_RANGE:
                self.override_function = self.FUNCTION_BLINKING
                self.override_off_duration = res.override_function * 10
                self.override_on_duration = res.override_on_duration * 10
            else:
                raise DecodingError()

            self.override_color = res.override_color

        if self.lamp_test_enabled:
            self.lamp_test_duration = res.lamp_test_duration * 100

    def to_request(self, req: Message) -> Message:
        """Fill a Set FRU LED State request with the override state.

        The durations are converted from milliseconds to the units of the
        request. A blinking LED has an off duration of 10 - 2500 ms and an
        on duration of 0 - 2550 ms in steps of 10 ms, a lamp test takes
        0 - 12700 ms in steps of 100 ms.

        Args:
            req: The Set FRU LED State request.

        Returns:
            The request.

        Raises:
            EncodingError: A duration is not set, out of range or not a
                multiple of its step.
        """
        req.fru_id = self.fru_id
        req.led_id = self.led_id
        req.color = self.override_color

        if self.override_function == self.FUNCTION_ON:
            req.led_function = picmg.LED_FUNCTION_ON
            req.on_duration = 0
        elif self.override_function == self.FUNCTION_OFF:
            req.led_function = picmg.LED_FUNCTION_OFF
            req.on_duration = 0
        elif self.override_function == self.FUNCTION_BLINKING:
            req.led_function = _led_duration(
                self.override_off_duration, 10,
                picmg.LED_FUNCTION_BLINKING_RANGE[0],
                picmg.LED_FUNCTION_BLINKING_RANGE[-1])
            req.on_duration = _led_duration(
                self.override_on_duration, 10, 0, 0xff)
        elif self.override_function == self.FUNCTION_LAMP_TEST:
            req.led_function = picmg.LED_FUNCTION_LAMP_TEST
            req.on_duration = _led_duration(
                self.lamp_test_duration, 100, 0, 0x7f)
        else:
            raise AssertionError()

        return req


class GlobalStatus(State):
    """The global status of a MicroTCA power module.

    Attributes:
        role (int): The role of the power module, 1 for primary, 0 for
            redundant.
        management_power_good (bool): The management power is good.
        payload_power_good (bool): The payload power is good.
        unidentified_fault (bool): An unidentified fault occurred.
    """

    __properties__ = [
        # (property, description)
        ('role', ''),
        ('management_power_good', ''),
        ('payload_power_good', ''),
        ('unidentified_fault', ''),
    ]

    def _from_response(self, rsp: Message) -> None:
        self.role = rsp.global_status.role
        self.management_power_good = \
            bool(rsp.global_status.management_power_good)
        self.payload_power_good = \
            bool(rsp.global_status.payload_power_good)
        self.unidentified_fault = \
            bool(rsp.global_status.unidentified_fault)


class PowerChannelStatus(State):
    """The status of a power channel of a MicroTCA power module.

    The status flags are 1 if set.

    Attributes:
        present (int): A module is present on the channel.
        management_power (int): The management power is on.
        management_power_overcurrent (int): The management power is
            overcurrent.
        enable (int): The channel is enabled.
        payload_power (int): The payload power is on.
        payload_power_overcurrent (int): The payload power is overcurrent.
        pwr_on (int): The PWR_ON signal is active.
    """

    __properties__ = [
        # (property, description)
        ('present', ''),
        ('management_power', ''),
        ('management_power_overcurrent', ''),
        ('enable', ''),
        ('payload_power', ''),
        ('payload_power_overcurrent', ''),
        ('pwr_on', ''),
    ]

    def _from_response(self, rsp: Message) -> None:
        data = rsp.data[0]
        self.present = (data >> 0) & 1
        self.management_power = (data >> 1) & 1
        self.management_power_overcurrent = (data >> 2) & 1
        self.enable = (data >> 3) & 1
        self.payload_power = (data >> 4) & 1
        self.payload_power_overcurrent = (data >> 5) & 1
        self.pwr_on = (data >> 6) & 1
