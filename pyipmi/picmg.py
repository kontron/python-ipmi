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

import array
from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import picmg
from pyipmi.utils import check_completion_code

from pyipmi.msgs.picmg import \
        FRU_CONTROL_COLD_RESET, FRU_CONTROL_WARM_RESET, \
        FRU_CONTROL_GRACEFUL_REBOOT, FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT, \
        FRU_ACTIVATION_FRU_ACTIVATE, FRU_ACTIVATION_FRU_DEACTIVATE

class Picmg:
    def get_picmg_properties(self):
        req = create_request_by_name('GetPicmgProperties')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp

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

    def get_fan_speed_properties(self, fru_id):
        req = create_request_by_name('GetFanSpeedProperties')
        req.fru_id = fru_id
        rsp = self.send_message(req)
        return FanSpeedProperties(rsp)

    def set_fan_level(self, fru_id, fan_level):
        req = create_request_by_name('SetFanLevel')
        req.fru_id = fru_id
        req.fan_level = fan_level
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_fan_level(self, fru_id):
        req = create_request_by_name('GetFanLevel')
        req.fru_id = fru_id
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        local_control_fan_level = None
        if rsp.data:
            local_control_fan_level = rsp.data[0]
        return (rsp.override_fan_level, local_control_fan_level)

    def get_led_state(self, fru_id, led_id):
        req = create_request_by_name('GetFruLedState')
        req.fru_id = fru_id
        req.led_id = led_id
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return LedState(rsp)

    def set_led_state(self, led):
        req = create_request_by_name('SetFruLedState')
        led.to_request(req)
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

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

    def set_port_state(self, link_descr, state):
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

    def get_port_state(self, channel_number, channel_interface):
        req = create_request_by_name('GetPortState')
        req.channel.number = channel_number
        req.channel.interface = channel_interface
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

        if len(rsp.data) > 4:
            link = LinkDescriptor()
            link.channel = rsp.data[0] & 0x3F
            link.interface = rsp.data[0]>>6 & 0x3
            link.link_flags = rsp.data[1]&0xf
            link.type = rsp.data[1]>>4&0xf
            link.sig_class = rsp.data[2] &0xf
            link.extension = rsp.data[2]>>4&0xf
            link.grouping_id = rsp.data[3]
            state = rsp.data[4]

        return (link, state)

    def get_pm_global_status(self):
        req = create_request_by_name('GetPowerChannelStatus')
        req.starting_power_channel_number = 1
        req.power_channel_count = 1
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return GlobalStatus(rsp)

    def get_power_channel_status(self, starting_number):
        req = create_request_by_name('GetPowerChannelStatus')
        req.starting_power_channel_number = starting_number
        req.power_channel_count = 1
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return PowerChannelStatus(rsp.data[0])

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


class LinkDescriptor:
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

    PROPERTIES = [
            # (propery, description)
            ('channel', ''),
            ('interface', ''),
            ('link_flags', ''),
            ('type', ''),
            ('sig_class', ''),
            ('extension', ''),
            ('grouping_id', ''),
    ]

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)

    INTERFACE_DESCR_STRING = [
        # Interface, 'STRING'
        ( INTERFACE_BASE, 'Base' ),
        ( INTERFACE_FABRIC, 'Fabric' ),
        ( INTERFACE_UPDATE_CHANNEL, 'Update Channel' ),
    ]

    def get_interface_string(self, interf):
        for d in self.INTERFACE_DESCR_STRING:
            if d[0] == interf:
                return d[1]
        return 'unknown'

    LINK_TYPE_DESCR_STRING = [
        # Type, Extension, class, 'STRING'
        ( TYPE_BASE,
            TYPE_EXT_BASE0,
            SIGNALING_CLASS_BASIC,
            '10/100/1000 BASE-T'),
        ( TYPE_BASE,
            TYPE_EXT_BASE1,
            SIGNALING_CLASS_BASIC,
            '10/100 BASE-T ShMC Cross-connect'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX1000_BX,
            SIGNALING_CLASS_BASIC,
            'Fixed 1000BASE-BX'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX10G_BX4,
            SIGNALING_CLASS_BASIC,
            'Fixed 10GBASE-BX4 (XAUI)'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FCPI,
            SIGNALING_CLASS_BASIC,
            'FC-PI'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX1000_KX,
            SIGNALING_CLASS_BASIC,
            'Fixed 1000BASE-KX'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX10G_KX4,
            SIGNALING_CLASS_BASIC,
            'Fixed 10GBASE-KX4'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX10G_KR,
            SIGNALING_CLASS_10_3125_GBD,
            'Fixed 10GBASE-KR'),
        ( TYPE_ETHERNET_FABRIC,
            TYPE_EXT_ETHERNET_FIX40G_KR4,
            SIGNALING_CLASS_10_3125_GBD,
            'Fixed 40GBASE-KR4'),
    ]

    def get_link_type_string(self, type, ext, cls=0):
        for d in self.LINK_TYPE_DESCR_STRING:
            if d[0] == type and d[1] == ext and d[2] == cls:
                return d[3]
        return 'unknown'


class PowerLevel:
    def __init__(self, res=None):
        if res:
            self.from_response(res)

    def from_response(self, res):
        print res
        self.dynamic_power_configuration = res.properties.dynamic_power_configuration
        self.power_level = res.properties.power_level
        self.delay_to_stable = res.delay_to_stable_power
        self.power_mulitplier = res.power_multiplier
        self.power_levels = res.power_draw


class FanSpeedProperties:
    def __init__(self, res=None):
        if res:
            self.from_response(res)

    def from_response(self, res):
        self.minimum_speed_level = res.minimum_speed_level
        self.maximum_speed_level = res.maximum_speed_level
        self.normal_operation_level = res.normal_operation_level
        self.local_control_supported = res.properties.local_control_supported


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
    FUNCTION_LAMP_TEST = 4

    PROPERTIES = [
            # (propery, description)
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
        req.fru_id = self.fru_id
        req.led_id = self.led_id
        req.color = self.override_color

        if self.led_function == self.FUNCTION_ON:
            req.led_function = picmg.LED_FUNCTION_ON
            req.on_duration = 0
        elif self.led_function == self.FUNCTION_OFF:
            req.led_function = picmg.LED_FUNCTION_OFF
            req.on_duration = 0
        elif self.led_function == self.FUNCTION_BLINKING:
            if self.override_off_duration not in \
                    picmg.picmg.LED_FUNCTION_BLINKING_RANGE:
                raise EncodingError()
            req.led_function = self.override_off_duration
            req.on_duration = self.override_on_duration
        elif self.led_function == self.FUNCTION_LAMP_TEST:
            req.led_function = picmg.LED_FUNCTION_LAMP_TEST
            req.on_duration = self.lamp_test_duration
        else:
            raise AssertionError()

        return req


class GlobalStatus:
    PROPERTIES = [
            # (propery, description)
            ('role', ''),
            ('management_power_good', ''),
            ('payload_power_good', ''),
            ('unidentified_fault', ''),
    ]

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)

    def from_response(self, res):
        self.role = res.global_status.role
        self.management_power_good =\
                bool(res.global_status.management_power_good)
        self.payload_power_good =\
                bool(res.global_status.payload_power_good)
        self.unidentified_fault =\
                bool(res.global_status.unidentified_fault)


class PowerChannelStatus:
    PROPERTIES = [
            # (propery, description)
            ('present', ''),
            ('management_power', ''),
            ('management_power_overcurrent', ''),
            ('enable', ''),
            ('payload_power', ''),
            ('payload_power_overcurrent', ''),
            ('pwr_on', ''),
    ]

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)

    def from_response(self, data):
        self.present = (data >> 0) & 1
        self.management_power = (data >> 1) & 1
        self.management_power_overcurrent = (data >> 2) & 1
        self.enable = (data >> 3) & 1
        self.payload_power = (data >> 4) & 1
        self.payload_power_overcurrent = (data >> 5) & 1
        self.pwr_on = (data >> 6) & 1
