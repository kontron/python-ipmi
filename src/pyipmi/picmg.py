#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from errors import DecodingError, CompletionCodeError
from msgs import picmg, check_completion_code

class Helper:
    def fru_control_cold_reset(self, fn, fru_id=0):
        self._fru_control(fn, fru_id, picmg.FRU_CONTROL_COLD_RESET)

    def fru_control_warm_reset(self, fn, fru_id=0):
        self._fru_control(fn, fru_id, picmg.FRU_CONTROL_WARM_RESET)

    def fru_control_graceful_reboot(self, fn, fru_id=0):
        self._fru_control(fn, fru_id, picmg.FRU_CONTROL_GRACEFUL_REBOOT)

    def fru_control_diagnostic_interrupt(self, fn, fru_id=0):
        self._fru_control(fn, fru_id,
                picmg.FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT)

    def _fru_control(self, fn, fru_id, option):
        m = picmg.FruControl()
        m.req.fru_id = fru_id
        m.req.option = option
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def get_led_state(self, fn, fru_id, led_id):
        m = picmg.GetFruLedState()
        m.req.fru_id = fru_id
        m.req.led_id = led_id
        fn(m)
        check_completion_code(m.rsp.completion_code)
        return LedState(m.rsp)

    def set_fru_activation_lock(self, fn, fru_id):
        m = picmg.SetFruActivationPolicy()
        m.req.fru_id = fru_id
        m.req.mask.activation_locked = 1
        m.req.set.activation_locked = 1
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def clear_fru_activation_lock(self, fn, fru_id):
        m = picmg.SetFruActivationPolicy()
        m.req.fru_id = fru_id
        m.req.mask.activation_locked = 1
        m.req.set.activation_locked = 0
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def set_fru_deactivation_lock(self, fn, fru_id):
        m = picmg.SetFruActivationPolicy()
        m.req.fru_id = fru_id
        m.req.mask.deactivation_locked = 1
        m.req.set.deactivation_locked = 1
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def clear_fru_deactivation_lock(self, fn, fru_id):
        m = picmg.SetFruActivationPolicy()
        m.req.fru_id = fru_id
        m.req.mask.deactivation_locked = 1
        m.req.set.deactivation_locked = 0
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def set_port_state(self, fn, link_info):
        m = picmg.SetPortState()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def set_signaling_class(self, fn, interface, channel, signaling_class):
        m = picmg.SetSignalingClass()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def get_signaling_class(self, fn, interface, channel):
        m = picmg.GetSignalingClass()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        return None

class LedState:
    COLOR_BLUE = picmg.LED_COLOR_BLUE
    COLOR_RED = picmg.LED_COLOR_RED
    COLOR_GREEN = picmg.LED_COLOR_GREEN
    COLOR_AMBER = picmg.LED_COLOR_AMBER
    COLOR_ORANGE = picmg.LED_COLOR_ORANGE
    COLOR_WHITE = picmg.LED_COLOR_WHITE

    FUNCTION_OFF = 1
    FUNCTION_BLINKING = 2
    FUNCTION_ON = 3

    PROPERTIES = [
            # (propery, description)
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

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)

    def __str__(self):
        s = '[flags '
        s += self.local_state_available and ' LOCAL_STATE' or ''
        s += self.override_enabled and ' OVR_EN' or ''
        s += self.lamp_test_enabled and ' LAMP_TEST_EN' or ''
        if not self.local_state_available and not self.override_enabled \
                and not self.lamp_test_enabled:
            s += ' NONE'
        if self.local_state_available:
            s += ' local_function %s local_color %s' % (
                    self.local_function, self.local_color)
        if self.override_enabled:
            s += ' override_function %s override_color %s' % (
                    self.override_function, self.override_color)
        s += ']'
        return s

    def from_response(self, res):
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
                self.override_off_duration = res.local_function * 10
            else:
                raise DecodingError()

            self.override_off_duration = res.override_on_duration * 10
            self.override_color = res.override_color

        if self.lamp_test_enabled:
            self.lamp_test_duration = res.lamp_test_duration * 100

    def to_request(self, req):
        raise NotImplementedError()

