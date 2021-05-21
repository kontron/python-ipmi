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

from .msgs import create_request_by_name
from .utils import check_completion_code
from .state import State

from .msgs.chassis import \
        CONTROL_POWER_DOWN, CONTROL_POWER_UP, CONTROL_POWER_CYCLE, \
        CONTROL_HARD_RESET, CONTROL_DIAGNOSTIC_INTERRUPT, \
        CONTROL_SOFT_SHUTDOWN, \
        BOOT_OPTION_LEGACY, BOOT_OPTION_EFI, BOOT_DEVICE_PXE, BOOT_DEVICE_DISK \


class Chassis(object):
    def get_chassis_status(self):
        return ChassisStatus(self.send_message_with_name('GetChassisStatus'))

    def chassis_control(self, option):
        req = create_request_by_name('ChassisControl')
        req.control.option = option
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_boot_options(self, persistent_boot_option, boot_device):
        req = create_request_by_name('SetSystemBootOptions')
        req.parameter_selector.boot_options = 5
        req.parameter_selector.parameter_valid = 0
        req.data_1.valid_flag = 1
        # intersted field
        req.data_1.persistent_boot_option = persistent_boot_option
        req.data_1.bios_boot_efi = 0
        req.data_3.ignore = 0
        req.data_4.ignore = 0
        req.data_5.ignore = 0
        req.data_2.lock_reset_buttons = 1
        req.data_2.screen_blank = 1
        # intersted field
        req.data_2.boot_device = boot_device
        req.data_2.lock_keyboard = 1
        req.data_2.cmos_clear = 1
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_boot_options(self):
        req = create_request_by_name('GetSystemBootOptions')
        req.parameter_selector.boot_options = 5
        req.set_selector.boot_options = 0
        req.block_selector.boot_options = 0
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return ChassisBootOptions(rsp)

    def chassis_control_power_down_krub(self):
        self.chassis_control(CONTROL_POWER_DOWN)

    def chassis_control_power_up_krub(self):
        self.chassis_control(CONTROL_POWER_UP)

    def chassis_control_power_cycle(self):
        self.chassis_control(CONTROL_POWER_CYCLE)

    def chassis_control_hard_reset(self):
        self.chassis_control(CONTROL_HARD_RESET)

    def chassis_control_diagnostic_interrupt(self):
        self.chassis_control(CONTROL_DIAGNOSTIC_INTERRUPT)

    def chassis_control_soft_shutdown(self):
        self.chassis_control(CONTROL_SOFT_SHUTDOWN)

class ChassisBootOptions(State):
  completion_code = None
  parameter_valid = None
  boot_options = None
  parameter_version = None
  # only interested in data_2
  data_2 = {
    'boot_device': None
  }
  def _from_response(self, rsp):
        self.parameter_version = bool(rsp.parameter_version.version)
        self.parameter_valid = rsp.parameter_validator.is_parameter_valid
        self.boot_options = rsp.parameter_validator.boot_options
        self.data_2['boot_device'] = rsp.data_2.boot_device

class ChassisStatus(State):
    power_on = None
    overload = None
    interlock = None
    fault = None
    control_fault = None
    restore_policy = None
    id_cmd_state_info_support=None
    chassis_id_state=None
    front_panel_button_capabilities=None
    last_event = []
    chassis_state = []

    def _from_response(self, rsp):
        self.power_on = bool(rsp.current_power_state.power_on)
        self.overload = bool(rsp.current_power_state.power_overload)
        self.interlock = bool(rsp.current_power_state.interlock)
        self.fault = bool(rsp.current_power_state.power_fault)
        self.control_fault = bool(rsp.current_power_state.power_control_fault)
        self.restore_policy = rsp.current_power_state.power_restore_policy
        self.id_cmd_state_info_support=bool(rsp.misc_chassis_state.id_cmd_state_info_support)
        self.chassis_id_state=rsp.misc_chassis_state.chassis_id_state
        if rsp.front_panel_button_capabilities is not None:
            self.front_panel_button_capabilities=rsp.front_panel_button_capabilities

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
