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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from functools import partial

from pyipmi.msgs import create_request_by_name
from pyipmi.errors import DecodingError, CompletionCodeError
from utils import check_completion_code

from pyipmi.msgs.chassis import \
        CONTROL_POWER_DOWN, CONTROL_POWER_UP, CONTROL_POWER_CYCLE, \
        CONTROL_HARD_RESET, CONTROL_DIAGNOSTIC_INTERRUPT, \
        CONTROL_SOFT_SHUTDOWN

class Chassis:
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
