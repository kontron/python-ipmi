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

from __future__ import absolute_import
from enum import Enum


from .msgs import create_request_by_name
from .utils import check_completion_code, ByteBuffer
from .state import State

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


class BootDevice(str, Enum):
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
    8:  BootDevice.PRIMARY_REMOTE,
    9:  BootDevice.REMOTE_CD,
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


def data_to_boot_mode(data):
    """
    Convert a `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)` response data
    into the string representation of the encoded boot mode.
    """
    boot_mode_raw = (data[0] >> 5) & 1
    boot_mode = "legacy" if boot_mode_raw == 0 else "efi"
    return boot_mode


def data_to_boot_persistency(data):
    """
    Convert a `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)` response data
    into the boolean representation of the encoded boot persistency.
    """
    boot_persistent_raw = (data[0] >> 6) & 1
    return boot_persistent_raw == 1


def data_to_boot_device(data):
    """
    Convert a `GetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)` response data
    into the string representation of the encoded boot device.
    """
    boot_device_raw = (data[1] >> 2) & 0b1111
    return CONVERT_RAW_TO_BOOT_DEVICE[boot_device_raw]


def boot_options_to_data(boot_device, boot_mode, boot_persistency):
    """
    Convert a boot mode (string), boot device (string) and boot persistency (bool)
    into a `SetSystemBootOptions(BOOT_PARAMETER_BOOT_FLAGS)` request data.
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


class Chassis(object):
    def get_chassis_status(self):
        return ChassisStatus(self.send_message_with_name('GetChassisStatus'))

    def chassis_control(self, option):
        req = create_request_by_name('ChassisControl')
        req.control.option = option
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def chassis_control_power_down(self):
        self.chassis_control(CONTROL_POWER_DOWN)

    def chassis_control_power_up(self):
        self.chassis_control(CONTROL_POWER_UP)

    def chassis_control_power_cycle(self):
        self.chassis_control(CONTROL_POWER_CYCLE)

    def chassis_control_hard_reset(self):
        self.chassis_control(CONTROL_HARD_RESET)

    def chassis_control_diagnostic_interrupt(self):
        self.chassis_control(CONTROL_DIAGNOSTIC_INTERRUPT)

    def chassis_control_soft_shutdown(self):
        self.chassis_control(CONTROL_SOFT_SHUTDOWN)

    def get_system_boot_options(self, parameter_selector=0,
                                set_selector=0, block_selector=0):
        req = create_request_by_name('GetSystemBootOptions')
        req.parameter_selector.boot_option_parameter_selector = parameter_selector
        req.set_selector = set_selector
        req.block_selector = block_selector
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.data

    def set_system_boot_options(self, parameter_selector, data,
                                mark_parameter_invalid=0):
        req = create_request_by_name('SetSystemBootOptions')
        req.parameter_selector.parameter_validity = mark_parameter_invalid
        req.parameter_selector.boot_option_parameter_selector = parameter_selector
        req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_boot_mode(self):
        """
        Return a string corresponding to the device boot mode.

        Possible values are: legacy, efi.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_mode(rsp)

    def get_boot_persistency(self):
        """
        Return True if the boot configuration is to be applied to every future
        boot, Fale if it only will applied to the next boot.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_persistency(rsp)

    def get_boot_device(self):
        """
        Return a string corresponding to the target boot device.

        Possible values are listed in the `BootDevice` class.
        """
        rsp = self.get_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS)
        return data_to_boot_device(rsp)

    def set_boot_options(self, boot_device, boot_mode, boot_persistency):
        data = boot_options_to_data(boot_device, boot_mode, boot_persistency)
        self.set_system_boot_options(BOOT_PARAMETER_BOOT_FLAGS, data)


class ChassisStatus(State):
    power_on = None
    overload = None
    interlock = None
    fault = None
    control_fault = None
    restore_policy = None
    id_cmd_state_info_support = None
    chassis_id_state = None
    front_panel_button_capabilities = None
    last_event = []
    chassis_state = []

    def _from_response(self, rsp):
        self.power_on = bool(rsp.current_power_state.power_on)
        self.overload = bool(rsp.current_power_state.power_overload)
        self.interlock = bool(rsp.current_power_state.interlock)
        self.fault = bool(rsp.current_power_state.power_fault)
        self.control_fault = bool(rsp.current_power_state.power_control_fault)
        self.restore_policy = rsp.current_power_state.power_restore_policy
        self.id_cmd_state_info_support = \
                bool(rsp.misc_chassis_state.id_cmd_state_info_support)  # noqa:E127
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
