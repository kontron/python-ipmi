#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import chassis
from utils import check_completion_code

class Helper:
    def chassis_control_power_down(self, fn):
        self._chassis_control(fn, chassis.CONTROL_POWER_DOWN)

    def chassis_control_power_up(self, fn):
        self._chassis_control(fn, chassis.CONTROL_POWER_UP)

    def chassis_control_power_cycle(self, fn):
        self._chassis_control(fn, chassis.CONTROL_POWER_CYCLE)

    def chassis_control_hard_reset(self, fn):
        self._chassis_control(fn, chassis.CONTROL_HARD_RESET)

    def chassis_control_diagnostic_interrupt(self, fn):
        self._chassis_control(fn, chassis.CONTROL_DIAGNOSTIC_INTERRUPT)

    def chassis_control_soft_shutdown(self, fn):
        self._chassis_control(fn, chassis.CONTROL_SOFT_SHUTDOWN)

    def _chassis_control(self, fn, option):
        m = chassis.ChassisControl()
        m.req.control.option = option
        fn(m)
        check_completion_code(m.rsp.completion_code)

