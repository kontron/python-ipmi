#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import array
from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import picmg
from pyipmi.utils import check_completion_code

from pyipmi.msgs.picmg import \
        CHANNEL_SIGNALING_CLASS_BASIC, CHANNEL_SIGNALING_CLASS_10_3125GBD, \
        FRU_CONTROL_COLD_RESET, FRU_CONTROL_WARM_RESET, \
        FRU_CONTROL_GRACEFUL_REBOOT, FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT, \
        FRU_ACTIVATION_FRU_ACTIVATE, FRU_ACTIVATION_FRU_DEACTIVATE

class Picmg:
    def fru_control(self, fru_id, option):
        req = create_request_by_name('FruControl')
        req.fru_id = fru_id
        req.option = option
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def fru_control_cold_reset(self, fru_id=0):
        self.fru_control(fru_id, FRU_CONTROL_COLD_RESET)

    def fru_control_warm_reset(self, fru_id=0):
        self.fru_control(fru_id, FRU_CONTROL_WARM_RESET)

    def fru_control_graceful_reboot(self, fru_id=0):
        self.fru_control(fru_id, FRU_CONTROL_GRACEFUL_REBOOT)

    def fru_control_diagnostic_interrupt(self, fru_id=0):
        self.fru_control(fru_id, FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT)

    def get_power_level(self, fru_id, power_type):
        req = create_request_by_name('GetPowerLevel')
        req.fru_id = fru_id
        req.power_type = power_type
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return PowerLevel(rsp)

    def get_led_state(self, fru_id, led_id):
        req = create_request_by_name('GetFruLedState')
        req.fru_id = fru_id
        req.led_id = led_id
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return LedState(rsp)

    def set_fru_activation(self, fru_id):
        req = create_request_by_name('SetFruActivation')
        req.fru_id = fru_id
        req.control = FRU_ACTIVATION_FRU_ACTIVATE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_fru_deactivation(self, fru_id):
        req = create_request_by_name('SetFruActivation')
        req.fru_id = fru_id
        req.control = FRU_ACTIVATION_FRU_DEACTIVATE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_fru_activation_lock(self, fru_id):
        req = create_request_by_name('SetFruActivationPolicy')
        req.fru_id = fru_id
        req.mask.activation_locked = 1
        req.set.activation_locked = 1
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def clear_fru_activation_lock(self, fru_id):
        req = create_request_by_name('SetFruActivationPolicy')
        req.fru_id = fru_id
        req.mask.activation_locked = 1
        req.set.activation_locked = 0
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_fru_deactivation_lock(self, fru_id):
        req = create_request_by_name('SetFruActivationPolicy')
        req.fru_id = fru_id
        req.mask.deactivation_locked = 1
        req.set.deactivation_locked = 1
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def clear_fru_deactivation_lock(self, fru_id):
        req = create_request_by_name('SetFruActivationPolicy')
        req.fru_id = fru_id
        req.mask.deactivation_locked = 1
        req.set.deactivation_locked = 0
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_port_state(self, link_info):
        req = create_request_by_name('SetPortState')
        req.link_info.channel = link_info.channel
        req.link_info.interface = link_info.interface
        req.link_info.port_0 = (link_info.link_flags >> 0) & 1
        req.link_info.port_1 = (link_info.link_flags >> 1) & 1
        req.link_info.port_2 = (link_info.link_flags >> 2) & 1
        req.link_info.port_3 = (link_info.link_flags >> 3) & 1
        req.link_info.type = link_info.type
        req.link_info.type_extension = link_info.extension
        req.link_info.grouping_id = link_info.grouping_id
        req.state = link_info.state
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_signaling_class(self, interface, channel, signaling_class):
        req = create_request_by_name('SetSignalingClass')
        req.channel_info.channel_number = channel
        req.channel_info.interface = interface
        req.channel_signaling.class_capability = signaling_class
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_signaling_class(self, interface, channel):
        req = create_request_by_name('GetSignalingClass')
        req.channel_info.channel_number = channel
        req.channel_info.interface = interface
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.channel_signaling.class_capability

class LinkInfo:
    # TODO dont duplicate exports, import them instead
    from pyipmi.msgs import picmg
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

    TYPE_EXT_ETHERNET_FIX1000BX = picmg.LINK_TYPE_EXT_ETHERNET_FIX1000BX
    TYPE_EXT_ETHERNET_FIX10GBX4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX10GBX4
    TYPE_EXT_ETHERNET_FCPI = picmg.LINK_TYPE_EXT_ETHERNET_FCPI
    TYPE_EXT_ETHERNET_FIX1000KX_10GKR = \
            picmg.LINK_TYPE_EXT_ETHERNET_FIX1000KX_10GKR
    TYPE_EXT_ETHERNET_FIX10GKX4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX10GKX4
    TYPE_EXT_ETHERNET_FIX40GKR4 = picmg.LINK_TYPE_EXT_ETHERNET_FIX40GKR4

    TYPE_EXT_OEM_LINK_TYPE_EXT_0 = picmg.LINK_TYPE_EXT_OEM_LINK_TYPE_EXT_0

    FLAGS_LANE0 = picmg.LINK_FLAGS_LANE0
    FLAGS_LANE0123 = picmg.LINK_FLAGS_LANE0123

    STATE_DISABLE = picmg.LINK_STATE_DISABLE
    STATE_ENABLE = picmg.LINK_STATE_ENABLE

    PROPERTIES = [
            # (propery, description)
            ('channel', ''),
            ('interface', ''),
            ('link_flags', ''),
            ('type', ''),
            ('extension', ''),
            ('grouping_id', ''),
            ('state', ''),
    ]

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)


class PowerLevel:
    def __init__(self, res=None):
        if res:
            self.from_response(res)

    def from_response(self, res):
        print res
        self.dynamic_power_configuration = res.dynamic_power_configuration
        self.power_level = res.power_level
        self.delay_to_stable = res.delay_to_stable_power
        self.power_mulitplier = res.power_multiplier
        self.power_levels = [ord(c) for c in res.data]


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

