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

"""Sensor Data Records (SDR) and the SDR repository commands.

Sensor Data Records describe the sensors and devices of a system: e.g.
the sensor type, the conversion of the raw readings and the thresholds of
a sensor. The records are stored in the SDR repository of the BMC or in
the device SDR repository of a controller (see :mod:`pyipmi.sensor`).

The repository commands are the methods of :class:`Sdr`, which are
available on :class:`pyipmi.Ipmi`. A record is decoded by
:meth:`SdrCommon.from_data` into the class for its record type, e.g.
:class:`SdrFullSensorRecord`. The ``SDR_TYPE_*`` constants are the record
types, the ``L_*`` constants the linearizations of a sensor reading.

Example:
    Print the full sensor records of the SDR repository::

        for sdr in ipmi.sdr_repository_entries():
            if isinstance(sdr, pyipmi.sdr.SdrFullSensorRecord):
                print(sdr.number, sdr.device_id_string)
"""

from __future__ import annotations

import math
from array import array
from collections.abc import Callable, Generator

from . import errors

from .errors import DecodingError
from .fields import SdrTypeLengthString
from .utils import check_completion_code, ByteBuffer, ByteSequence
from .msgs import create_request_by_name, Message

from .helper import get_sdr_data_helper, clear_repository_helper
from .helper import get_sdr_chunk_helper, ReadLength
from .state import State
from .constants import manufacturer_name
from .mixin import IpmiMixin

SDR_TYPE_FULL_SENSOR_RECORD = 0x01
SDR_TYPE_COMPACT_SENSOR_RECORD = 0x02
SDR_TYPE_EVENT_ONLY_SENSOR_RECORD = 0x03
SDR_TYPE_ENTITY_ASSOCIATION_RECORD = 0x08
SDR_TYPE_FRU_DEVICE_LOCATOR_RECORD = 0x11
SDR_TYPE_MANAGEMENT_CONTROLLER_DEVICE_LOCATOR_RECORD = 0x12
SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD = 0x13
SDR_TYPE_BMC_MESSAGE_CHANNEL_INFO_RECORD = 0x14
SDR_TYPE_OEM_SENSOR_RECORD = 0xC0

GET_INITIALIZATION_AGENT_STATUS = 0
RUN_INITIALIZATION_AGENT = 1

L_LINEAR = 0
L_LN = 1
L_LOG = 2
L_LOG2 = 3
L_E = 4
L_EXP10 = 5
L_EXP2 = 6
L_1_X = 7
L_SQR = 8
L_CUBE = 9
L_SQRT = 10
L_CUBERT = 11

# Names of the record types
SDR_TYPE_NAMES = {
    SDR_TYPE_FULL_SENSOR_RECORD: 'Full Sensor Record',
    SDR_TYPE_COMPACT_SENSOR_RECORD: 'Compact Sensor Record',
    SDR_TYPE_EVENT_ONLY_SENSOR_RECORD: 'Event-Only Record',
    SDR_TYPE_ENTITY_ASSOCIATION_RECORD: 'Entity Association Record',
    0x09: 'Device-relative Entity Association Record',
    0x10: 'Generic Device Locator Record',
    SDR_TYPE_FRU_DEVICE_LOCATOR_RECORD: 'FRU Device Locator Record',
    SDR_TYPE_MANAGEMENT_CONTROLLER_DEVICE_LOCATOR_RECORD:
        'Management Controller Device Locator Record',
    SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD:
        'Management Controller Confirmation Record',
    SDR_TYPE_BMC_MESSAGE_CHANNEL_INFO_RECORD:
        'BMC Message Channel Info Record',
    SDR_TYPE_OEM_SENSOR_RECORD: 'OEM Record',
}

# Names of the entity IDs (IPMI v2.0 table 43-13, PICMG 3.0 table 3-5)
ENTITY_ID_NAMES = {
    0x00: 'Unspecified',
    0x01: 'Other',
    0x02: 'Unknown',
    0x03: 'Processor',
    0x04: 'Disk or Disk Bay',
    0x05: 'Peripheral Bay',
    0x06: 'System Management Module',
    0x07: 'System Board',
    0x08: 'Memory Module',
    0x09: 'Processor Module',
    0x0a: 'Power Supply',
    0x0b: 'Add-in Card',
    0x0c: 'Front Panel Board',
    0x0d: 'Back Panel Board',
    0x0e: 'Power System Board',
    0x0f: 'Drive Backplane',
    0x10: 'System Internal Expansion Board',
    0x11: 'Other System Board',
    0x12: 'Processor Board',
    0x13: 'Power Unit / Power Domain',
    0x14: 'Power Module / DC-to-DC Converter',
    0x15: 'Power Management / Power Distribution Board',
    0x16: 'Chassis Back Panel Board',
    0x17: 'System Chassis',
    0x18: 'Sub-Chassis',
    0x19: 'Other Chassis Board',
    0x1a: 'Disk Drive Bay',
    0x1b: 'Peripheral Bay',
    0x1c: 'Device Bay',
    0x1d: 'Fan / Cooling Device',
    0x1e: 'Cooling Unit / Cooling Domain',
    0x1f: 'Cable / Interconnect',
    0x20: 'Memory Device',
    0x21: 'System Management Software',
    0x22: 'System Firmware',
    0x23: 'Operating System',
    0x24: 'System Bus',
    0x25: 'Group',
    0x26: 'Remote Management Communication Device',
    0x27: 'External Environment',
    0x28: 'Battery',
    0x29: 'Processing Blade',
    0x2a: 'Connectivity Switch',
    0x2b: 'Processor / Memory Module',
    0x2c: 'I/O Module',
    0x2d: 'Processor / IO Module',
    0x2e: 'Management Controller Firmware',
    0x2f: 'IPMI Channel',
    0x30: 'PCI Bus',
    0x31: 'PCI Express Bus',
    0x32: 'SCSI Bus (parallel)',
    0x33: 'SATA / SAS Bus',
    0x34: 'Processor / Front-side Bus',
    0x35: 'Real Time Clock (RTC)',
    0x37: 'Air Inlet',
    0x40: 'Air Inlet',
    0x41: 'Processor / CPU',
    0x42: 'Baseboard',
    0xa0: 'PICMG Front Board',
    0xc0: 'PICMG Rear Transition Module',
    0xc1: 'PICMG AdvancedMC Module',
    0xc2: 'PICMG MicroTCA Carrier Hub',
    0xf0: 'PICMG Shelf Management Controller',
    0xf1: 'PICMG Filtration Unit',
    0xf2: 'PICMG Shelf FRU Information',
    0xf3: 'PICMG Alarm Panel',
}

# Names of the sensor unit type codes (IPMI v2.0 table 43-15)
UNIT_NAMES = (
    'unspecified', 'degrees C', 'degrees F', 'degrees K', 'Volts', 'Amps',
    'Watts', 'Joules', 'Coulombs', 'VA', 'Nits', 'lumen', 'lux', 'Candela',
    'kPa', 'PSI', 'Newton', 'CFM', 'RPM', 'Hz', 'microsecond',
    'millisecond', 'second', 'minute', 'hour', 'day', 'week', 'mil',
    'inches', 'feet', 'cu in', 'cu feet', 'mm', 'cm', 'm', 'cu cm', 'cu m',
    'liters', 'fluid ounce', 'radians', 'steradians', 'revolutions',
    'cycles', 'gravities', 'ounce', 'pound', 'ft-lb', 'oz-in', 'gauss',
    'gilberts', 'henry', 'millihenry', 'farad', 'microfarad', 'ohms',
    'siemens', 'mole', 'becquerel', 'PPM', 'reserved', 'Decibels', 'DbA',
    'DbC', 'gray', 'sievert', 'color temp deg K', 'bit', 'kilobit',
    'megabit', 'gigabit', 'byte', 'kilobyte', 'megabyte', 'gigabyte',
    'word', 'dword', 'qword', 'line', 'hit', 'miss', 'retry', 'reset',
    'overrun / overflow', 'underrun', 'collision', 'packets', 'messages',
    'characters', 'error', 'correctable error', 'uncorrectable error',
    'fatal error', 'grams',
)

# The rate units of the sensor units 1 byte, bits 5:3
_RATE_UNITS = ('', ' per microsecond', ' per millisecond', ' per second',
               ' per minute', ' per hour', ' per day')


def sdr_type_to_string(sdr_type: int) -> str:
    """Return the name of a record type.

    Args:
        sdr_type: The record type.

    Returns:
        The name of the record type, 'Unknown Record' for an unknown type.
    """
    return SDR_TYPE_NAMES.get(sdr_type, 'Unknown Record')


def entity_id_to_string(entity_id: int) -> str:
    """Return the name of an entity ID.

    Args:
        entity_id: The entity ID.

    Returns:
        The name of the entity, the kind of the range for an ID that is
        chassis-specific, board-set specific or OEM.
    """
    name = ENTITY_ID_NAMES.get(entity_id)
    if name is not None:
        return name
    if 0x90 <= entity_id <= 0xaf:
        return 'Chassis-specific'
    if 0xb0 <= entity_id <= 0xcf:
        return 'Board-set specific'
    if entity_id >= 0xd0:
        return 'OEM'
    return 'Unknown'


def units_to_string(units_1: int, units_2: int, units_3: int) -> str:
    """Return the unit of a sensor.

    Args:
        units_1: The sensor units 1 byte, with the rate unit, the modifier
            unit and the percentage.
        units_2: The base unit type code.
        units_3: The modifier unit type code.

    Returns:
        The unit, e.g. 'degrees C', 'Volts' or '% RPM'. An empty
        string for an unspecified unit.
    """
    def name(code: int) -> str:
        if code < len(UNIT_NAMES):
            return UNIT_NAMES[code]
        return f'unit 0x{code:02x}'

    unit = '' if units_2 == 0 else name(units_2)
    modifier = (units_1 >> 1) & 0x3
    if modifier == 1:
        unit += f'/{name(units_3)}'
    elif modifier == 2:
        unit += f'*{name(units_3)}'
    rate = (units_1 >> 3) & 0x7
    if rate < len(_RATE_UNITS):
        unit += _RATE_UNITS[rate]
    if units_1 & 0x1:
        unit = f'% {unit}'.rstrip()
    return unit


class Sdr(IpmiMixin):
    """SDR repository commands, available on :class:`pyipmi.Ipmi`.

    The records are read in chunks. If the BMC cannot return the requested
    number of bytes, the chunk size is reduced and kept for the following
    records.
    """

    def __init__(self) -> None:
        """Initialize the SDR command group."""
        # read length of the SDR repository, a reduced length is kept for the
        # following records
        self._sdr_read_length = ReadLength()

    def get_sdr_repository_info(self) -> SdrRepositoryInfo:
        """Get the information about the SDR repository.

        Returns:
            The SDR repository information.
        """
        return SdrRepositoryInfo(
                self.send_message_by_name('GetSdrRepositoryInfo'))

    def get_sdr_repository_allocation_info(self) -> SdrRepositoryAllocationInfo:
        """Get the allocation information of the SDR repository.

        Returns:
            The SDR repository allocation information.
        """
        return SdrRepositoryAllocationInfo(
                self.send_message_by_name('GetSdrRepositoryAllocationInfo'))

    def reserve_sdr_repository(self) -> int:
        """Reserve the SDR repository.

        A reservation is needed to read records partially, and to delete records
        or clear the repository. It is canceled when the repository changes.

        Returns:
            The reservation ID.
        """
        rsp = self.send_message_by_name('ReserveSdrRepository')
        return rsp.reservation_id

    def _get_sdr_chunk(self, reservation_id: int, record_id: int, offset: int,
                       length: int) -> tuple[int, array]:
        req = create_request_by_name('GetSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.bytes_to_read = length

        rsp = get_sdr_chunk_helper(self.send_message, req)

        return (rsp.next_record_id, rsp.record_data)

    def get_repository_sdr(self, record_id: int,
                           reservation_id: int | None = None) -> SdrCommon:
        """Read and decode a record of the SDR repository.

        Args:
            record_id: The record ID, 0 for the first record.
            reservation_id: The reservation ID, the repository is reserved if
                None.

        Returns:
            The decoded record, its ``next_id`` is the record ID of the next
            record, 0xffff for the last record.

        Raises:
            DecodingError: The record data is invalid.
        """
        return self._get_repository_sdr(record_id, reservation_id)[0]

    def _get_repository_sdr(self, record_id: int,
                            reservation_id: int | None
                            ) -> tuple[SdrCommon, int]:
        # returns the reservation ID too, a new one if it was canceled
        (next_id, record_data, reservation_id) = get_sdr_data_helper(
                self.reserve_sdr_repository, self._get_sdr_chunk,
                record_id, reservation_id, self._sdr_read_length)
        return (SdrCommon.from_data(record_data, next_id), reservation_id)

    def sdr_repository_entries(self) -> Generator[SdrCommon, None, None]:
        """Return a generator of all records of the SDR repository.

        The repository is reserved once, and again if the reservation is
        canceled. The records are read starting with record ID 0 until the
        next record ID is 0xffff.

        Yields:
            The decoded records.
        """
        reservation_id = self.reserve_sdr_repository()
        record_id = 0

        while True:
            (s, reservation_id) = self._get_repository_sdr(record_id,
                                                           reservation_id)
            yield s
            if s.next_id == 0xffff:
                break
            record_id = s.next_id

    def get_repository_sdr_list(self,
                                reservation_id: int | None = None) -> list[SdrCommon]:
        """Return all records of the SDR repository.

        Args:
            reservation_id: Not used, the repository is reserved by
                :meth:`sdr_repository_entries`.

        Returns:
            The decoded records.
        """
        return list(self.sdr_repository_entries())

    def partial_add_sdr(self, reservation_id: int, record_id: int,
                        offset: int, progress: int, data: bytes) -> int:
        """Add a part of a record to the SDR repository.

        Args:
            reservation_id: The reservation ID.
            record_id: The record ID, 0 for the first part of a new record.
            offset: The offset of the data in the record.
            progress: 1 for the last part of the record, 0 otherwise.
            data: The part of the record data.

        Returns:
            The record ID of the added record.

        Raises:
            CompletionCodeError: The BMC rejected the request.
        """
        req = create_request_by_name('PartialAddSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.status.in_progress = progress
        req.record_data = array('B', data)
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.record_id

    def delete_sdr(self, record_id: int) -> int:
        """Delete a record of the SDR repository.

        Args:
            record_id: The record ID.

        Returns:
            The record ID of the deleted record.
        """
        reservation_id = self.reserve_sdr_repository()
        rsp = self.send_message_by_name('DeleteSdr',
                                        reservation_id=reservation_id,
                                        record_id=record_id)
        return rsp.record_id

    def _clear_sdr_repository(self, cmd: int, reservation_id: int) -> int:
        rsp = self.send_message_by_name('ClearSdrRepository',
                                        reservation_id=reservation_id,
                                        cmd=cmd)
        return rsp.status.erase_in_progress

    def clear_sdr_repository(self, retry: int = 5) -> None:
        """Delete all records of the SDR repository.

        The erase is started and polled until it is completed.

        Args:
            retry: The number of times the erase status is polled.

        Raises:
            RetryError: The erase was not completed in time.
        """
        clear_repository_helper(self.reserve_sdr_repository,
                                self._clear_sdr_repository, retry)

    def _run_initialization_agent(self, cmd: int) -> int:
        rsp = self.send_message_by_name('RunInitializationAgent', cmd=cmd)
        return rsp.status.initialization_completed

    def start_initialization_agent(self) -> None:
        """Run the initialization agent.

        The initialization agent initializes the sensors as described by the
        initialization bits of their records.
        """
        self._run_initialization_agent(RUN_INITIALIZATION_AGENT)

    def get_initialization_agent_status(self) -> int:
        """Get the status of the initialization agent.

        Returns:
            1 if the initialization is completed, 0 if it is in progress.
        """
        return self._run_initialization_agent(GET_INITIALIZATION_AGENT_STATUS)


class SdrRepositoryInfo(State):
    """The information about the SDR repository.

    The ``support_*`` attributes are the supported operations.

    Attributes:
        sdr_version (int): The SDR version, 0x51 for IPMI v1.5 and v2.0.
        record_count (int): The number of records.
        free_space (int): The free space in bytes.
        most_recent_addition (int): The time of the most recent addition.
        support_get_allocation_info (int): Get SDR Repository Allocation
            Info is supported.
        support_reserve (int): Reserve SDR Repository is supported.
        support_partial_add (int): Partial Add SDR is supported.
        support_delete (int): Delete SDR is supported.
        support_update_type (int): The supported update type, non-modal,
            modal or both.
        support_overflow_flag (int): Records could not be added because
            the repository was full.
    """

    def __init__(self, rsp: Message | None) -> None:
        """Decode the response.

        Args:
            rsp: The response of Get SDR Repository Info. Nothing is decoded
                if it is None.
        """
        if rsp:
            self._from_response(rsp)

    def _from_response(self, rsp: Message) -> None:
        self.sdr_version = rsp.sdr_version
        self.record_count = rsp.record_count
        self.free_space = rsp.free_space
        self.most_recent_addition = rsp.most_recent_addition
        self.support_get_allocation_info = rsp.support.get_allocation_info
        self.support_reserve = rsp.support.reserve
        self.support_partial_add = rsp.support.partial_add
        self.support_delete = rsp.support.delete
        self.support_update_type = rsp.support.update_type
        self.support_overflow_flag = rsp.support.overflow_flag


class SdrRepositoryAllocationInfo(State):
    """The allocation information of the SDR repository.

    Attributes:
        number_of_units (int): The number of allocation units.
        unit_size (int): The size of an allocation unit in bytes.
        free_units (int): The number of free allocation units.
        largest_free_block (int): The largest free block in allocation
            units.
        maximum_record_size (int): The maximum record size in allocation
            units.
    """

    def __init__(self, rsp: Message | None) -> None:
        """Decode the response.

        Args:
            rsp: The response of Get SDR Repository Allocation Info.
                Nothing is decoded if it is None.
        """
        if rsp:
            self._from_response(rsp)

    def _from_response(self, rsp: Message) -> None:
        self.number_of_units = rsp.number_of_units
        self.unit_size = rsp.unit_size
        self.free_units = rsp.free_units
        self.largest_free_block = rsp.largest_free_block
        self.maximum_record_size = rsp.maximum_record_size


class SdrCommon:
    """Base class of the Sensor Data Records.

    The records are decoded by :meth:`from_data`. Depending on the record
    type, a record has the record key (``owner_id``, ``owner_lun`` and the
    sensor ``number``), the entity (``entity_id`` and ``entity_instance``)
    and the device ID string (``device_id_string``,
    ``device_id_string_type`` and ``device_id_string_length``).

    Attributes:
        data (ByteSequence): The record data.
        id (int): The record ID.
        version (int): The SDR version of the record.
        type (int): The record type, one of the ``SDR_TYPE_*`` constants.
        length (int): The length of the record body in bytes.
        next_id (int): The record ID of the next record in the repository,
            only set if it is known.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        if data:
            self.data = data
            self._common_header(data)

            if hasattr(self, '_from_data'):
                self._from_data(data)

        if next_id:
            self.next_id = next_id

    def __str__(self) -> str:
        """Return the device ID string, if any, and the record data."""
        data = ' '.join(f'{b:02x}' for b in self.data)
        if hasattr(self, 'device_id_string'):
            s = f'["{self.device_id_string}"] [{data}]'
        else:
            s = f'[{data}]'
        return s

    def _common_header(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[:])
        try:
            self.id = buffer.pop_unsigned_int(2)
            self.version = buffer.pop_unsigned_int(1)
            self.type = buffer.pop_unsigned_int(1)
            self.length = buffer.pop_unsigned_int(1)
        except IndexError:
            raise DecodingError('Invalid SDR length '
                                f'({len(data):d})') from None

    def _common_record_key(self, buffer: ByteBuffer) -> None:
        self.owner_id = buffer.pop_unsigned_int(1)
        self.owner_lun = buffer.pop_unsigned_int(1) & 0x3
        self.number = buffer.pop_unsigned_int(1)

    def _entity(self, buffer: ByteBuffer) -> None:
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)

    def _device_id_string(self, buffer: ByteBuffer) -> None:
        self.device_id_string_type = (buffer[0] & 0xc0) >> 6
        self.device_id_string_length = buffer[0] & 0x3f
        field = SdrTypeLengthString(data=buffer[0:1+self.device_id_string_length])
        self.device_id_string = field.string
#        self.device_id_string = \
#            buffer.pop_string(self.device_id_string_length & 0x3f)

    @staticmethod
    def from_data(data: ByteSequence, next_id: int | None = None) -> SdrCommon:
        """Decode a record with the class for its record type.

        Records of an unknown type are decoded by
        :class:`SdrUnknownSensorRecord`.

        Args:
            data: The record data, starting with the record header.
            next_id: The record ID of the next record in the repository.

        Returns:
            The decoded record.

        Raises:
            DecodingError: The record data is too short.
        """
        sdr_type = data[3]

        cls = {
            SDR_TYPE_FULL_SENSOR_RECORD:
                SdrFullSensorRecord,
            SDR_TYPE_COMPACT_SENSOR_RECORD:
                SdrCompactSensorRecord,
            SDR_TYPE_EVENT_ONLY_SENSOR_RECORD:
                SdrEventOnlySensorRecord,
            SDR_TYPE_FRU_DEVICE_LOCATOR_RECORD:
                SdrFruDeviceLocator,
            SDR_TYPE_MANAGEMENT_CONTROLLER_DEVICE_LOCATOR_RECORD:
                SdrManagementControllerDeviceLocator,
            SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD:
                SdrManagementControllerConfirmationRecord,
            SDR_TYPE_OEM_SENSOR_RECORD:
                SdrOEMSensorRecord,
        }.get(sdr_type, SdrUnknownSensorRecord)

        return cls(data, next_id)


###
# SDR type 0x01
##################################################
class SdrFullSensorRecord(SdrCommon):
    """A Full Sensor Record (type 0x01).

    The record describes an analog sensor and the conversion of its raw
    readings: ``y = L[(M * x + B * 10^K1) * 10^K2]`` with the linearization
    ``L``. The ``DATA_FMT_*`` constants are the analog data formats.

    Attributes:
        initialization (list[str]): The sensor initialization settings:
            ``'scanning'``, ``'events'``, ``'thresholds'``,
            ``'hysteresis'``, ``'type'``, ``'default_event_generation'``
            and ``'default_scanning'``.
        capabilities (list[str]): The sensor capabilities:
            ``'ignore_sensor'``, ``'auto_rearm'``, the hysteresis support
            (``'hysteresis_*'``) and the threshold support
            (``'threshold_*'``).
        sensor_type_code (int): The sensor type.
        event_reading_type_code (int): The event/reading type.
        assertion_mask (int): The assertion event mask.
        deassertion_mask (int): The deassertion event mask.
        discrete_reading_mask (int): The discrete reading mask.
        units_1 (int): The sensor units 1 byte.
        units_2 (int): The base unit type code.
        units_3 (int): The modifier unit type code.
        analog_data_format (int): The analog data format, one of the
            ``DATA_FMT_*`` constants.
        rate_unit (int): The rate unit.
        modifier_unit (int): How the modifier unit is applied.
        percentage (int): 1 if the reading is a percentage.
        linearization (int): The linearization, one of the ``L_*``
            constants.
        m (int): The conversion factor M.
        tolerance (int): The tolerance in +/- half raw counts.
        b (int): The conversion offset B.
        accuracy (int): The accuracy in 0.01 percent units.
        accuracy_exp (int): The accuracy exponent.
        k1 (int): The exponent of B.
        k2 (int): The result exponent.
        analog_characteristic (list[str]): The analog characteristics that
            are specified: ``'nominal_reading'``, ``'normal_max'`` and
            ``'normal_min'``.
        nominal_reading (int): The nominal raw reading.
        normal_maximum (int): The normal maximum raw reading.
        normal_minimum (int): The normal minimum raw reading.
        sensor_maximum_reading (int): The maximum raw reading.
        sensor_minimum_reading (int): The minimum raw reading.
        threshold (dict[str, int]): The raw thresholds, with the keys
            ``'unr'``, ``'ucr'``, ``'unc'``, ``'lnr'``, ``'lcr'`` and
            ``'lnc'`` (upper/lower non-recoverable, critical and
            non-critical).
        hysteresis (dict[str, int]): The raw hysteresis values, with the
            keys ``'positive_going'`` and ``'negative_going'``.
        oem (int): The OEM byte.
    """

    DATA_FMT_UNSIGNED = 0
    DATA_FMT_1S_COMPLEMENT = 1
    DATA_FMT_2S_COMPLEMENT = 2
    DATA_FMT_NONE = 3

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return the device ID string, the entity and the record data."""
        data = ' '.join(f'{b:02x}' for b in self.data)
        s = (f'["{self.device_id_string}"] '
             f'[{self.entity_id}:{self.entity_instance}] [{data}]')
        return s

    def convert_sensor_raw_to_value(self, raw: int | None) -> float | None:
        """Convert a raw sensor reading to the value in the sensor unit.

        Args:
            raw: The raw reading, e.g. of :meth:`pyipmi.Ipmi.get_sensor_reading`.

        Returns:
            The converted value, None if ``raw`` is None.

        Raises:
            DecodingError: The linearization is unknown.
        """
        if raw is None:
            return None
        fmt = self.analog_data_format
        if (fmt == self.DATA_FMT_1S_COMPLEMENT):
            if raw & 0x80:
                raw = -((raw & 0x7f) ^ 0x7f)
        elif (fmt == self.DATA_FMT_2S_COMPLEMENT):
            if raw & 0x80:
                raw = -((raw & 0x7f) ^ 0x7f) - 1

        return self.lin((self.m * float(raw)
                         + (self.b * 10**self.k1)) * 10**self.k2)

    def convert_sensor_value_to_raw(self, value: float) -> int:
        """Convert a value in the sensor unit to the raw sensor value.

        This is the inverse of :meth:`convert_sensor_raw_to_value`, e.g. to set
        a threshold. The value is rounded to the next raw value.

        Args:
            value: The value in the sensor unit.

        Returns:
            The raw value.

        Raises:
            NotImplementedError: The sensor is not linear.
            ValueError: The value is out of the range of the raw values.
        """
        linearization = self.linearization & 0x7f

        if linearization is not L_LINEAR:
            raise NotImplementedError()

        # inverse of y = (M * x + B * 10^K1) * 10^K2
        raw = ((float(value) * 10**(-1 * self.k2))
               - (self.b * 10**self.k1)) / self.m

        raw = int(round(raw))

        # the sign of the raw value depends on the offset B and not only on
        # the sign of the given value. Check the range before the conversion,
        # it maps any negative value into 0x80..0xff.
        fmt = self.analog_data_format
        if (fmt == self.DATA_FMT_1S_COMPLEMENT):
            if raw < -127 or raw > 127:
                raise ValueError()
            if raw < 0:
                raw = (-raw ^ 0x7f) | 0x80
        elif (fmt == self.DATA_FMT_2S_COMPLEMENT):
            if raw < -128 or raw > 127:
                raise ValueError()
            if raw < 0:
                raw = (-(raw + 1) ^ 0x7f) | 0x80
        elif raw < 0 or raw > 0xff:
            raise ValueError()

        return raw

    @property
    def lin(self) -> Callable[[float], float]:
        """The linearization function of the sensor.

        Raises:
            DecodingError: The linearization is unknown.
        """
        try:
            return {
                L_LN: math.log,
                L_LOG: lambda x: math.log(x, 10),
                L_LOG2: lambda x: math.log(x, 2),
                L_E: math.exp,
                L_EXP10: lambda x: math.pow(10, x),
                L_EXP2: lambda x: math.pow(2, x),
                L_1_X: lambda x: 1.0 / x,
                L_SQR: lambda x: math.pow(x, 2),
                L_CUBE: lambda x: math.pow(x, 3),
                L_SQRT: math.sqrt,
                L_CUBERT: lambda x: math.pow(x, 1.0/3),
                L_LINEAR: lambda x: x,
            }[self.linearization & 0x7f]
        except KeyError:
            linearization = self.linearization & 0x7f
            raise errors.DecodingError('unknown linearization '
                                       f'{linearization:d}') from None

    @staticmethod
    def _convert_complement(value: int, size: int) -> int:
        if (value & (1 << (size - 1))):
            value = -(1 << size) + value
        return value

    def _decode_capabilities(self, capabilities: int) -> None:
        self.capabilities = []

        # ignore sensor
        if capabilities & 0x80:
            self.capabilities.append('ignore_sensor')
        # sensor auto re-arm support
        if capabilities & 0x40:
            self.capabilities.append('auto_rearm')
        # sensor hysteresis support
        HYSTERESIS_MASK = 0x30
        HYSTERESIS_IS_NOT_SUPPORTED = 0x00
        HYSTERESIS_IS_READABLE = 0x10
        HYSTERESIS_IS_READ_AND_SETTABLE = 0x20
        HYSTERESIS_IS_FIXED = 0x30
        if capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_NOT_SUPPORTED:
            self.capabilities.append('hysteresis_not_supported')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_READABLE:
            self.capabilities.append('hysteresis_readable')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_READ_AND_SETTABLE:
            self.capabilities.append('hysteresis_read_and_setable')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_FIXED:
            self.capabilities.append('hysteresis_fixed')
        # sensor threshold support
        THRESHOLD_MASK = 0x0C
        THRESHOLD_IS_NOT_SUPPORTED = 0x00
        THRESHOLD_IS_READABLE = 0x04
        THRESHOLD_IS_READ_AND_SETTABLE = 0x08
        THRESHOLD_IS_FIXED = 0x0C
        if capabilities & THRESHOLD_MASK == THRESHOLD_IS_NOT_SUPPORTED:
            self.capabilities.append('threshold_not_supported')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_READABLE:
            self.capabilities.append('threshold_readable')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_READ_AND_SETTABLE:
            self.capabilities.append('threshold_read_and_setable')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_FIXED:
            self.capabilities.append('threshold_fixed')
        # sensor event message control support
        if (capabilities & 0x03) == 0:
            pass
        if (capabilities & 0x03) == 1:
            pass
        if (capabilities & 0x03) == 2:
            pass
        if (capabilities & 0x03) == 3:
            pass

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])
        # record key bytes
        self._common_record_key(buffer.pop_slice(3))
        # record body bytes
        self._entity(buffer.pop_slice(2))

        # byte 11
        initialization = buffer.pop_unsigned_int(1)
        self.initialization = []
        if initialization & 0x40:
            self.initialization.append('scanning')
        if initialization & 0x20:
            self.initialization.append('events')
        if initialization & 0x10:
            self.initialization.append('thresholds')
        if initialization & 0x08:
            self.initialization.append('hysteresis')
        if initialization & 0x04:
            self.initialization.append('type')
        if initialization & 0x02:
            self.initialization.append('default_event_generation')
        if initialization & 0x01:
            self.initialization.append('default_scanning')

        # byte 12 - sensor capabilities
        self._decode_capabilities(buffer.pop_unsigned_int(1))

        self.sensor_type_code = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.assertion_mask = buffer.pop_unsigned_int(2)
        self.deassertion_mask = buffer.pop_unsigned_int(2)
        self.discrete_reading_mask = buffer.pop_unsigned_int(2)
        # byte 21, 22, 23
        self.units_1 = buffer.pop_unsigned_int(1)
        self.units_2 = buffer.pop_unsigned_int(1)
        self.units_3 = buffer.pop_unsigned_int(1)
        self.analog_data_format = (self.units_1 >> 6) & 0x3
        self.rate_unit = (self.units_1 >> 3) & 0x7
        self.modifier_unit = (self.units_1 >> 1) & 0x3
        self.percentage = self.units_1 & 0x1
        # byte 24
        self.linearization = buffer.pop_unsigned_int(1) & 0x7f
        # byte 25, 26
        m = buffer.pop_unsigned_int(1)
        m_tol = buffer.pop_unsigned_int(1)
        self.m = (m & 0xff) | ((m_tol & 0xc0) << 2)
        # NAC: Bug fix.  Upstream did not properly account for
        # 'M' being a twos complement value.
        self.m = self._convert_complement(self.m, 10)
        self.tolerance = (m_tol & 0x3f)

        # byte 27, 28, 29
        b = buffer.pop_unsigned_int(1)
        b_acc = buffer.pop_unsigned_int(1)
        acc_accexp = buffer.pop_unsigned_int(1)
        self.b = (b & 0xff) | ((b_acc & 0xc0) << 2)
        self.b = self._convert_complement(self.b, 10)
        self.accuracy = (b_acc & 0x3f) | ((acc_accexp & 0xf0) << 2)
        self.accuracy_exp = (acc_accexp & 0x0c) >> 2
        # byte 30
        rexp_bexp = buffer.pop_unsigned_int(1)
        self.k2 = (rexp_bexp & 0xf0) >> 4
        # convert 2s complement
        self.k2 = self._convert_complement(self.k2, 4)

        self.k1 = rexp_bexp & 0x0f
        # convert 2s complement
        self.k1 = self._convert_complement(self.k1, 4)

        # byte 31
        analog_characteristics = buffer.pop_unsigned_int(1)
        self.analog_characteristic = []
        if analog_characteristics & 0x01:
            self.analog_characteristic.append('nominal_reading')
        if analog_characteristics & 0x02:
            self.analog_characteristic.append('normal_max')
        if analog_characteristics & 0x04:
            self.analog_characteristic.append('normal_min')

        self.nominal_reading = buffer.pop_unsigned_int(1)
        self.normal_maximum = buffer.pop_unsigned_int(1)
        self.normal_minimum = buffer.pop_unsigned_int(1)
        self.sensor_maximum_reading = buffer.pop_unsigned_int(1)
        self.sensor_minimum_reading = buffer.pop_unsigned_int(1)
        self.threshold = {}
        self.threshold['unr'] = buffer.pop_unsigned_int(1)
        self.threshold['ucr'] = buffer.pop_unsigned_int(1)
        self.threshold['unc'] = buffer.pop_unsigned_int(1)
        self.threshold['lnr'] = buffer.pop_unsigned_int(1)
        self.threshold['lcr'] = buffer.pop_unsigned_int(1)
        self.threshold['lnc'] = buffer.pop_unsigned_int(1)
        self.hysteresis = {}
        self.hysteresis['positive_going'] = buffer.pop_unsigned_int(1)
        self.hysteresis['negative_going'] = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(2)
        self.oem = buffer.pop_unsigned_int(1)
        self._device_id_string(buffer)


###
# SDR type 0x02
##################################################
class SdrCompactSensorRecord(SdrCommon):
    """A Compact Sensor Record (type 0x02).

    The record describes a sensor without conversion of its readings,
    typically a discrete sensor.

    Attributes:
        sensor_initialization (int): The sensor initialization byte.
        capabilities (int): The sensor capabilities byte.
        sensor_type_code (int): The sensor type.
        event_reading_type_code (int): The event/reading type.
        assertion_mask (int): The assertion event mask.
        deassertion_mask (int): The deassertion event mask.
        discrete_reading_mask (int): The discrete reading mask.
        units_1 (int): The sensor units 1 byte.
        units_2 (int): The base unit type code.
        units_3 (int): The modifier unit type code.
        record_sharing (int): The sensor record sharing bytes.
        positive_going_hysteresis (int): The positive going hysteresis.
        negative_going_hysteresis (int): The negative going hysteresis.
        oem (int): The OEM byte.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return the device ID string and the record data."""
        data = ' '.join(f'{b:02x}' for b in self.data)
        s = f'["{self.device_id_string}"] [{data}]'
        return s

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])

        # record key bytes
        self._common_record_key(buffer.pop_slice(3))

        # record body bytes
        self._entity(buffer.pop_slice(2))

        self.sensor_initialization = buffer.pop_unsigned_int(1)
        self.capabilities = buffer.pop_unsigned_int(1)
        self.sensor_type_code = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.assertion_mask = buffer.pop_unsigned_int(2)
        self.deassertion_mask = buffer.pop_unsigned_int(2)
        self.discrete_reading_mask = buffer.pop_unsigned_int(2)
        self.units_1 = buffer.pop_unsigned_int(1)
        self.units_2 = buffer.pop_unsigned_int(1)
        self.units_3 = buffer.pop_unsigned_int(1)
        self.record_sharing = buffer.pop_unsigned_int(2)
        self.positive_going_hysteresis = buffer.pop_unsigned_int(1)
        self.negative_going_hysteresis = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(3)
        self.oem = buffer.pop_unsigned_int(1)
        self._device_id_string(buffer)


###
# SDR type 0x03
##################################################
class SdrEventOnlySensorRecord(SdrCommon):
    """An Event-Only Sensor Record (type 0x03).

    The record describes a sensor that only generates events and cannot
    be read.

    Attributes:
        sensor_type (int): The sensor type.
        event_reading_type_code (int): The event/reading type.
        record_sharing (int): The sensor record sharing bytes.
        oem (int): The OEM byte.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return that the record is not formatted yet."""
        return 'Not supported yet.'

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])

        # record key bytes
        self._common_record_key(buffer.pop_slice(3))

        # record body bytes
        self._entity(buffer.pop_slice(2))

        self.sensor_type = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.record_sharing = buffer.pop_unsigned_int(2)
        self.reserved = buffer.pop_unsigned_int(1)
        self.oem = buffer.pop_unsigned_int(1)
        self._device_id_string(buffer)


###
# SDR type 0x11
##################################################
class SdrFruDeviceLocator(SdrCommon):
    """A FRU Device Locator Record (type 0x11).

    The record describes where the FRU inventory data of a device is
    accessed.

    Attributes:
        device_access_address (int): The 7-bit address of the controller
            that gives access to the FRU device.
        fru_device_id (int): The FRU device ID, or the 7-bit I2C address
            of a non-intelligent FRU device.
        logical_physical (int): The logical/physical FRU device byte.
        channel_number (int): The channel number byte.
        device_type (int): The device type.
        device_type_modifier (int): The device type modifier.
        oem (int): The OEM byte.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return the device ID string and the record data."""
        data = ' '.join(f'{b:02x}' for b in self.data)
        s = f'["{self.device_id_string}"] [{data}]'
        return s

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])
        self.device_access_address = buffer.pop_unsigned_int(1) >> 1
        self.fru_device_id = buffer.pop_unsigned_int(1)
        self.logical_physical = buffer.pop_unsigned_int(1)
        self.channel_number = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(1)
        self.device_type = buffer.pop_unsigned_int(1)
        self.device_type_modifier = buffer.pop_unsigned_int(1)
        self._entity(buffer.pop_slice(2))
        self.oem = buffer.pop_unsigned_int(1)
        self._device_id_string(buffer)


###
# SDR type 0x12
##################################################
class SdrManagementControllerDeviceLocator(SdrCommon):
    """A Management Controller Device Locator Record (type 0x12).

    The record describes a management controller on the IPMB.

    Attributes:
        device_slave_address (int): The 7-bit address of the controller.
        channel_number (int): The channel number.
        power_state_notification (int): The power state notification and
            global initialization byte.
        global_initialization (int): Always 0, it is part of
            ``power_state_notification``.
        device_capabilities (int): The device capabilities byte.
        oem (int): The OEM byte.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(
                data, next_id)

    def __str__(self) -> str:
        """Return the device ID string and the record data."""
        data = ' '.join(f'{b:02x}' for b in self.data)
        s = f'["{self.device_id_string}"] [{data}]'
        return s

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])
        self.device_slave_address = buffer.pop_unsigned_int(1) >> 1
        self.channel_number = buffer.pop_unsigned_int(1) & 0xf
        self.power_state_notification = buffer.pop_unsigned_int(1)
        self.global_initialization = 0
        self.device_capabilities = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(3)
        self._entity(buffer.pop_slice(2))
        self.oem = buffer.pop_unsigned_int(1)
        self._device_id_string(buffer)


###
# SDR type 0x13
##################################################
class SdrManagementControllerConfirmationRecord(SdrCommon):
    """A Management Controller Confirmation Record (type 0x13).

    The record confirms that a management controller was detected.

    Attributes:
        device_slave_address (int): The 7-bit address of the controller.
        device_id (int): The device ID.
        channel_number (int): The channel number.
        device_revision (int): The device revision.
        firmware_revision_1 (int): The major firmware revision.
        firmware_revision_2 (int): The minor firmware revision, BCD
            encoded.
        ipmi_version (int): The IPMI version, BCD encoded with the minor
            version in the upper nibble.
        manufacturer_id (int): The manufacturer ID.
        manufacturer_name (str | None): The name of a well known
            manufacturer, see :func:`pyipmi.constants.manufacturer_name`.
            None for other manufacturers.
        product_id (int): The product ID.
        device_guid (int): The device GUID.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(
                data, next_id)

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])
        self.device_slave_address = buffer.pop_unsigned_int(1) >> 1
        self.device_id = buffer.pop_unsigned_int(1)
        tmp = buffer.pop_unsigned_int(1)
        self.channel_number = (tmp >> 4) & 0xf
        self.device_revision = tmp & 0xf
        self.firmware_revision_1 = buffer.pop_unsigned_int(1) & 0x7f
        self.firmware_revision_2 = buffer.pop_unsigned_int(1)
        self.ipmi_version = buffer.pop_unsigned_int(1)
        self.manufacturer_id = buffer.pop_unsigned_int(3) & 0xfffff
        self.manufacturer_name = manufacturer_name(self.manufacturer_id)
        self.product_id = buffer.pop_unsigned_int(2)
        self.device_guid = buffer.pop_unsigned_int(16)


###
# SDR type 0xC0
##################################################
class SdrOEMSensorRecord(SdrCommon):
    """An OEM Record (type 0xC0).

    The record has no record key, its data starts with the manufacturer ID,
    followed by the OEM data.

    Attributes:
        manufacturer_id (int | None): The manufacturer ID, None if the
            record is too short for it.
        manufacturer_name (str | None): The name of a well known
            manufacturer, see :func:`pyipmi.constants.manufacturer_name`.
        oem_data (bytes): The OEM data after the manufacturer ID.
    """

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return that the record is not formatted yet."""
        return 'Not supported yet.'

    def _from_data(self, data: ByteSequence) -> None:
        buffer = ByteBuffer(data[5:])

        # no record key, the manufacturer ID, LS byte first
        self.manufacturer_id: int | None = None
        self.manufacturer_name: str | None = None
        if len(buffer) >= 3:
            self.manufacturer_id = buffer.pop_unsigned_int(3)
            self.manufacturer_name = manufacturer_name(self.manufacturer_id)
        self.oem_data = buffer.tobytes()


# Any SDR type not known or not implemented
class SdrUnknownSensorRecord(SdrCommon):
    """A record of a type that is not decoded, only its header is."""

    def __init__(self, data: ByteSequence | None = None,
                 next_id: int | None = None) -> None:
        """Decode the record.

        Args:
            data: The record data, starting with the record header. Nothing
                is decoded if it is None or empty.
            next_id: The record ID of the next record in the repository.

        Raises:
            DecodingError: The record data is too short.
        """
        super().__init__(data, next_id)

    def __str__(self) -> str:
        """Return that the record is not formatted yet."""
        return 'Not supported yet.'
