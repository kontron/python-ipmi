# cOPYRIGht (c) 2014  Kontron Europe GmbH
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

from __future__ import absolute_import

# from builtins import object

# import math
# from . import errors
# import array
# import time
# from pyipmi.errors import DecodingError, CompletionCodeError, RetryError
from .utils import check_completion_code # ByteBuffer
from .msgs import create_request_by_name
# from .msgs import constants

from .helper import get_sdr_data_helper, get_sdr_chunk_helper

from . import sdr


# THRESHOLD BASED STATES
EVENT_READING_TYPE_CODE_THRESHOLD = 0x01
# DMI-based "Usage States" STATES
EVENT_READING_TYPE_CODE_DISCRETE = 0x02
# DIGITAL/DISCRETE EVENT STATES
EVENT_READING_TYPE_CODE_STATE = 0x03
EVENT_READING_TYPE_CODE_PREDICTIVE_FAILURE = 0x04
EVENT_READING_TYPE_CODE_LIMIT = 0x05
EVENT_READING_TYPE_CODE_PERFORMANCE = 0x06

# Sensor Types
SENSOR_TYPE_TEMPERATURE = 0x01
SENSOR_TYPE_VOLTAGE = 0x02
SENSOR_TYPE_CURRENT = 0x03
SENSOR_TYPE_FAN = 0x04
SENSOR_TYPE_CHASSIS_INTRUSION = 0x05
SENSOR_TYPE_PLATFORM_SECURITY = 0x06
SENSOR_TYPE_PROCESSOR = 0x07
SENSOR_TYPE_POWER_SUPPLY = 0x08
SENSOR_TYPE_POWER_UNIT = 0x09
SENSOR_TYPE_COOLING_DEVICE = 0x0a
SENSOR_TYPE_OTHER_UNITS_BASED_SENSOR = 0x0b
SENSOR_TYPE_MEMORY = 0x0c
SENSOR_TYPE_DRIVE_SLOT = 0x0d
SENSOR_TYPE_POST_MEMORY_RESIZE = 0x0e
SENSOR_TYPE_SYSTEM_FIRMWARE_PROGRESS = 0x0f
SENSOR_TYPE_EVENT_LOGGING_DISABLED = 0x10
SENSOR_TYPE_WATCHDOG_1 = 0x11
SENSOR_TYPE_SYSTEM_EVENT = 0x12
SENSOR_TYPE_CRITICAL_INTERRUPT = 0x13
SENSOR_TYPE_BUTTON = 0x14
SENSOR_TYPE_MODULE_BOARD = 0x15
SENSOR_TYPE_MICROCONTROLLER_COPROCESSOR = 0x16
SENSOR_TYPE_ADD_IN_CARD = 0x17
SENSOR_TYPE_CHASSIS = 0x18
SENSOR_TYPE_CHIP_SET = 0x19
SENSOR_TYPE_OTHER_FRU = 0x1a
SENSOR_TYPE_CABLE_INTERCONNECT = 0x1b
SENSOR_TYPE_TERMINATOR = 0x1c
SENSOR_TYPE_SYSTEM_BOOT_INITIATED = 0x1d
SENSOR_TYPE_BOOT_ERROR = 0x1e
SENSOR_TYPE_OS_BOOT = 0x1f
SENSOR_TYPE_OS_CRITICAL_STOP = 0x20
SENSOR_TYPE_SLOT_CONNECTOR = 0x21
SENSOR_TYPE_SYSTEM_ACPI_POWER_STATE = 0x22
SENSOR_TYPE_WATCHDOG_2 = 0x23
SENSOR_TYPE_PLATFORM_ALERT = 0x24
SENSOR_TYPE_ENTITY_PRESENT = 0x25
SENSOR_TYPE_MONITOR_ASIC_IC = 0x26
SENSOR_TYPE_LAN = 0x27
SENSOR_TYPE_MANGEMENT_SUBSYSTEM_HEALTH = 0x28
SENSOR_TYPE_BATTERY = 0x29
SENSOR_TYPE_SESSION_AUDIT = 0x2a
SENSOR_TYPE_VERSION_CHANGE = 0x2b
SENSOR_TYPE_FRU_STATE = 0x2c
SENSOR_TYPE_FRU_HOT_SWAP = 0xf0
SENSOR_TYPE_IPMB_PHYSICAL_LINK = 0xf1
SENSOR_TYPE_MODULE_HOT_SWAP = 0xf2
SENSOR_TYPE_POWER_CHANNEL_NOTIFICATION = 0xf3
SENSOR_TYPE_TELCO_ALARM_INPUT = 0xf4

SENSOR_TYPE_OEM_KONTRON_FRU_INFORMATION_AGENT = 0xc5
SENSOR_TYPE_OEM_KONTRON_POST_VALUE = 0xc6
SENSOR_TYPE_OEM_KONTRON_FW_UPGRADE = 0xc7
SENSOR_TYPE_OEM_KONTRON_DIAGNOSTIC = 0xc9
SENSOR_TYPE_OEM_KONTRON_SYSTEM_FIRMWARE_UPGRADE = 0xca
SENSOR_TYPE_OEM_KONTRON_POWER_DENIED = 0xcd
SENSOR_TYPE_OEM_KONTRON_RESET = 0xcf


class Sensor(object):
    def reserve_device_sdr_repository(self):
        rsp = self.send_message_with_name('ReserveDeviceSdrRepository')
        return  rsp.reservation_id

    def _get_device_sdr_chunk(self, reservation_id, record_id, offset, length):
        req = create_request_by_name('GetDeviceSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.bytes_to_read = length

        rsp = get_sdr_chunk_helper(self.send_message, req, \
                self.reserve_device_sdr_repository)

        return (rsp.next_record_id, rsp.record_data)

    def get_device_sdr(self, record_id, reservation_id=None):
        """Collects all data from the sensor device to get the SDR
        specified by record id.

        `record_id` the Record ID.
        `reservation_id=None` can be set. if None the reservation ID will
        be determined.
        """
        (next_id, record_data) = get_sdr_data_helper(self.reserve_device_sdr_repository,
                self._get_device_sdr_chunk, record_id, reservation_id)

        return sdr.SdrCommon.from_data(record_data, next_id)

    def device_sdr_entries(self):
        """A generator that returns the SDR list. Starting with ID=0x0000 and
        end when ID=0xffff is returned.
        """
        reservation_id = self.reserve_device_sdr_repository()
        record_id = 0

        while True:
            s = self.get_device_sdr(record_id, reservation_id)
            yield s
            if s.next_id == 0xffff:
                break
            record_id = s.next_id

    def get_device_sdr_list(self, reservation_id=None):
        """Returns the complete SDR list.
        """
        return list(self.device_sdr_entries())

    def rearm_sensor_events(self, sensor_number):
        """Rearm sensor events for the given sensor number.
        """
        self.send_message_with_name('RearmSensorEvents',
                                    sensor_number=sensor_number)

    def get_sensor_reading(self, sensor_number, lun=0):
        """Returns the sensor reading at the assertion states for the given
        sensor number.

        `sensor_number`

        Returns a tuple with `raw reading`and `assertion states`.
        """
        rsp = self.send_message_with_name('GetSensorReading',
                                          sensor_number=sensor_number,
                                          lun=lun)

        reading = rsp.sensor_reading
        if rsp.config.initial_update_in_progress:
            reading = None

        states = None
        if rsp.states1 is not None:
            states = rsp.states1
            if rsp.states2 is not None:
                states |= (rsp.states2 << 8)
        return (reading, states)

    def set_sensor_thresholds(self, sensor_number, lun=0, unr=None, ucr=None,
                unc=None, lnc=None, lcr=None, lnr=None):
        """Set the sensor thresholds that are not 'None'

        `sensor_number`
        `unr` for upper non-recoverable
        `ucr` for upper critical
        `unc` for upper non-critical
        `lnc` for lower non-critical
        `lcr` for lower critical
        `lnr` for lower non-recoverable
        """
        req = create_request_by_name('SetSensorThresholds')
        req.sensor_number = sensor_number
        req.lun = lun

        thresholds = dict(unr=unr, ucr=ucr, unc=unc, lnc=lnc, lcr=lcr, lnr=lnr)

        for k, v in thresholds.items():
            if v is not None:
                setattr(req.set_mask, k, 1)
                setattr(req.threshold, k, v)

        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_sensor_thresholds(self, sensor_number, lun=0):
        rsp = self.send_message_with_name('GetSensorThresholds',
                                          sensor_number=sensor_number,
                                          lun=lun)

        thresholds = {}
        threshold_list = ('unr', 'ucr', 'unc', 'lnc', 'lcr', 'lnr')
        for t in threshold_list:
            if hasattr(rsp.readable_mask, t):
                if getattr(rsp.readable_mask, t):
                    thresholds[t] = getattr(rsp.threshold, t)
        return thresholds
