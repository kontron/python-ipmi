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

"""BMC device commands: device ID, resets, I2C access and watchdog timer.

The commands are the methods of :class:`Bmc`, which are available on
:class:`pyipmi.Ipmi`.

Example:
    Print the device ID and the firmware version of the BMC::

        device_id = ipmi.get_device_id()
        print(device_id.device_id, device_id.fw_revision)
"""

from __future__ import annotations

from array import array

from .msgs import create_request_by_name, Message
from .utils import check_completion_code
from .state import State
from .fields import VersionField
from .constants import manufacturer_name
from .mixin import IpmiMixin


class Bmc(IpmiMixin):
    """BMC device commands, available on :class:`pyipmi.Ipmi`."""

    def get_device_id(self) -> DeviceId:
        """Get the device ID of the controller.

        Returns:
            The device ID, firmware version, IPMI version and supported
            functions of the controller.
        """
        return DeviceId(self.send_message_by_name('GetDeviceId'))

    def get_device_guid(self) -> DeviceGuid:
        """Get the GUID of the controller.

        Returns:
            The device GUID.
        """
        return DeviceGuid(self.send_message_by_name('GetDeviceGuid'))

    def cold_reset(self) -> None:
        """Cold reset the controller, it is reinitialized."""
        self.send_message_by_name('ColdReset')

    def warm_reset(self) -> None:
        """Warm reset the controller, its state is kept."""
        self.send_message_by_name('WarmReset')

    def i2c_write_read(self, bus_type: int, bus_id: int, channel: int,
                       address: int, count: int,
                       data: bytes | None = None) -> array:
        """Write to and read from a device on an I2C bus of the controller.

        The data is written first, then ``count`` bytes are read.

        Args:
            bus_type: 0 for a public bus (IPMB), 1 for a private bus.
            bus_id: The bus ID.
            channel: The channel number of a public bus.
            address: The 7-bit I2C address of the device.
            count: The number of bytes to read.
            data: The data to write, nothing is written if None or empty.

        Returns:
            The data read.

        Raises:
            CompletionCodeError: The controller rejected the request, e.g.
                because the device did not acknowledge.
        """
        req = create_request_by_name('MasterWriteRead')
        req.bus_id.type = bus_type
        req.bus_id.id = bus_id
        req.bus_id.channel = channel
        req.bus_id.slave_address = address
        req.read_count = count
        if data:
            req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.data

    def i2c_write(self, bus_type: int, bus_id: int, channel: int,
                  address: int, data: bytes) -> None:
        """Write to a device on an I2C bus of the controller.

        Args:
            bus_type: 0 for a public bus (IPMB), 1 for a private bus.
            bus_id: The bus ID.
            channel: The channel number of a public bus.
            address: The 7-bit I2C address of the device.
            data: The data to write.

        Raises:
            CompletionCodeError: The controller rejected the request.
        """
        self.i2c_write_read(bus_type, bus_id, channel, address, 0, data)

    def i2c_read(self, bus_type: int, bus_id: int, channel: int,
                 address: int, count: int) -> array:
        """Read from a device on an I2C bus of the controller.

        Args:
            bus_type: 0 for a public bus (IPMB), 1 for a private bus.
            bus_id: The bus ID.
            channel: The channel number of a public bus.
            address: The 7-bit I2C address of the device.
            count: The number of bytes to read.

        Returns:
            The data read.

        Raises:
            CompletionCodeError: The controller rejected the request.
        """
        return self.i2c_write_read(bus_type, bus_id, channel,
                                   address, count, None)

    def set_watchdog_timer(self, config: Watchdog) -> None:
        """Set the watchdog timer.

        The timer is started with :meth:`reset_watchdog_timer`.

        Args:
            config: The settings of the watchdog timer. All attributes
                except ``is_running`` and ``present_countdown`` have to be
                set.

        Raises:
            CompletionCodeError: The controller rejected the settings.
        """
        req = create_request_by_name('SetWatchdogTimer')
        req.timer_use.timer_use = config.timer_use
        req.timer_use.dont_stop = config.dont_stop and 1 or 0
        req.timer_use.dont_log = config.dont_log and 1 or 0

        req.timer_actions.pre_timeout_interrupt = config.pre_timeout_interrupt
        req.timer_actions.timeout_action = config.timeout_action

        req.pre_timeout_interval = config.pre_timeout_interval
        req.timer_use_expiration_flags = config.timer_use_expiration_flags
        req.initial_countdown = config.initial_countdown
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_watchdog_timer(self) -> Watchdog:
        """Get the settings and the present countdown of the watchdog timer.

        Returns:
            The watchdog timer, ``dont_stop`` is not set.
        """
        return Watchdog(self.send_message_by_name('GetWatchdogTimer'))

    def reset_watchdog_timer(self) -> None:
        """Start or restart the watchdog timer with its initial countdown.

        Raises:
            CompletionCodeError: The timer was not set before (0x80).
        """
        self.send_message_by_name('ResetWatchdogTimer')


class Watchdog(State):
    """The settings of the watchdog timer.

    The ``TIMER_USE_*`` and ``TIMEOUT_ACTION_*`` constants are the timer
    uses and the timeout actions.

    Attributes:
        timer_use (int): The use of the timer, one of the ``TIMER_USE_*``
            constants.
        is_running (bool): Only returned: the timer is running.
        dont_log (bool): Don't log the timer expiration in the SEL.
        pre_timeout_interrupt (int): The interrupt before the timeout
            action: 0 none, 1 SMI, 2 NMI / diagnostic interrupt, 3 messaging
            interrupt.
        timeout_action (int): The action on the timer expiration, one of
            the ``TIMEOUT_ACTION_*`` constants.
        pre_timeout_interval (int): The time in seconds before the timeout
            action at which the pre-timeout interrupt is generated.
        timer_use_expiration_flags (int): A bit mask with one bit per timer
            use, bit 1 for BIOS FRB2 up to bit 5 for OEM: the expired timer
            uses when returned, the flags to clear when set.
        initial_countdown (int): The countdown value in 100 ms units.
        present_countdown (int): Only returned: the present countdown value
            in 100 ms units.
    """

    TIMER_USE_OEM = 5
    TIMER_USE_SMS_OS = 4
    TIMER_USE_OS_LOAD = 3
    TIMER_USE_BIOS_POST = 2
    TIMER_USE_BIOS_FRB2 = 1

    TIMEOUT_ACTION_NO_ACTION = 0
    TIMEOUT_ACTION_HARD_RESET = 1
    TIMEOUT_ACTION_POWER_DOWN = 2
    TIMEOUT_ACTION_POWER_CYCLE = 3

    #: Only used to set the timer: keep a running timer running. It is not
    #: returned by :meth:`Bmc.get_watchdog_timer`.
    dont_stop: bool | None

    __properties__ = [
        # (property, description)
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

    def _from_response(self, rsp: Message) -> None:
        self.timer_use = rsp.timer_use.timer_use
        self.is_running = bool(rsp.timer_use.is_running)
        self.dont_log = bool(rsp.timer_use.dont_log)
        self.pre_timeout_interrupt = rsp.timer_actions.pre_timeout_interrupt
        self.timeout_action = rsp.timer_actions.timeout_action
        self.pre_timeout_interval = rsp.pre_timeout_interval
        self.timer_use_expiration_flags = rsp.timer_use_expiration_flags
        self.initial_countdown = rsp.initial_countdown
        self.present_countdown = rsp.present_countdown


class DeviceId(State):
    """The device ID of a controller.

    Attributes:
        device_id (int): The device ID.
        revision (int): The device revision.
        provides_sdrs (bool): The device provides device SDRs.
        available (bool): The device firmware, an SDR update or the
            self-initialization is in progress. Despite its name, the
            device is in normal operation if this is False.
        fw_revision (VersionField): The firmware revision.
        ipmi_version (VersionField): The IPMI version, e.g. 2.0.
        manufacturer_id (int): The IANA manufacturer ID.
        manufacturer_name (str | None): The name of a well known
            manufacturer, see :func:`pyipmi.constants.manufacturer_name`.
            None for other manufacturers.
        product_id (int): The product ID.
        supported_functions (list[str]): The supported device functions,
            see :meth:`supports_function`.
        aux (list[int] | None): The auxiliary firmware revision, None if
            the controller does not report it.
    """

    def __str__(self) -> str:
        """Return the device ID fields as one line."""
        string = 'Device ID: %d' % self.device_id
        string += ' revision: %d' % self.revision
        string += ' available: %d' % self.available
        string += ' fw version: %s' % (self.fw_revision)
        string += ' ipmi: %s' % self.ipmi_version
        string += ' manufacturer: %d' % self.manufacturer_id
        string += ' product: %d' % self.product_id
        string += ' functions: %s' % ','.join(self.supported_functions)
        return string

    def supports_function(self, name: str) -> bool:
        """Return whether the device supports a function.

        Args:
            name: The function, one of 'SENSOR', 'SDR_REPOSITORY', 'SEL',
                'FRU_INVENTORY', 'IPMB_EVENT_RECEIVER',
                'IPMB_EVENT_GENERATOR', 'BRIDGE' or 'CHASSIS', in any case.

        Returns:
            True if the function is supported.
        """
        return name.lower() in self.supported_functions

    def _from_response(self, rsp: Message) -> None:
        self.device_id = rsp.device_id
        self.revision = rsp.device_revision.device_revision
        self.provides_sdrs = bool(rsp.device_revision.provides_device_sdrs)
        self.available = bool(rsp.firmware_revision.device_available)

        self.fw_revision = VersionField(
            (rsp.firmware_revision.major, rsp.firmware_revision.minor))

        self.ipmi_version = VersionField(
            (rsp.ipmi_version & 0xf, (rsp.ipmi_version >> 4) & 0xf))

        self.manufacturer_id = rsp.manufacturer_id
        self.manufacturer_name = manufacturer_name(self.manufacturer_id)
        self.product_id = rsp.product_id

        self.supported_functions = []
        functions = ('sensor',
                     'sdr_repository',
                     'sel',
                     'fru_inventory',
                     'ipmb_event_receiver',
                     'ipmb_event_generator',
                     'bridge',
                     'chassis')

        for function in functions:
            if hasattr(rsp.additional_support, function):
                if getattr(rsp.additional_support, function):
                    self.supported_functions.append(function)

        self.aux = None
        if rsp.auxiliary is not None:
            self.aux = list(rsp.auxiliary)


class DeviceGuid(State):
    """The GUID of a controller.

    Attributes:
        device_guid (Sequence[int]): The 16 bytes of the GUID as returned.
        device_guid_string (str): The GUID in the usual string format.
    """

    def __str__(self) -> str:
        """Return the GUID string."""
        return 'Device GUID: %s' % self.device_guid_string

    def _from_response(self, rsp: Message) -> None:
        self.device_guid = rsp.device_guid
        self.device_guid_string = \
            '%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-' \
            '%02x%02x%02x%02x%02x%02x' % tuple(reversed(self.device_guid))
