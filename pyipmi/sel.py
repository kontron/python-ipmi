
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

"""System Event Log (SEL) commands.

The System Event Log of the BMC stores the event messages of the system,
e.g. a sensor that crossed a threshold. Each entry is a 16 byte record.

The commands are the methods of :class:`Sel`, which are available on
:class:`pyipmi.Ipmi`. An entry is decoded by :class:`SelEntry`.

Example:
    Print the sensor events of the SEL::

        for entry in ipmi.sel_entries():
            if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
                print(entry.timestamp, entry.sensor_type,
                      entry.sensor_number, entry.event_data)
"""

from __future__ import annotations

from array import array
from collections.abc import Generator
from datetime import datetime, timezone

from .errors import CompletionCodeError, DecodingError
from .utils import check_completion_code, ByteBuffer, ByteSequence
from .msgs import create_request_by_name, Message
from .msgs import constants
from .event import EVENT_ASSERTION, EVENT_DEASSERTION
from .sensor import (EVENT_READING_TYPE_CODE_THRESHOLD,
                     event_offset_to_string, sensor_type_to_string)

from .helper import clear_repository_helper
from .state import State
from .mixin import IpmiMixin


# The timestamp of an event before the SEL time was set is the time since
# the initialization of the BMC (IPMI v2.0 section 37.1)
TIMESTAMP_UNSPECIFIED = 0xffffffff
TIMESTAMP_PRE_INIT_MAX = 0x20000000


class Sel(IpmiMixin):
    """SEL commands, available on :class:`pyipmi.Ipmi`."""

    def get_sel_entries_count(self) -> int:
        """Return the number of entries in the SEL.

        Returns:
            The number of entries.
        """
        info = SelInfo(self.send_message_by_name('GetSelInfo'))
        return info.entries

    def get_sel_reservation_id(self) -> int:
        """Reserve the SEL.

        A reservation is needed to read entries partially, and to delete
        entries or clear the SEL. It is canceled when the SEL changes.

        Returns:
            The reservation ID.
        """
        rsp = self.send_message_by_name('ReserveSel')
        return rsp.reservation_id

    def _clear_sel(self, cmd: int, reservation: int) -> int:
        rsp = self.send_message_by_name('ClearSel',
                                        reservation_id=reservation,
                                        cmd=cmd)
        return rsp.status.erase_in_progress

    def clear_sel(self, retry: int = 5) -> None:
        """Delete all entries of the SEL.

        The erase is started and polled until it is completed.

        Args:
            retry: The number of times the erase status is polled.

        Raises:
            RetryError: The erase was not completed in time.
        """
        clear_repository_helper(self.get_sel_reservation_id,
                                self._clear_sel, retry)

    def delete_sel_entry(self, record_id: int, reservation: int = 0) -> int:
        """Delete an entry of the SEL.

        Args:
            record_id: The record ID of the entry.
            reservation: The reservation ID of :meth:`get_sel_reservation_id`.

        Returns:
            The record ID of the deleted entry.
        """
        rsp = self.send_message_by_name('DeleteSelEntry',
                                        reservation_id=reservation,
                                        record_id=record_id)
        return rsp.record_id

    def get_and_clear_sel_entry(self, record_id: int) -> SelEntry:
        """Read and delete an entry of the SEL.

        The SEL is reserved for both commands, so no other entry is deleted
        if the SEL changes in between. The commands are repeated with a new
        reservation if the reservation is canceled.

        Args:
            record_id: The record ID of the entry.

        Returns:
            The decoded entry.

        Raises:
            CompletionCodeError: The BMC rejected a request.
        """
        while True:
            reservation = self.get_sel_reservation_id()
            try:
                sel_entry, _ = self.get_sel_entry(record_id, reservation)
            except CompletionCodeError as e:
                if e.cc == constants.CC_RES_CANCELED:
                    continue
                else:
                    raise
            try:
                self.delete_sel_entry(record_id, reservation)
            except CompletionCodeError as e:
                if e.cc == constants.CC_RES_CANCELED:
                    continue
                else:
                    raise
            return sel_entry

    def get_sel_entry(self, record_id: int,
                      reservation: int = 0) -> tuple[SelEntry, int]:
        """Read and decode an entry of the SEL.

        The entry is read at once. If the BMC cannot return the whole entry,
        it is read in parts.

        Args:
            record_id: The record ID of the entry, 0 for the first entry.
            reservation: The reservation ID of :meth:`get_sel_reservation_id`,
                it is needed to read the entry in parts.

        Returns:
            A tuple of the decoded entry and the record ID of the next
            entry, 0xffff for the last entry.

        Raises:
            CompletionCodeError: The BMC rejected a request.
            DecodingError: The entry is invalid.
        """
        ENTIRE_RECORD = 0xff
        req = create_request_by_name('GetSelEntry')
        req.reservation_id = reservation
        req.record_id = record_id
        req.offset = 0
        self.max_req_len = ENTIRE_RECORD

        record_data = ByteBuffer()

        while True:
            req.length = self.max_req_len
            if (self.max_req_len != 0xff
                    and (req.offset + req.length) > 16):
                req.length = 16 - req.offset

            rsp = self.send_message(req)
            if rsp.completion_code == constants.CC_CANT_RET_NUM_REQ_BYTES:
                if self.max_req_len == 0xff:
                    self.max_req_len = 16
                else:
                    self.max_req_len -= 1
                continue
            else:
                check_completion_code(rsp.completion_code)

            record_data.extend(rsp.record_data)
            req.offset = len(record_data)

            if len(record_data) >= 16:
                break

        return (SelEntry(record_data), rsp.next_record_id)

    def sel_entries(self) -> Generator[SelEntry, None, None]:
        """Return a generator of all entries of the SEL.

        The SEL is reserved once. The entries are read starting with the
        first entry until the next record ID is 0xffff.

        Yields:
            The decoded entries.
        """
        START_SEL_RECORD_ID = 0
        END_SEL_RECORD_ID = 0xffff
        if self.get_sel_entries_count() == 0:
            return

        reservation_id = self.get_sel_reservation_id()
        next_record_id = START_SEL_RECORD_ID
        while True:
            (sel_entry, next_record_id) = self.get_sel_entry(next_record_id,
                                                             reservation_id)
            yield sel_entry
            if next_record_id == END_SEL_RECORD_ID:
                break

    def get_sel_entries(self) -> list[SelEntry]:
        """Return all entries of the SEL.

        Returns:
            The decoded entries.
        """
        return list(self.sel_entries())


class SelInfo(State):
    """The information about the SEL.

    Attributes:
        version (int): The SEL version, 0x51 for IPMI v1.5 and v2.0.
        entries (int): The number of entries.
        free_bytes (int): The free space in bytes.
        most_recent_addition (int): The time of the most recent addition.
        most_recent_erase (int): The time of the most recent erase.
        operation_support (list[str]): The supported operations
            (``'get_sel_allocation_info'``, ``'reserve_sel'``,
            ``'partial_add_sel_entry'`` and ``'delete_sel'``), and
            ``'overflow_flag'`` if events were dropped because the SEL was
            full.
    """

    def _from_response(self, rsp: Message) -> None:
        self.version = rsp.version
        self.entries = rsp.entries
        self.free_bytes = rsp.free_bytes
        self.most_recent_addition = rsp.most_recent_addition
        self.most_recent_erase = rsp.most_recent_erase
        self.operation_support = []
        if rsp.operation_support.get_sel_allocation_info:
            self.operation_support.append('get_sel_allocation_info')
        if rsp.operation_support.reserve_sel:
            self.operation_support.append('reserve_sel')
        if rsp.operation_support.partial_add_sel_entry:
            self.operation_support.append('partial_add_sel_entry')
        if rsp.operation_support.delete_sel:
            self.operation_support.append('delete_sel')
        if rsp.operation_support.overflow_flag:
            self.operation_support.append('overflow_flag')


class SelEntry(State):
    """An entry of the SEL.

    The record type is ``TYPE_SYSTEM_EVENT`` or in one of the OEM ranges
    ``TYPE_OEM_TIMESTAMPED_RANGE`` and ``TYPE_OEM_NON_TIMESTAMPED_RANGE``.

    Note:
        All entries are decoded with the layout of a system event record.
        The fields after the record type of an OEM entry are OEM data.

    Attributes:
        data (ByteSequence): The record data.
        record_id (int): The record ID.
        type (int): The record type.
        timestamp (int): The time the event was logged, in seconds since
            1970-01-01.
        generator_id (int): The ID of the device that generated the event.
        evm_rev (int): The event message format version.
        sensor_type (int): The sensor type, see the ``SENSOR_TYPE_*``
            constants of :mod:`pyipmi.sensor`.
        sensor_number (int): The number of the sensor that generated the
            event.
        event_direction (int): ``EVENT_ASSERTION`` or
            ``EVENT_DEASSERTION`` of :mod:`pyipmi.event`.
        event_type (int): The event/reading type.
        event_data (list[int]): The event data bytes 1 - 3.
        event_offset (int): The event offset of a generic or sensor-specific
            event, bits 3:0 of the event data byte 1.
    """

    TYPE_SYSTEM_EVENT = 0x02
    TYPE_OEM_TIMESTAMPED_RANGE = list(range(0xc0, 0xe0))
    TYPE_OEM_NON_TIMESTAMPED_RANGE = list(range(0xe0, 0x100))

    def __init__(self, data: ByteSequence | None = None) -> None:
        """Decode the entry.

        Args:
            data: The 16 bytes of the record. Nothing is decoded if it is
                None or empty.

        Raises:
            DecodingError: The record is not 16 bytes long or its type is
                unknown.
        """
        # a SEL entry is decoded from the record data, not from a response
        super().__init__()
        if data:
            self._from_data(data)

    def __str__(self) -> str:
        """Return the fields of the entry as multi-line string."""
        raw = f"[{' '.join([f'0x{b:02x}' for b in self.data])}]"
        string = []
        string.append(f'SEL Record ID 0x{self.record_id:04x}')
        string.append(f'  Raw: {raw}')
        string.append(f'  Type: {self.type:d}')
        string.append(f'  Timestamp: {self.timestamp:d}')
        string.append(f'  Generator: {self.generator_id:d}')
        string.append(f'  EvM rev: {self.evm_rev:d}')
        string.append(f'  Sensor Type: 0x{self.sensor_type:02x}')
        string.append(f'  Sensor Number: {self.sensor_number:d}')
        string.append(f'  Event Direction: {self.event_direction:d}')
        string.append(f'  Event Type: 0x{self.event_type:02x}')
        string.append(f"  Event Data: {array('B', self.event_data).tolist()}")
        return "\n".join(string)

    @staticmethod
    def type_to_string(entry_type: int) -> str | None:
        """Return the name of a record type.

        Args:
            entry_type: The record type.

        Returns:
            The name of the record type, None for an unknown type.
        """
        string = None
        if entry_type == SelEntry.TYPE_SYSTEM_EVENT:
            string = 'System Event'
        elif entry_type in SelEntry.TYPE_OEM_TIMESTAMPED_RANGE:
            string = f'OEM timestamped (0x{entry_type:02x})'
        elif entry_type in SelEntry.TYPE_OEM_NON_TIMESTAMPED_RANGE:
            string = f'OEM non-timestamped (0x{entry_type:02x})'
        return string

    @staticmethod
    def sensor_type_to_string(sensor_type: int) -> str:
        """Return the name of a sensor type.

        See :func:`pyipmi.sensor.sensor_type_to_string`.
        """
        return sensor_type_to_string(sensor_type)

    def is_timestamped(self) -> bool:
        """Return True if the entry has a timestamp."""
        return self.type not in self.TYPE_OEM_NON_TIMESTAMPED_RANGE

    def timestamp_to_string(self) -> str:
        """Return the timestamp as date and time (UTC).

        Returns:
            The date and time as 'YYYY-MM-DD HH:MM:SS', 'Pre-Init <n>s' for
            a time since the initialization of the BMC, or 'Unspecified'.
        """
        if (not self.is_timestamped()
                or self.timestamp == TIMESTAMP_UNSPECIFIED):
            return 'Unspecified'
        if self.timestamp <= TIMESTAMP_PRE_INIT_MAX:
            return f'Pre-Init {self.timestamp:d}s'
        time = datetime.fromtimestamp(self.timestamp, timezone.utc)
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def generator_to_string(self) -> str:
        """Return the generator ID as IPMB address or software ID.

        Returns:
            E.g. 'IPMB 0x20 LUN 0 channel 0' or 'Software 0x01'.
        """
        address = self.generator_id & 0xff
        lun = (self.generator_id >> 8) & 0x3
        channel = (self.generator_id >> 12) & 0xf
        if address & 0x1:
            string = f'Software 0x{address >> 1:02x}'
        else:
            string = f'IPMB 0x{address:02x} LUN {lun:d}'
        if channel:
            string += f' channel {channel:d}'
        return string

    def event_to_string(self) -> str:
        """Return the description of the event.

        The event offset is looked up in the generic or sensor-specific
        event offsets of the IPMI specification.

        Returns:
            The description of the event, or the event/reading type and
            offset as hex numbers if they are unknown.
        """
        string = event_offset_to_string(self.event_type, self.sensor_type,
                                        self.event_offset)
        if string is None:
            if 0x70 <= self.event_type <= 0x7f:
                string = (f'OEM Event Type 0x{self.event_type:02x} '
                          f'Offset 0x{self.event_offset:02x}')
            else:
                string = (f'Event Type 0x{self.event_type:02x} '
                          f'Offset 0x{self.event_offset:02x}')
        return string

    def direction_to_string(self) -> str:
        """Return 'Asserted' or 'Deasserted'."""
        if self.event_direction == EVENT_DEASSERTION:
            return 'Deasserted'
        return 'Asserted'

    def threshold_event_values(self) -> tuple[int | None, int | None]:
        """Return the raw values of a threshold event.

        The event data bytes 2 and 3 can hold the trigger reading and the
        trigger threshold, as indicated in the event data byte 1.

        Returns:
            A tuple of the raw trigger reading and the raw threshold value,
            None if a value is not given or the event is no threshold event.
        """
        if self.event_type != EVENT_READING_TYPE_CODE_THRESHOLD:
            return (None, None)
        reading = None
        threshold = None
        if (self.event_data[0] >> 6) & 0x3 == 0x1:
            reading = self.event_data[1]
        if (self.event_data[0] >> 4) & 0x3 == 0x1:
            threshold = self.event_data[2]
        return (reading, threshold)

    def _from_data(self, data: ByteSequence) -> None:
        if len(data) != 16:
            raise DecodingError(f'Invalid SEL record length ({len(data):d})')

        self.data = data

        # pop will change data, therefore copy it
        buffer = ByteBuffer(data)

        self.record_id = buffer.pop_unsigned_int(2)
        self.type = buffer.pop_unsigned_int(1)
        if (self.type != self.TYPE_SYSTEM_EVENT
                and self.type not in self.TYPE_OEM_TIMESTAMPED_RANGE
                and self.type not in self.TYPE_OEM_NON_TIMESTAMPED_RANGE):
            raise DecodingError(f'Unknown SEL type (0x{self.type:02x})')
        self.timestamp = buffer.pop_unsigned_int(4)
        self.generator_id = buffer.pop_unsigned_int(2)
        self.evm_rev = buffer.pop_unsigned_int(1)
        self.sensor_type = buffer.pop_unsigned_int(1)
        self.sensor_number = buffer.pop_unsigned_int(1)
        event_desc = buffer.pop_unsigned_int(1)
        if event_desc & 0x80:
            self.event_direction = EVENT_DEASSERTION
        else:
            self.event_direction = EVENT_ASSERTION
        self.event_type = event_desc & 0x7f
        self.event_data = [buffer.pop_unsigned_int(1) for _ in range(3)]
        self.event_offset = self.event_data[0] & 0x0f
