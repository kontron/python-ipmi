#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from errors import DecodingError, CompletionCodeError
from msgs import bmc, check_completion_code

class Helper:
    def get_device_id(self, fn):
        m = bmc.GetDeviceId()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        return DeviceId(m.rsp)

    def cold_reset(self, fn):
        m = bmc.ColdReset()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def warm_reset(self, fn):
        m = bmc.WarmReset()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def set_watchdog_timer(self, fn, config):
        m = bmc.SetWatchdogTimer()
        m.req.timer_use.timer_use = config.timer_use
        m.req.timer_use.dont_stop = config.dont_stop
        m.req.timer_use.dont_log = config.dont_log

        m.req.timer_actions.pre_timeout_interrupt = \
                config.pre_timeout_interrupt
        m.req.timer_actions.timeout_action = \
                config.timeout_action

        m.req.pre_timeout_interval = config.pre_timeout_interval
        m.req.timer_use_expiration_flags = config.timer_use_expiration_flags
        m.req.initial_countdown = config.initial_countdown
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def reset_watchdog_timer(self, fn):
        m = bmc.ResetWatchdogTimer()
        fn(m)
        check_completion_code(m.rsp.completion_code)


class Watchdog:
    TIMER_USE_OEM = 5
    TIMER_USE_SMS_OS = 4
    TIMER_USE_OS_LOAD = 3
    TIMER_USE_BIOS_POST = 2
    TIMER_USE_BIOS_FRB2 = 1

    TIMEOUT_ACTION_NO_ACTION = 0
    TIMEOUT_ACTION_HARD_RESET = 1
    TIMEOUT_ACTION_POWER_DOWN = 2
    TIMEOUT_ACTION_POWER_CYCLE = 3

    PROPERTIES = [
            # (propery, description)
            ('timer_use', ''),
            ('dont_stop', ''),
            ('dont_log', ''),
            ('pre_timeout_interrupt', ''),
            ('timeout_action', ''),
            ('pre_timeout_interval', ''),
            ('timer_use_expiration_flags', ''),
            ('initial_countdown', ''),
            ('present_countdown', ''),
    ]

    def __init__(self, res=None):
        for p in self.PROPERTIES:
            setattr(self, p[0], None)
        if res:
            self.from_response(res)


class DeviceId:
    def __init__(self, rsp=None):
        if rsp is not None:
            self.from_response(rsp)

    def __str__(self):
        s = 'Device ID: %d' % self.id
        s+= ' revision: %d' % self.revision
        s+= ' available: %d' % self.available
        s+= ' fw version: %d.%d' % (self.major_fw_revision, self.minor_fw_revision)
        s+= ' ipmi: %d.%d' % (self.major_ipmi_version, self.minor_ipmi_version)
        s+= ' manufacturer: %d' % self.manufacturer_id
        s+= ' product: %d' % self.product_id
        return s

    def supports_function(self, name):
        """Returns if a function is supported.

        `name` is one of 'SENSOR', 'SDR_REPOSITORY', 'SEL', 'FRU_INVENTORY',
        'IPMB_EVENT_RECEIVER', 'IPMB_EVENT_GENERATOR', 'BRIDGE', 'CHASSIS'.
        """

        return name.lower() in self.supported_functions

    def from_response(self, rsp):
        self.id = rsp.device_id
        self.revision = rsp.device_revision.device_revision
        self.provides_sdrs = bool(rsp.device_revision.provides_device_sdrs)
        self.available = bool(rsp.firmware_revision.device_available)
        self.major_fw_revision = rsp.firmware_revision.major
        self.minor_fw_revision = (
                ((rsp.firmware_revision.minor >> 4) & 0xf) * 10
                + (rsp.firmware_revision.minor & 0xf))
        self.major_ipmi_version = rsp.ipmi_version & 0xf
        self.minor_ipmi_version = (rsp.ipmi_version >> 4) & 0xf

        self.manufacturer_id = rsp.manufacturer_id
        self.product_id = rsp.product_id

        self.supported_functions = []
        if rsp.additional_support.sensor:
            self.supported_functions.append('sensor')
        if rsp.additional_support.sdr_repository:
            self.supported_functions.append('sdr_repository')
        if rsp.additional_support.sel:
            self.supported_functions.append('sel')
        if rsp.additional_support.fru_inventory:
            self.supported_functions.append('fru_inventory')
        if rsp.additional_support.ipmb_event_receiver:
            self.supported_functions.append('ipmb_event_receiver')
        if rsp.additional_support.ipmb_event_generator:
            self.supported_functions.append('ipmb_event_generator')
        if rsp.additional_support.bridge:
            self.supported_functions.append('bridge')
        if rsp.additional_support.chassis:
            self.supported_functions.append('chassis')

        if hasattr(rsp, 'auxiliary'):
            self.aux = list(rsp.auxiliary)
        else:
            self.aux = None
