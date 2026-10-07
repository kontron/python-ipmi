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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

"""Sensor and event commands of the sensor device.

A sensor device has sensors, which are described by the Sensor Data Records
(SDR) of its device SDR repository. The commands read the sensors and their
thresholds, set the thresholds and send platform events.

The commands are the methods of :class:`Sensor`, which are available on
:class:`pyipmi.Ipmi`. The ``SENSOR_TYPE_*`` constants are the sensor types,
the ``EVENT_READING_TYPE_*`` constants the event/reading types of the IPMI
specification.

Example:
    Print the value of the full sensor records of a device::

        for record in ipmi.device_sdr_entries():
            if isinstance(record, pyipmi.sdr.SdrFullSensorRecord):
                raw, states = ipmi.get_sensor_reading(record.number,
                                                      record.owner_lun)
                value = record.convert_sensor_raw_to_value(raw)
                print(record.device_id_string, value)
"""

from __future__ import annotations

from array import array
from collections.abc import Generator

from .utils import check_completion_code
from .msgs import create_request_by_name

from .helper import (get_sdr_data_helper, get_sdr_chunk_helper,
                     ReadLength)

from . import sdr
from .mixin import IpmiMixin


# THRESHOLD BASED STATES
EVENT_READING_TYPE_CODE_THRESHOLD = 0x01
# DMI-based "Usage States" STATES
EVENT_READING_TYPE_CODE_DISCRETE = 0x02
# DIGITAL/DISCRETE EVENT STATES
EVENT_READING_TYPE_CODE_STATE = 0x03
EVENT_READING_TYPE_CODE_PREDICTIVE_FAILURE = 0x04
EVENT_READING_TYPE_CODE_LIMIT = 0x05
EVENT_READING_TYPE_CODE_PERFORMANCE = 0x06
EVENT_READING_TYPE_SENSOR_SPECIFIC = 0x6f

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

# VITA-defined sensor types
SENSOR_TYPE_VITA_FRU_STATE = 0xf0
SENSOR_TYPE_VITA_IPMB_LINK = 0xf1
SENSOR_TYPE_VITA_FRU_HEALTH = 0xf2
SENSOR_TYPE_VITA_FRU_TEMPERATURE = 0xf3
SENSOR_TYPE_VITA_PAYLOAD_TEST = 0xf4
SENSOR_TYPE_VITA_PAYLOAD_TEST_STATUS = 0xf5
SENSOR_TYPE_VITA_PAYLOAD_MODE = 0xf7
SENSOR_TYPE_VITA_IPMC_RESET_TYPE = 0xf8


class Sensor(IpmiMixin):
    """Sensor device commands, available on :class:`pyipmi.Ipmi`.

    The device SDRs are read in chunks. If the device cannot return the
    requested number of bytes, the chunk size is reduced and kept for the
    following records.
    """

    def __init__(self) -> None:
        """Initialize the sensor command group."""
        # read length of the device SDRs, a reduced length is kept for the
        # following records
        self._device_sdr_read_length = ReadLength()

    def reserve_device_sdr_repository(self) -> int:
        """Reserve the device SDR repository.

        A reservation is needed to read records partially. It is canceled
        when the repository changes.

        Returns:
            The reservation ID.
        """
        rsp = self.send_message_by_name('ReserveDeviceSdrRepository')
        return rsp.reservation_id

    def _get_device_sdr_chunk(self, reservation_id: int, record_id: int,
                              offset: int, length: int) -> tuple[int, array]:
        req = create_request_by_name('GetDeviceSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.bytes_to_read = length

        rsp = get_sdr_chunk_helper(self.send_message, req,
                                   self.reserve_device_sdr_repository)

        return (rsp.next_record_id, rsp.record_data)

    def get_device_sdr(self, record_id: int,
                       reservation_id: int | None = None) -> sdr.SdrCommon:
        """Read and decode a record of the device SDR repository.

        Args:
            record_id: The record ID, 0 for the first record.
            reservation_id: The reservation ID, the device SDR repository is
                reserved if None.

        Returns:
            The decoded record, its ``next_id`` is the record ID of the next
            record, 0xffff for the last record.

        Raises:
            DecodingError: The record data is invalid.
        """
        (next_id, record_data) = \
            get_sdr_data_helper(self.reserve_device_sdr_repository,
                                self._get_device_sdr_chunk,
                                record_id, reservation_id,
                                self._device_sdr_read_length)

        return sdr.SdrCommon.from_data(record_data, next_id)

    def device_sdr_entries(self) -> Generator[sdr.SdrCommon, None, None]:
        """Return a generator of all records of the device SDR repository.

        The repository is reserved once. The records are read starting with
        record ID 0 until the next record ID is 0xffff.

        Yields:
            The decoded records.
        """
        reservation_id = self.reserve_device_sdr_repository()
        record_id = 0

        while True:
            record = self.get_device_sdr(record_id, reservation_id)
            yield record
            if record.next_id == 0xffff:
                break
            record_id = record.next_id

    def get_device_sdr_list(self, reservation_id: int | None = None) -> list[sdr.SdrCommon]:
        """Return all records of the device SDR repository.

        Args:
            reservation_id: Not used, the repository is reserved by
                :meth:`device_sdr_entries`.

        Returns:
            The decoded records.
        """
        return list(self.device_sdr_entries())

    def rearm_sensor_events(self, sensor_number: int) -> None:
        """Rearm the events of a sensor.

        Args:
            sensor_number: The sensor number.
        """
        self.send_message_by_name('RearmSensorEvents',
                                  sensor_number=sensor_number)

    def get_sensor_reading(self, sensor_number: int,
                           lun: int = 0) -> tuple[int | None, int | None]:
        """Read a sensor.

        The raw reading is converted to the sensor unit with
        :meth:`pyipmi.sdr.SdrFullSensorRecord.convert_sensor_raw_to_value`.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            A tuple of the raw reading and the states. The raw reading is
            None while the initial update of the sensor is in progress. The
            states are a bit mask, the threshold comparison status of a
            threshold sensor or the asserted states of a discrete sensor in
            bits 0-14. They are None if the sensor does not report them.
        """
        rsp = self.send_message_by_name('GetSensorReading',
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

    def set_sensor_thresholds(self, sensor_number: int, lun: int = 0,
                              unr: int | None = None, ucr: int | None = None,
                              unc: int | None = None, lnc: int | None = None,
                              lcr: int | None = None,
                              lnr: int | None = None) -> None:
        """Set the thresholds of a sensor that are not None.

        The thresholds are raw values, a value in the sensor unit is
        converted with
        :meth:`pyipmi.sdr.SdrFullSensorRecord.convert_sensor_value_to_raw`.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.
            unr: The upper non-recoverable threshold.
            ucr: The upper critical threshold.
            unc: The upper non-critical threshold.
            lnc: The lower non-critical threshold.
            lcr: The lower critical threshold.
            lnr: The lower non-recoverable threshold.

        Raises:
            CompletionCodeError: The device rejected the request, e.g. for a
                threshold that is not settable.
        """
        req = create_request_by_name('SetSensorThresholds')
        req.sensor_number = sensor_number
        req.lun = lun

        thresholds = dict(unr=unr, ucr=ucr, unc=unc, lnc=lnc, lcr=lcr, lnr=lnr)

        for key, value in thresholds.items():
            if value is not None:
                setattr(req.set_mask, key, 1)
                setattr(req.threshold, key, value)

        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_sensor_thresholds(self, sensor_number: int, lun: int = 0) -> dict[str, int]:
        """Get the readable thresholds of a sensor.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            The raw thresholds that are readable, with the keys ``'unr'``,
            ``'ucr'``, ``'unc'``, ``'lnc'``, ``'lcr'`` and ``'lnr'``
            (upper/lower non-recoverable, critical and non-critical).
        """
        rsp = self.send_message_by_name('GetSensorThresholds',
                                        sensor_number=sensor_number,
                                        lun=lun)

        thresholds = {}
        threshold_list = ('unr', 'ucr', 'unc', 'lnc', 'lcr', 'lnr')
        for threshold in threshold_list:
            if hasattr(rsp.readable_mask, threshold):
                if getattr(rsp.readable_mask, threshold):
                    thresholds[threshold] = getattr(rsp.threshold, threshold)
        return thresholds

    def send_platform_event(self, sensor_type: int, sensor_number: int,
                            event_type: int, asserted: bool = True,
                            event_data: list[int] | None = None) -> None:
        """Send a platform event message to the event receiver.

        Args:
            sensor_type: The sensor type, one of the ``SENSOR_TYPE_*``
                constants.
            sensor_number: The number of the sensor that generated the
                event.
            event_type: The event/reading type, one of the
                ``EVENT_READING_TYPE_*`` constants.
            asserted: True for an assertion event, False for a deassertion
                event.
            event_data: The event data bytes 1 - 3, ``[0]`` if None.

        Raises:
            CompletionCodeError: The device rejected the event.
        """
        req = create_request_by_name('PlatformEvent')
        req.sensor_type = sensor_type
        req.sensor_number = sensor_number
        req.event_type.type = event_type
        req.event_type.dir = 0 if asserted else 1
        req.event_data = [0] if event_data is None else event_data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
