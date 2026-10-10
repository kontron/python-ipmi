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

"""Chassis commands: status, power control, identify and boot options.

The commands are the methods of :class:`Chassis`, which are available on
:class:`pyipmi.Ipmi`. The ``CONTROL_*`` constants are the options of
:meth:`Chassis.chassis_control`, the ``POWER_RESTORE_POLICY_*`` constants
the policies of :meth:`Chassis.set_power_restore_policy`, the
``RESTART_CAUSE_*`` constants the causes of
:meth:`Chassis.get_system_restart_cause`, and the ``BOOT_PARAMETER_*``
constants the boot option parameters of
:meth:`Chassis.get_system_boot_options` and
:meth:`Chassis.set_system_boot_options`.

Example:
    Boot from the network once and power cycle the system::

        from pyipmi.chassis import BootDevice

        ipmi.set_boot_options(BootDevice.PXE, 'efi', False)
        ipmi.chassis_control_power_cycle()
"""

from __future__ import annotations

from array import array
from enum import Enum


from .msgs import create_request_by_name, Message
from .utils import check_completion_code, check_rsp_completion_code, ByteBuffer
from .state import State
from .mixin import IpmiMixin

from .msgs.chassis import \
        CONTROL_POWER_DOWN, CONTROL_POWER_UP, CONTROL_POWER_CYCLE, \
        CONTROL_HARD_RESET, CONTROL_DIAGNOSTIC_INTERRUPT, \
        CONTROL_SOFT_SHUTDOWN

BOOT_PARAMETER_SET_IN_PROGRESS = 0
BOOT_PARAMETER_SERVICE_PARTITION_SELECTOR = 1
BOOT_PARAMETER_SERVICE_PARTITION_SCAN = 2
BOOT_PARAMETER_BMC_BOOT_FLAG_VALID_BIT_CLEARING = 3
BOOT_PARAMETER_BOOT_INFO_ACKNOWLEDGE = 4
BOOT_PARAMETER_BOOT_FLAGS = 5
BOOT_PARAMETER_BOOT_INITIATOR_INFO = 6
BOOT_PARAMETER_BOOT_INITIATOR_MAILBOX = 7

# the power restore policies after AC/mains power returns
POWER_RESTORE_POLICY_ALWAYS_OFF = 0
POWER_RESTORE_POLICY_RESTORE_PREVIOUS = 1
POWER_RESTORE_POLICY_ALWAYS_ON = 2
# only for the request, to get the supported policies
POWER_RESTORE_POLICY_NO_CHANGE = 3

# the causes of the last system restart
RESTART_CAUSE_UNKNOWN = 0x0
RESTART_CAUSE_CHASSIS_CONTROL = 0x1
RESTART_CAUSE_RESET_BUTTON = 0x2
RESTART_CAUSE_POWER_BUTTON = 0x3
RESTART_CAUSE_WATCHDOG = 0x4
RESTART_CAUSE_OEM = 0x5
RESTART_CAUSE_POWER_RESTORE_ALWAYS_ON = 0x6
RESTART_CAUSE_POWER_RESTORE_PREVIOUS = 0x7
RESTART_CAUSE_PEF_RESET = 0x8
RESTART_CAUSE_PEF_POWER_CYCLE = 0x9
RESTART_CAUSE_SOFT_RESET = 0xa
RESTART_CAUSE_RTC_WAKEUP = 0xb

RESTART_CAUSE_NAMES = {
    RESTART_CAUSE_UNKNOWN: 'unknown',
    RESTART_CAUSE_CHASSIS_CONTROL: 'Chassis Control command',
    RESTART_CAUSE_RESET_BUTTON: 'reset via pushbutton',
    RESTART_CAUSE_POWER_BUTTON: 'power-up via power pushbutton',
    RESTART_CAUSE_WATCHDOG: 'watchdog expiration',
    RESTART_CAUSE_OEM: 'OEM',
    RESTART_CAUSE_POWER_RESTORE_ALWAYS_ON:
        'automatic power-up on AC being applied (always restore policy)',
    RESTART_CAUSE_POWER_RESTORE_PREVIOUS:
        'automatic power-up on AC being applied (restore previous policy)',
    RESTART_CAUSE_PEF_RESET: 'reset via PEF',
    RESTART_CAUSE_PEF_POWER_CYCLE: 'power-cycle via PEF',
    RESTART_CAUSE_SOFT_RESET: 'soft reset, e.g. Ctrl-Alt-Del',
    RESTART_CAUSE_RTC_WAKEUP: 'power-up via RTC wakeup',
}


def restart_cause_to_string(cause: int) -> str:
    """Return the description of a system restart cause.

    Args:
        cause: The restart cause, one of the ``RESTART_CAUSE_*`` constants.

    Returns:
        The description, 'reserved (0x..)' for an unknown cause.
    """
    return RESTART_CAUSE_NAMES.get(cause, f'reserved (0x{cause:x})')


class BootDevice(str, Enum):
    """The boot devices of the boot flags, the values are their names."""

    NO_OVERRIDE = "no override",
    PXE = "pxe",
    DEFAULT_HDD = "default hard drive",
    DEFAULT_HDD_SAFE = "default hard drive safe mode",
    DIAGNOSTIC = "diagnostic partition",
    CD = "cd",
    BIOS = "bios setup",
    REMOTE_USB = "remote removable media",
    PRIMARY_REMOTE = "primary remote media",
    REMOTE_CD = "remote cd",
    REMOTE_HDD = "remote hard drive",
    PRIMARY_USB = "primary removable media (usb)"


CONVERT_RAW_TO_BOOT_DEVICE = {
    0:  BootDevice.NO_OVERRIDE,
    1:  BootDevice.PXE,
    2:  BootDevice.DEFAULT_HDD,
    3:  BootDevice.DEFAULT_HDD_SAFE,
    4:  BootDevice.DIAGNOSTIC,
    5:  BootDevice.CD,
    6:  BootDevice.BIOS,
    7:  BootDevice.REMOTE_USB,
    8:  BootDevice.REMOTE_CD,
    9:  BootDevice.PRIMARY_REMOTE,
    11: BootDevice.REMOTE_HDD,
    15: BootDevice.PRIMARY_USB
}

CONVERT_BOOT_DEVICE_TO_RAW = {
    BootDevice.NO_OVERRIDE:      0b0000,
    BootDevice.PXE:              0b0001,
    BootDevice.DEFAULT_HDD:      0b0010,
    BootDevice.DEFAULT_HDD_SAFE: 0b0011,
    BootDevice.DIAGNOSTIC:       0b0100,
    BootDevice.CD:               0b0101,
    BootDevice.BIOS:             0b0110,
    BootDevice.REMOTE_USB:       0b0111,
    BootDevice.PRIMARY_REMOTE:   0b1001,
    BootDevice.REMOTE_CD:        0b1000,
    BootDevice.REMOTE_HDD:       0b1011,
    BootDevice.PRIMARY_USB:      0b1111
}


def data_to_boot_mode(data: array) -> str:
    """Convert the boot flags response data to the boot mode string.

    Args:
        data: The parameter data of
            `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)`.

    Returns:
        ``'legacy'`` or ``'efi'``.
    """
    boot_mode_raw = (data[0] >> 5) & 1
    boot_mode = "legacy" if boot_mode_raw == 0 else "efi"
    return boot_mode


def data_to_boot_persistency(data: array) -> bool:
    """Convert the boot flags response data to the boot persistency.

    Args:
        data: The parameter data of
            `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)`.

    Returns:
        True if the boot options apply to all future boots, False if they
        apply to the next boot only.
    """
    boot_persistent_raw = (data[0] >> 6) & 1
    return boot_persistent_raw == 1


def data_to_boot_device(data: array) -> BootDevice:
    """Convert the boot flags response data to the boot device.

    Args:
        data: The parameter data of
            `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)`.

    Returns:
        The boot device.

    Raises:
        KeyError: The boot device code is reserved.
    """
    boot_device_raw = (data[1] >> 2) & 0b1111
    return CONVERT_RAW_TO_BOOT_DEVICE[boot_device_raw]


def boot_options_to_data(boot_device: BootDevice, boot_mode: str,
                         boot_persistency: bool) -> ByteBuffer:
    """Convert the boot device, mode and persistency to boot flags data.

    Args:
        boot_device: The boot device.
        boot_mode: ``'legacy'`` or ``'efi'``.
        boot_persistency: True if the boot options apply to all future
            boots, False if they apply to the next boot only.

    Returns:
        The parameter data of
        `SetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)`, the boot flags
        are marked valid.

    Raises:
        TypeError: ``boot_persistency`` is not a bool.
        ValueError: The boot mode or the boot device is unknown.
    """
    if not isinstance(boot_persistency, bool):
        raise TypeError(f"Wrong type for boot_persistency argument: {type(boot_persistency)}, expected bool.")

    # Construct the boot mode byte
    if boot_mode == "efi":
        boot_mode_raw = 0b100000
    elif boot_mode == "legacy":
        boot_mode_raw = 0
    else:
        raise ValueError(f"Unknown value for boot_mode argument: {boot_mode}. Possible values are : legacy, efi.")

    # Construct the boot persistency + boot flags valid bits
    if boot_persistency:
        boot_persistent_raw = 0b11000000
    else:
        boot_persistent_raw = 0b10000000

    # Construct the boot device byte
    device_raw = CONVERT_BOOT_DEVICE_TO_RAW.get(boot_device, None)
    if device_raw is None:
        raise ValueError(f"Unknown value for boot_device argument: {boot_device}")

    # Construct the final data bytearray
    data = ByteBuffer([boot_mode_raw | boot_persistent_raw, device_raw << 2, 0, 0, 0])
    return data


class Chassis(IpmiMixin):
    """Chassis commands, available on :class:`pyipmi.Ipmi`."""

    def get_chassis_status(self) -> ChassisStatus:
        """Get the status of the chassis and its power.

        Returns:
            The chassis status.
        """
        return ChassisStatus(self.send_message_by_name('GetChassisStatus'))

    def chassis_control(self, option: int) -> None:
        """Control the chassis power.

        Args:
            option: One of the ``CONTROL_*`` constants: power down, power up,
                power cycle, hard reset, diagnostic interrupt or soft
                shutdown.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        req = create_request_by_name('ChassisControl')
        req.control.option = option
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def chassis_control_power_down(self) -> None:
        """Power down the chassis."""
        self.chassis_control(CONTROL_POWER_DOWN)

    def chassis_control_power_up(self) -> None:
        """Power up the chassis."""
        self.chassis_control(CONTROL_POWER_UP)

    def chassis_control_power_cycle(self) -> None:
        """Power cycle the chassis."""
        self.chassis_control(CONTROL_POWER_CYCLE)

    def chassis_control_hard_reset(self) -> None:
        """Hard reset the system."""
        self.chassis_control(CONTROL_HARD_RESET)

    def chassis_control_diagnostic_interrupt(self) -> None:
        """Issue a diagnostic interrupt (NMI) to the system."""
        self.chassis_control(CONTROL_DIAGNOSTIC_INTERRUPT)

    def chassis_control_soft_shutdown(self) -> None:
        """Initiate a soft shutdown of the operating system."""
        self.chassis_control(CONTROL_SOFT_SHUTDOWN)

    def chassis_reset(self) -> None:
        """Reset the chassis with the Chassis Reset command.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        self.send_message_by_name('ChassisReset')

    def chassis_identify(self, interval: int | None = None,
                         force_on: bool = False) -> None:
        """Turn on the chassis identification, e.g. a blinking LED.

        Args:
            interval: The time in seconds the identification stays on,
                0 turns it off. The BMC uses its default of 15 seconds if
                it is None.
            force_on: Turn on the identification until it is turned off
                with the interval 0. The interval is ignored then.

        Raises:
            ValueError: The interval is not in the range 0 - 255.
            CompletionCodeError: The BMC rejected the request.
        """
        if interval is not None and not 0 <= interval <= 255:
            raise ValueError(f'identify interval {interval} is not in the '
                             'range 0 - 255')
        if force_on:
            # the force byte is only allowed after the interval byte
            if interval is None:
                interval = 0
            self.send_message_by_name('ChassisIdentify', interval=interval,
                                      force_on=1)
        else:
            self.send_message_by_name('ChassisIdentify', interval=interval)

    def get_chassis_capabilities(self) -> ChassisCapabilities:
        """Get the capabilities of the chassis.

        Returns:
            The capabilities and the addresses of the chassis devices.
        """
        return ChassisCapabilities(
            self.send_message_by_name('GetChassisCapabilities'))

    def set_chassis_capabilities(self,
                                 capabilities: ChassisCapabilities) -> None:
        """Set the capabilities of the chassis.

        Only the intrusion sensor and the front panel lockout capabilities
        and the addresses can be set. Read the capabilities with
        :meth:`get_chassis_capabilities`, change them and set them.

        Args:
            capabilities: The capabilities and the addresses of the chassis
                devices. The bridge address is only set if it is not None.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        req = create_request_by_name('SetChassisCapabilities')
        req.capabilities_flags.intrusion_sensor = \
            int(bool(capabilities.intrusion_sensor))
        req.capabilities_flags.frontpanel_lockout = \
            int(bool(capabilities.frontpanel_lockout))
        req.fru_info_device_address = capabilities.fru_info_device_address
        req.sdr_device_address = capabilities.sdr_device_address
        req.sel_device_address = capabilities.sel_device_address
        req.system_management_device_address = \
            capabilities.system_management_device_address
        req.bridge_device_address = capabilities.bridge_device_address
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_power_restore_policy(self, policy: int) -> list[int]:
        """Set the power restore policy after AC/mains power returns.

        Args:
            policy: The policy, one of the ``POWER_RESTORE_POLICY_*``
                constants. ``POWER_RESTORE_POLICY_NO_CHANGE`` only returns
                the supported policies, see
                :meth:`get_supported_power_restore_policies`.

        Returns:
            The policies the chassis supports.

        Raises:
            ValueError: The policy is unknown.
            CompletionCodeError: The BMC rejected the request.
        """
        if not 0 <= policy <= POWER_RESTORE_POLICY_NO_CHANGE:
            raise ValueError(f'unknown power restore policy {policy}')
        req = create_request_by_name('SetPowerRestorePolicy')
        req.power_restore_policy.policy = policy
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        support = rsp.power_restore_policy_support
        supported = []
        if support.always_off:
            supported.append(POWER_RESTORE_POLICY_ALWAYS_OFF)
        if support.restore_previous:
            supported.append(POWER_RESTORE_POLICY_RESTORE_PREVIOUS)
        if support.always_on:
            supported.append(POWER_RESTORE_POLICY_ALWAYS_ON)
        return supported

    def get_supported_power_restore_policies(self) -> list[int]:
        """Get the power restore policies the chassis supports.

        The current policy is not changed, it is reported by
        :meth:`get_chassis_status`.

        Returns:
            The supported ``POWER_RESTORE_POLICY_*`` constants.
        """
        return self.set_power_restore_policy(POWER_RESTORE_POLICY_NO_CHANGE)

    def get_system_restart_cause(self) -> SystemRestartCause:
        """Get the cause of the last system restart.

        Returns:
            The restart cause and the channel of the restart command.
        """
        return SystemRestartCause(
            self.send_message_by_name('GetSystemRestartCause'))

    def get_poh_counter(self) -> PohCounter:
        """Get the power-on hours (POH) counter.

        Returns:
            The counter and the minutes per count.
        """
        return PohCounter(self.send_message_by_name('GetPohCounter'))

    def set_front_panel_button_enables(self, power_off: bool = True,
                                       reset: bool = True,
                                       diagnostic_interrupt: bool = True,
                                       standby: bool = True) -> None:
        """Enable or disable the front panel buttons.

        Which buttons can be disabled is reported in
        ``front_panel_button_capabilities`` of :meth:`get_chassis_status`.

        Args:
            power_off: Enable the power off function of the power button.
            reset: Enable the reset button.
            diagnostic_interrupt: Enable the diagnostic interrupt button.
            standby: Enable the standby (sleep) button.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        req = create_request_by_name('SetFrontPanelButtonEnables')
        req.disable.power_off_button = int(not power_off)
        req.disable.reset_button = int(not reset)
        req.disable.diagnostic_interrupt_button = \
            int(not diagnostic_interrupt)
        req.disable.standby_button = int(not standby)
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_power_cycle_interval(self, interval: int) -> None:
        """Set the time the power stays off during a power cycle.

        Args:
            interval: The interval in seconds, 0 - 255.

        Raises:
            ValueError: The interval is not in the range 0 - 255.
            CompletionCodeError: The BMC rejected the request.
        """
        if not 0 <= interval <= 255:
            raise ValueError(f'power cycle interval {interval} is not in the '
                             'range 0 - 255')
        self.send_message_by_name('SetPowerCycleInterval', interval=interval)

    def get_system_boot_options(self, parameter_selector: int = 0,
                                set_selector: int = 0,
                                block_selector: int = 0) -> array:
        """Get a boot option parameter.

        Args:
            parameter_selector: The parameter, one of the
                ``BOOT_PARAMETER_*`` constants.
            set_selector: The set selector of the parameter.
            block_selector: The block selector of the parameter.

        Returns:
            The parameter data.

        Raises:
            CompletionCodeError: The BMC rejected the request, e.g. for an
                unsupported parameter.
        """
        req = create_request_by_name('GetSystemBootOptions')
        req.parameter_selector.boot_option_parameter_selector = parameter_selector
        req.set_selector = set_selector
        req.block_selector = block_selector
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)
        return rsp.data

    def set_system_boot_options(self, parameter_selector: int, data: ByteBuffer,
                                mark_parameter_invalid: int = 0) -> None:
        """Set a boot option parameter.

        Args:
            parameter_selector: The parameter, one of the
                ``BOOT_PARAMETER_*`` constants.
            data: The parameter data.
            mark_parameter_invalid: 1 to mark the parameter invalid.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        req = create_request_by_name('SetSystemBootOptions')
        req.parameter_selector.parameter_validity = mark_parameter_invalid
        req.parameter_selector.boot_option_parameter_selector = parameter_selector
        req.data = data
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def get_boot_mode(self) -> str:
        """Return the boot mode of the boot flags.

        Returns:
            ``'legacy'`` or ``'efi'``.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_mode(rsp)

    def get_boot_persistency(self) -> bool:
        """Return whether the boot configuration applies to all boots.

        Returns:
            True if the boot configuration is applied to every future boot,
            False if it is only applied to the next boot.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_persistency(rsp)

    def get_boot_device(self) -> BootDevice:
        """Return the boot device of the boot flags.

        Returns:
            The boot device.

        Raises:
            KeyError: The boot device code is reserved.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_device(rsp)

    def set_boot_options(self, boot_device: BootDevice, boot_mode: str,
                         boot_persistency: bool) -> None:
        """Set the boot flags: the boot device, mode and persistency.

        Args:
            boot_device: The boot device.
            boot_mode: ``'legacy'`` or ``'efi'``.
            boot_persistency: True if the boot options apply to all future
                boots, False if they apply to the next boot only.

        Raises:
            TypeError: ``boot_persistency`` is not a bool.
            ValueError: The boot mode or the boot device is unknown.
        """
        data = boot_options_to_data(boot_device, boot_mode, boot_persistency)
        self.set_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS, data)


class ChassisStatus(State):
    """The status of the chassis and its power."""

    #: The system power is on.
    power_on: bool | None = None
    #: A power overload was detected.
    overload: bool | None = None
    #: The power interlock is active.
    interlock: bool | None = None
    #: A power fault was detected.
    fault: bool | None = None
    #: A fault of the power control was detected.
    control_fault: bool | None = None
    #: The power restore policy after an AC power loss: 0 stays off, 1
    #: restores the previous state, 2 powers up, 3 is unknown.
    restore_policy: int | None = None
    #: The chassis identify state is reported in ``chassis_id_state``.
    id_cmd_state_info_support: bool | None = None
    #: The chassis identify state: 0 off, 1 temporary on, 2 indefinite on.
    chassis_id_state: int | None = None
    #: The front panel button capabilities and disable/enable status, None
    #: if the BMC does not report them.
    front_panel_button_capabilities: int | None = None
    #: The causes of the last power event: ``'ac_failed'``,
    #: ``'overload'``, ``'interlock'``, ``'fault'`` and
    #: ``'power_on_via_ipmi'``.
    last_event: list[str] = []
    #: The active chassis states: ``'intrusion'``,
    #: ``'front_panel_lockout'``, ``'drive_fault'`` and ``'cooling_fault'``.
    chassis_state: list[str] = []

    def _from_response(self, rsp: Message) -> None:
        # don't append to the lists shared by all instances
        self.last_event = []
        self.chassis_state = []
        self.power_on = bool(rsp.current_power_state.power_on)
        self.overload = bool(rsp.current_power_state.power_overload)
        self.interlock = bool(rsp.current_power_state.interlock)
        self.fault = bool(rsp.current_power_state.power_fault)
        self.control_fault = bool(rsp.current_power_state.power_control_fault)
        self.restore_policy = rsp.current_power_state.power_restore_policy
        self.id_cmd_state_info_support = \
            bool(rsp.misc_chassis_state.id_cmd_state_info_support)
        self.chassis_id_state = rsp.misc_chassis_state.chassis_id_state
        if rsp.front_panel_button_capabilities is not None:
            self.front_panel_button_capabilities = \
                    rsp.front_panel_button_capabilities

        if rsp.last_power_event.ac_failed:
            self.last_event.append('ac_failed')
        if rsp.last_power_event.power_overload:
            self.last_event.append('overload')
        if rsp.last_power_event.power_interlock:
            self.last_event.append('interlock')
        if rsp.last_power_event.power_fault:
            self.last_event.append('fault')
        if rsp.last_power_event.power_is_on_via_ipmi_command:
            self.last_event.append('power_on_via_ipmi')

        if rsp.misc_chassis_state.chassis_intrusion_active:
            self.chassis_state.append('intrusion')
        if rsp.misc_chassis_state.front_panel_lockout_active:
            self.chassis_state.append('front_panel_lockout')
        if rsp.misc_chassis_state.drive_fault:
            self.chassis_state.append('drive_fault')
        if rsp.misc_chassis_state.cooling_fault_detected:
            self.chassis_state.append('cooling_fault')


class ChassisCapabilities(State):
    """The capabilities of the chassis and the addresses of its devices.

    The addresses are 8-bit IPMB slave addresses.
    """

    #: The chassis has an intrusion (physical security) sensor.
    intrusion_sensor: bool | None = None
    #: The chassis provides a front panel lockout.
    frontpanel_lockout: bool | None = None
    #: The chassis provides a diagnostic interrupt (FP NMI).
    diagnostic_interrupt: bool | None = None
    #: The chassis provides a power interlock.
    power_interlock: bool | None = None
    #: The address of the FRU info device.
    fru_info_device_address: int | None = None
    #: The address of the SDR device.
    sdr_device_address: int | None = None
    #: The address of the SEL device.
    sel_device_address: int | None = None
    #: The address of the system management device.
    system_management_device_address: int | None = None
    #: The address of the chassis bridge device, None if the BMC does not
    #: report it.
    bridge_device_address: int | None = None

    def _from_response(self, rsp: Message) -> None:
        flags = rsp.capabilities_flags
        self.intrusion_sensor = bool(flags.intrusion_sensor)
        self.frontpanel_lockout = bool(flags.frontpanel_lockout)
        self.diagnostic_interrupt = bool(flags.diagnostic_interrupt)
        self.power_interlock = bool(flags.power_interlock)
        self.fru_info_device_address = rsp.fru_info_device_address
        self.sdr_device_address = rsp.sdr_device_address
        self.sel_device_address = rsp.sel_device_address
        self.system_management_device_address = \
            rsp.system_management_device_address
        self.bridge_device_address = rsp.bridge_device_address


class SystemRestartCause(State):
    """The cause of the last system restart."""

    #: The restart cause, one of the ``RESTART_CAUSE_*`` constants.
    cause: int | None = None
    #: The channel the command that caused the restart was received on, 0
    #: if unknown, None if the BMC does not report it.
    channel_number: int | None = None

    def _from_response(self, rsp: Message) -> None:
        self.cause = rsp.restart_cause.cause
        self.channel_number = rsp.channel_number

    def __str__(self) -> str:
        """Return the description of the cause."""
        assert self.cause is not None
        return restart_cause_to_string(self.cause)


class PohCounter(State):
    """The power-on hours (POH) counter."""

    #: The minutes per count of the counter.
    minutes_per_count: int | None = None
    #: The counter reading.
    counter: int | None = None

    def _from_response(self, rsp: Message) -> None:
        self.minutes_per_count = rsp.minutes_per_count
        self.counter = rsp.counter_reading

    @property
    def minutes(self) -> int:
        """The power-on time in minutes."""
        assert self.minutes_per_count is not None
        assert self.counter is not None
        return self.minutes_per_count * self.counter
