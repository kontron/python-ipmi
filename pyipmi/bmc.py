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

from pyipmi.msgs import create_request_by_name
from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.utils import check_completion_code

class Bmc:
    def get_device_id(self):
        req = create_request_by_name('GetDeviceId')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return DeviceId(rsp)

    def cold_reset(self):
        req = create_request_by_name('ColdReset')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def warm_reset(self):
        req = create_request_by_name('WarmReset')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def i2c_write_read(self, type, id, channel, address, count, data=None):
        req = create_request_by_name('MasterWriteRead')
        req.bus_id.type = type
        req.bus_id.id= id
        req.bus_id.channel = channel
        req.bus_id.slave_address = address
        req.read_count = count
        if data:
            req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.data

    def i2c_write(self, type, id, channel, address, data):
        self.i2c_write_read(type, id, channel, address, 0, data)

    def i2c_read(self, type, id, channel, address, count):
        return self.i2c_write_read(type, id, channel, address, count, None)

    def set_watchdog_timer(self, config):
        req = create_request_by_name('SetWatchdogTimer')
        req.timer_use.timer_use = config.timer_use
        req.timer_use.dont_stop = config.dont_stop and 1 or 0
        req.timer_use.dont_log = config.dont_log and 1 or 0

        req.timer_actions.pre_timeout_interrupt = \
                config.pre_timeout_interrupt
        req.timer_actions.timeout_action = \
                config.timeout_action

        req.pre_timeout_interval = config.pre_timeout_interval
        req.timer_use_expiration_flags = config.timer_use_expiration_flags
        req.initial_countdown = config.initial_countdown
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_watchdog_timer(self):
        req = create_request_by_name('GetWatchdogTimer')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return Watchdog(rsp)

    def reset_watchdog_timer(self):
        req = create_request_by_name('ResetWatchdogTimer')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)


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
            ('is_running', ''),
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

    def from_response(self, rsp):
        self.timer_use = rsp.timer_use.timer_use
        self.is_running = bool(rsp.timer_use.is_running)
        self.dont_log = bool(rsp.timer_use.dont_log)
        self.pre_timeout_interrupt = rsp.timer_actions.pre_timeout_interrupt
        self.timeout_action = rsp.timer_actions.timeout_action
        self.pre_timeout_interval = rsp.pre_timeout_interval
        self.timer_use_expiration_flags = rsp.timer_use_expiration_flags
        self.initial_countdown = rsp.initial_countdown
        self.present_countdown = rsp.present_countdown


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

        if rsp.auxiliary is not None:
            self.aux = list(rsp.auxiliary)
        else:
            self.aux = None
