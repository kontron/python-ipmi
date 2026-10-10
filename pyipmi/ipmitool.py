#!/usr/bin/env python3

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

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import pprint
import sys
import textwrap
import time
import traceback
from array import array
from datetime import datetime, timezone
from collections.abc import Callable, Iterator
from typing import Any

import pyipmi
import pyipmi.interfaces
import pyipmi.logger
from pyipmi.utils import py3_array_tobytes


def auto_int(value: str) -> int:
    """Argument type for numbers, decimal or with 0x prefix."""
    return int(value, 0)


def ipv4_address(value: str) -> str:
    """Argument type for IPv4 addresses, xxx.xxx.xxx.xxx."""
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise argparse.ArgumentTypeError('invalid IPv4 address: '
                                         f'{value}') from None
    return value


def vlan_id(value: str) -> int:
    """Argument type for 802.1q VLAN IDs, 1 - 4095 or 'off' for 0."""
    if value == 'off':
        return 0
    try:
        vlan = int(value, 0)
    except ValueError:
        vlan = None
    if vlan is None or not 1 <= vlan <= 4095:
        raise argparse.ArgumentTypeError(f'invalid VLAN ID: {value}')
    return vlan


def log_level(value: str) -> tuple[str, int]:
    """Argument type for log levels, [<logger>=]<level>.

    The logger name is relative to 'pyipmi' (e.g. 'interfaces.aardvark'),
    without a name the level applies to all pyipmi loggers.
    """
    name, _, level = value.rpartition('=')
    if name in ('', 'pyipmi'):
        name = 'pyipmi'
    elif not name.startswith('pyipmi.'):
        name = 'pyipmi.' + name

    if level.isdigit():
        return (name, int(level))
    # getLevelName() maps a known level name to its number
    number = logging.getLevelName(level.upper())
    if not isinstance(number, int):
        raise argparse.ArgumentTypeError(f'invalid log level: {level}')
    return (name, number)


def cmd_bmc_info(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    device_id = ipmi.get_device_id()
    manufacturer = device_id.manufacturer_name or 'Unknown'
    print(f'''
Device ID:          {device_id.device_id:d} (0x{device_id.device_id:02x})
Device Revision:    {device_id.revision}
Firmware Revision:  {device_id.fw_revision}
IPMI Version:       {device_id.ipmi_version}
Manufacturer ID:    {device_id.manufacturer_id:d} (0x{device_id.manufacturer_id:04x})
Manufacturer Name:  {manufacturer}
Product ID:         {device_id.product_id:d} (0x{device_id.product_id:04x})
Device Available:   {device_id.available:d}
Provides SDRs:      {device_id.provides_sdrs:d}
Additional Device Support:
'''[1:-1])

    functions = (
            ('SENSOR', 'Sensor Device'),
            ('SDR_REPOSITORY', 'SDR Repository Device'),
            ('SEL', 'SEL Device'),
            ('FRU_INVENTORY', 'FRU Inventory Device'),
            ('IPMB_EVENT_RECEIVER', 'IPMB Event Receiver'),
            ('IPMB_EVENT_GENERATOR', 'IPMB Event Generator'),
            ('BRIDGE', 'Bridge'),
            ('CHASSIS', 'Chassis Device')
    )
    for n, s in functions:
        if device_id.supports_function(n):
            print(f'  {s}')

    if device_id.aux is not None:
        print("Aux Firmware Rev Info:  "
              f"[{' '.join(f'{d:02x}' for d in device_id.aux):s}]")


def cmd_bmc_reset(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.type == 'cold':
        ipmi.cold_reset()
    else:
        ipmi.warm_reset()


def sel_sensor_records(ipmi: pyipmi.Ipmi) -> dict[tuple[int, int, int],
                                                  pyipmi.sdr.SdrCommon]:
    """Return the sensor records by owner ID, owner LUN and sensor number.

    The records are read from the SDR repository, or from the device SDR
    repository of a device without SDR repository.
    """
    records = sdr_entries(ipmi)
    if records is None:
        return {}
    return {(s.owner_id, s.owner_lun, s.number): s for s in records
            if hasattr(s, 'number') and hasattr(s, 'owner_id')}


def sel_entry_sensor(entry: pyipmi.sel.SelEntry,
                     records: dict[tuple[int, int, int],
                                   pyipmi.sdr.SdrCommon]
                     ) -> pyipmi.sdr.SdrCommon | None:
    """Return the sensor record of the sensor that generated an event."""
    owner_id = entry.generator_id & 0xff
    owner_lun = (entry.generator_id >> 8) & 0x3
    return records.get((owner_id, owner_lun, entry.sensor_number))


def sel_entry_values(entry: pyipmi.sel.SelEntry,
                     record: pyipmi.sdr.SdrCommon | None) -> str | None:
    """Return the trigger reading and threshold of a threshold event.

    The raw values are converted with the full sensor record, if given.
    """
    (reading, threshold) = entry.threshold_event_values()
    if reading is None and threshold is None:
        return None

    def convert(raw: int) -> str:
        if isinstance(record, pyipmi.sdr.SdrFullSensorRecord):
            value = format_analog_value(
                record.convert_sensor_raw_to_value(raw))
            return f'[0x{raw:02x}] {value}'
        return f'0x{raw:02x}'

    values = []
    if reading is not None:
        values.append(f'Reading {convert(reading)}')
    if threshold is not None:
        values.append(f'Threshold {convert(threshold)}')
    return ', '.join(values)


def sel_entry_sensor_name(entry: pyipmi.sel.SelEntry,
                          record: pyipmi.sdr.SdrCommon | None) -> str:
    sensor_type = entry.sensor_type_to_string(entry.sensor_type)
    name = getattr(record, 'device_id_string', None)
    if name:
        return f'{sensor_type} {name}'
    return f'{sensor_type} #0x{entry.sensor_number:02x}'


def print_sel_entry(entry: pyipmi.sel.SelEntry,
                    record: pyipmi.sdr.SdrCommon | None) -> None:
    columns = [f'0x{entry.record_id:04x}', f'{entry.timestamp_to_string():<19}']
    if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
        columns.append(sel_entry_sensor_name(entry, record))
        columns.append(entry.event_to_string())
        columns.append(entry.direction_to_string())
        values = sel_entry_values(entry, record)
        if values is not None:
            columns.append(values)
    else:
        # the bytes after the timestamp (or the record type) are OEM data
        start = 7 if entry.is_timestamped() else 3
        columns.append(pyipmi.sel.SelEntry.type_to_string(entry.type) or '')
        columns.append(' '.join(f'{b:02x}' for b in entry.data[start:]))
    print(' | '.join(columns))


def print_sel_entry_details(entry: pyipmi.sel.SelEntry,
                            record: pyipmi.sdr.SdrCommon | None) -> None:
    raw = ' '.join(f'{b:02x}' for b in entry.data)
    print(f'SEL Record ID:   0x{entry.record_id:04x}')
    if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
        type_name = 'System Event'
    elif entry.is_timestamped():
        type_name = 'OEM timestamped'
    else:
        type_name = 'OEM non-timestamped'
    print(f'Record Type:     [0x{entry.type:02x}] {type_name}')
    timestamp = entry.timestamp_to_string()
    if entry.is_timestamped():
        timestamp = f'[0x{entry.timestamp:08x}] {timestamp}'
    print(f'Timestamp:       {timestamp}')
    if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
        print(f'Generator ID:    [0x{entry.generator_id:04x}] '
              f'{entry.generator_to_string()}')
        print(f'EvM Revision:    0x{entry.evm_rev:02x}')
        print(f'Sensor Type:     [0x{entry.sensor_type:02x}] '
              f'{entry.sensor_type_to_string(entry.sensor_type)}')
        print(f'Sensor Number:   0x{entry.sensor_number:02x}')
        name = getattr(record, 'device_id_string', None)
        if name:
            print(f'Sensor Name:     {name}')
        type_name = pyipmi.sensor.event_reading_type_to_string(
            entry.event_type)
        print(f'Event Type:      [0x{entry.event_type:02x}] {type_name}')
        print(f'Event Direction: [0x{entry.event_direction:x}] '
              f'{entry.direction_to_string()}')
        print(f'Event Data:      '
              f"{' '.join(f'{b:02x}' for b in entry.event_data)}")
        print(f'Description:     [0x{entry.event_offset:02x}] '
              f'{entry.event_to_string()}')
        values = sel_entry_values(entry, record)
        if values is not None:
            print(f'Values:          {values}')
    print(f'Raw Data:        {raw}')
    print()


def cmd_sel_list(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    records = sel_sensor_records(ipmi) if args.sdr else {}
    print_entry = print_sel_entry_details if args.details else print_sel_entry
    for entry in ipmi.sel_entries():
        record = None
        if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
            record = sel_entry_sensor(entry, records)
        print_entry(entry, record)


def cmd_sel_clear(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.clear_sel()


def cmd_sel_info(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    info = ipmi.get_sel_info()
    ts = pyipmi.sel.timestamp_to_string
    operations = [op for op in info.operation_support
                  if op != 'overflow_flag']
    print(f'''
Version:                 {info.version & 0xf:d}.{info.version >> 4:d}
Entries:                 {info.entries:d}
Free Space:              {info.free_bytes:d} bytes
Last Add Time:           {ts(info.most_recent_addition)}
Last Erase Time:         {ts(info.most_recent_erase)}
Overflow:                {'overflow_flag' in info.operation_support}
Supported Commands:      {', '.join(operations) or 'none'}
'''[1:-1])
    if 'get_sel_allocation_info' in info.operation_support:
        alloc = ipmi.get_sel_allocation_info()
        print(f'''
Allocation Units:        {alloc.possible_alloc_units:d}
Allocation Unit Size:    {alloc.alloc_unit_size:d} bytes
Free Allocation Units:   {alloc.free_alloc_units:d}
Largest Free Block:      {alloc.largest_free_block:d} units
Maximum Record Size:     {alloc.max_record_size:d} units
'''[1:-1])


def sel_time(value: str) -> int:
    """Argument type for a SEL time, 'now' or 'YYYY-MM-DD HH:MM:SS' (UTC)."""
    if value == 'now':
        return int(time.time())
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid time: {value}, use '
                                         '"YYYY-MM-DD HH:MM:SS" or now') \
            from None
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def cmd_sel_time_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    print(pyipmi.sel.timestamp_to_string(ipmi.get_sel_time()))


def cmd_sel_time_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_sel_time(args.time)
    print(pyipmi.sel.timestamp_to_string(ipmi.get_sel_time()))


def utc_offset(value: str) -> int | str:
    """Argument type for the UTC offset, minutes or 'unspecified'."""
    if value == 'unspecified':
        return value
    try:
        offset = int(value, 0)
    except ValueError:
        offset = None
    if offset is None or not -1440 <= offset <= 1440:
        raise argparse.ArgumentTypeError(f'invalid UTC offset: {value}, use '
                                         '-1440 - 1440 minutes or '
                                         'unspecified')
    return offset


def cmd_sel_utc_offset(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.offset is not None:
        ipmi.set_sel_time_utc_offset(None if args.offset == 'unspecified'
                                     else args.offset)
    offset = ipmi.get_sel_time_utc_offset()
    if offset is None:
        print('UTC offset: unspecified')
    else:
        print(f'UTC offset: {offset:+d} minutes')


def cmd_sel_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    records = sel_sensor_records(ipmi) if args.sdr else {}
    reservation = ipmi.get_sel_reservation_id()
    for record_id in args.record_ids:
        entry, _ = ipmi.get_sel_entry(record_id, reservation)
        record = None
        if entry.type == pyipmi.sel.SelEntry.TYPE_SYSTEM_EVENT:
            record = sel_entry_sensor(entry, records)
        print_sel_entry_details(entry, record)


def byte_value(value: str) -> int:
    """Argument type for a byte, decimal or with 0x prefix."""
    try:
        byte = int(value, 0)
    except ValueError:
        byte = -1
    if not 0 <= byte <= 0xff:
        raise argparse.ArgumentTypeError(f'invalid byte: {value}')
    return byte


def cmd_sel_add(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    data = bytes(args.record_data)
    if args.partial:
        record_id = ipmi.partial_add_sel_entry(data)
    else:
        record_id = ipmi.add_sel_entry(data)
    print(f'Added SEL entry 0x{record_id:04x}')


def cmd_sel_delete(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    reservation = ipmi.get_sel_reservation_id()
    for record_id in args.record_ids:
        ipmi.delete_sel_entry(record_id, reservation)
        print(f'Deleted SEL entry 0x{record_id:04x}')


SEL_AUXILIARY_LOGS = {
    'mca': pyipmi.sel.AUXILIARY_LOG_MCA,
    'oem1': pyipmi.sel.AUXILIARY_LOG_OEM1,
    'oem2': pyipmi.sel.AUXILIARY_LOG_OEM2,
}


def cmd_sel_aux_status(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    data = ipmi.get_auxiliary_log_status(SEL_AUXILIARY_LOGS[args.log])
    print(data.hex(' ') or 'no status data')


def cmd_sensor_rearm(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.rearm_sensor_events(args.number)


def format_sensor_type(sensor_type: int, event_reading_type: int) -> str:
    type_name = pyipmi.sensor.sensor_type_to_string(sensor_type)
    event_name = pyipmi.sensor.event_reading_type_to_string(
        event_reading_type)
    return (f'Sensor Type:             [0x{sensor_type:02x}] {type_name}\n'
            f'Event/Reading Type:      [0x{event_reading_type:02x}] '
            f'{event_name}')


def cmd_sensor_type(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.type is not None:
        ipmi.set_sensor_type(args.number, args.type[0], args.type[1],
                             lun=args.lun)
    print(format_sensor_type(*ipmi.get_sensor_type(args.number,
                                                   lun=args.lun)))


def cmd_sensor_hysteresis(ipmi: pyipmi.Ipmi,
                          args: argparse.Namespace) -> None:
    if args.hysteresis is not None:
        ipmi.set_sensor_hysteresis(args.number, args.hysteresis[0],
                                   args.hysteresis[1], lun=args.lun)
    positive, negative = ipmi.get_sensor_hysteresis(args.number, lun=args.lun)
    print(f'''
Positive Hysteresis:     [0x{positive:02x}] {positive:d}
Negative Hysteresis:     [0x{negative:02x}] {negative:d}
'''[1:-1])


def sensor_events_to_strings(mask: int | None, sensor_type: int,
                             event_reading_type: int) -> list[str]:
    """Return the raw mask and the names of the events of a mask."""
    if mask is None:
        return ['na']
    names = []
    for offset in range(15):
        if mask & (1 << offset):
            name = pyipmi.sensor.event_offset_to_string(
                event_reading_type, sensor_type, offset)
            names.append(name or f'Offset 0x{offset:02x}')
    return [f'[0x{mask:04x}]'] + names


def print_sensor_events(label: str, mask: int | None, sensor_type: int,
                        event_reading_type: int) -> None:
    lines = sensor_events_to_strings(mask, sensor_type, event_reading_type)
    print(f'{label + ":":<25}{lines[0]}')
    for line in lines[1:]:
        print(f'{"":<25}{line}')


def cmd_sensor_events(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.messages is not None or args.scanning is not None:
        # both are set at once, keep the one that is not given
        enable = ipmi.get_sensor_event_enable(args.number, lun=args.lun)
        messages = enable.event_messages if args.messages is None \
            else args.messages == 'on'
        scanning = enable.sensor_scanning if args.scanning is None \
            else args.scanning == 'on'
        ipmi.set_sensor_event_enable(args.number, event_messages=messages,
                                     sensor_scanning=scanning, lun=args.lun)

    sensor_type, event_reading_type = ipmi.get_sensor_type(args.number,
                                                           lun=args.lun)
    enable = ipmi.get_sensor_event_enable(args.number, lun=args.lun)
    status = ipmi.get_sensor_event_status(args.number, lun=args.lun)
    print(format_sensor_type(sensor_type, event_reading_type))
    print(f'''
Event Messages:          {'enabled' if enable.event_messages else 'disabled'}
Sensor Scanning:         {'enabled' if enable.sensor_scanning else 'disabled'}
Reading Unavailable:     {status.reading_unavailable}
'''[1:-1])
    types = (sensor_type, event_reading_type)
    print_sensor_events('Enabled Assertions', enable.assertion_mask, *types)
    print_sensor_events('Enabled Deassertions', enable.deassertion_mask,
                        *types)
    print_sensor_events('Asserted Events', status.asserted, *types)
    print_sensor_events('Deasserted Events', status.deasserted, *types)


def cmd_sensor_factors(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    factors = ipmi.get_sensor_reading_factors(args.number, args.reading,
                                              lun=args.lun)
    print(f'''
M:                       {factors.m:d}
B:                       {factors.b:d}
K1 (B Exponent):         {factors.k1:d}
K2 (Result Exponent):    {factors.k2:d}
Tolerance:               {factors.tolerance:d}
Accuracy:                {factors.accuracy:d}
Accuracy Exponent:       {factors.accuracy_exp:d}
Next Reading:            [0x{factors.next_reading:02x}] {factors.next_reading:d}
'''[1:-1])


def cmd_sensor_set_reading(ipmi: pyipmi.Ipmi,
                           args: argparse.Namespace) -> None:
    ipmi.set_sensor_reading_and_event_status(args.number, reading=args.reading,
                                             lun=args.lun)


def format_analog_value(value: float | None) -> str:
    """Format a converted analog sensor value with 3 decimal places."""
    if value is None:
        return 'na'
    return f'{value:.3f}'


def sdr_entries(ipmi: pyipmi.Ipmi) -> Iterator[pyipmi.sdr.SdrCommon] | None:
    """Return the records of the SDR repository.

    The records are read from the device SDR repository of a device without
    SDR repository, None if the device has neither.
    """
    device_id = ipmi.get_device_id()
    if device_id.supports_function('sdr_repository'):
        return ipmi.sdr_repository_entries()
    if device_id.supports_function('sensor'):
        return ipmi.device_sdr_entries()
    return None


# The thresholds of a full sensor record: the key, the name and the bit of
# the threshold in the readable threshold mask
SDR_THRESHOLDS = (
    ('unr', 'Upper Non-recoverable', 5),
    ('ucr', 'Upper Critical', 4),
    ('unc', 'Upper Non-critical', 3),
    ('lnc', 'Lower Non-critical', 0),
    ('lcr', 'Lower Critical', 1),
    ('lnr', 'Lower Non-recoverable', 2),
)

# The device capabilities of a management controller device locator
MC_DEVICE_CAPABILITIES = ('Sensor Device', 'SDR Repository Device',
                          'SEL Device', 'FRU Inventory Device',
                          'IPMB Event Receiver', 'IPMB Event Generator',
                          'Bridge', 'Chassis Device')


def print_sdr_field(label: str, value: object) -> None:
    print(f'{label + ":":<24}{value}')


def print_sdr_list_field(label: str, values: list[str]) -> None:
    """Print a field with one value per line."""
    if not values:
        print_sdr_field(label, 'none')
        return
    print_sdr_field(label, values[0])
    for value in values[1:]:
        print(f'{"":<24}{value}')


def format_owner(owner_id: int, lun: int | None = None) -> str:
    """Format the 8-bit IPMB address or the software ID of an owner."""
    if owner_id & 0x1:
        return f'Software 0x{owner_id >> 1:02x}'
    if lun is None:
        return f'IPMB 0x{owner_id:02x}'
    return f'IPMB 0x{owner_id:02x} LUN {lun:d}'


def format_sdr_value(record: pyipmi.sdr.SdrFullSensorRecord, raw: int | None,
                     unit: str) -> str:
    """Format a raw value converted to the sensor unit and the raw value."""
    if raw is None:
        return 'na'
    value = format_analog_value(record.convert_sensor_raw_to_value(raw))
    if value != 'na' and unit:
        value = f'{value} {unit}'
    return f'[0x{raw:02x}] {value}'


# The records of a sensor
SdrSensorRecord = (pyipmi.sdr.SdrFullSensorRecord
                   | pyipmi.sdr.SdrCompactSensorRecord
                   | pyipmi.sdr.SdrEventOnlySensorRecord)


def sdr_sensor_type(record: SdrSensorRecord) -> int:
    # the event-only record has another attribute name for the sensor type
    if isinstance(record, pyipmi.sdr.SdrEventOnlySensorRecord):
        return record.sensor_type
    return record.sensor_type_code


def sdr_event_strings(record: SdrSensorRecord, mask: int) -> list[str]:
    """Return the descriptions of the event offsets or states of a mask."""
    strings = []
    for offset in range(15):
        if mask & (1 << offset):
            string = pyipmi.sensor.event_offset_to_string(
                record.event_reading_type_code, sdr_sensor_type(record),
                offset)
            strings.append(string or f'Offset 0x{offset:02x}')
    return strings


def sdr_show_sensor(s: SdrSensorRecord) -> None:
    """Print the fields of a full, compact or event-only sensor record."""
    sensor_type = sdr_sensor_type(s)
    event_type = s.event_reading_type_code
    threshold_based = (event_type
                       == pyipmi.sensor.EVENT_READING_TYPE_CODE_THRESHOLD)
    unit = ''
    if not isinstance(s, pyipmi.sdr.SdrEventOnlySensorRecord):
        unit = pyipmi.sdr.units_to_string(s.units_1, s.units_2, s.units_3)

    print_sdr_field('Sensor Owner',
                    f'[0x{s.owner_id:02x} 0x{s.owner_lun:02x}] '
                    f'{format_owner(s.owner_id, s.owner_lun)}')
    print_sdr_field('Sensor Number', f'0x{s.number:02x}')
    type_name = pyipmi.sensor.sensor_type_to_string(sensor_type)
    print_sdr_field('Sensor Type', f'[0x{sensor_type:02x}] {type_name}')
    type_name = pyipmi.sensor.event_reading_type_to_string(event_type)
    print_sdr_field('Event/Reading Type', f'[0x{event_type:02x}] {type_name}')
    # the values of a full sensor record are printed with the unit
    if unit and isinstance(s, pyipmi.sdr.SdrCompactSensorRecord):
        print_sdr_field('Unit', f'[0x{s.units_1:02x} 0x{s.units_2:02x} '
                                f'0x{s.units_3:02x}] {unit}')

    if isinstance(s, pyipmi.sdr.SdrEventOnlySensorRecord):
        return

    if isinstance(s, pyipmi.sdr.SdrFullSensorRecord) and threshold_based:
        # the readable thresholds are in the reading mask
        readable = s.discrete_reading_mask & 0x3f
        for key, name, bit in SDR_THRESHOLDS:
            if readable & (1 << bit):
                print_sdr_field(name,
                                format_sdr_value(s, s.threshold[key], unit))
        for key, name, value in (
                ('nominal_reading', 'Nominal Reading', s.nominal_reading),
                ('normal_max', 'Normal Maximum', s.normal_maximum),
                ('normal_min', 'Normal Minimum', s.normal_minimum)):
            if key in s.analog_characteristic:
                print_sdr_field(name, format_sdr_value(s, value, unit))
        print_sdr_field('Sensor Minimum',
                        format_sdr_value(s, s.sensor_minimum_reading, unit))
        print_sdr_field('Sensor Maximum',
                        format_sdr_value(s, s.sensor_maximum_reading, unit))

    # bits 14:12 of the masks of a threshold sensor are no events
    events = 0x0fff if threshold_based else 0x7fff
    for label, mask in (('Assertion Events', s.assertion_mask),
                        ('Deassertion Events', s.deassertion_mask)):
        print_sdr_list_field(label, [f'[0x{mask:04x}]']
                             + sdr_event_strings(s, mask & events))


def sdr_show(s: pyipmi.sdr.SdrCommon) -> None:
    """Print the fields of a record, without reading the sensor."""
    print_sdr_field('Record ID', f'0x{s.id:04x}')
    type_name = pyipmi.sdr.sdr_type_to_string(s.type)
    print_sdr_field('Record Type', f'[0x{s.type:02x}] {type_name}')
    # not all record types have an ID string and entity
    if getattr(s, 'device_id_string', None) is not None:
        print_sdr_field('Name', s.device_id_string)
    if hasattr(s, 'entity_id'):
        print_sdr_field('Entity',
                        f'[0x{s.entity_id:02x} 0x{s.entity_instance:02x}] '
                        f'{pyipmi.sdr.entity_id_to_string(s.entity_id)}')

    if isinstance(s, (pyipmi.sdr.SdrFullSensorRecord,
                      pyipmi.sdr.SdrCompactSensorRecord,
                      pyipmi.sdr.SdrEventOnlySensorRecord)):
        sdr_show_sensor(s)
    elif isinstance(s, pyipmi.sdr.SdrFruDeviceLocator):
        print_sdr_field('Device Access Address',
                        f'0x{s.device_access_address << 1:02x}')
        logical = f'[0x{s.logical_physical:02x}]'
        if s.logical_physical & 0x80:
            print_sdr_field('FRU Device ID',
                            f'[0x{s.fru_device_id:02x}] {s.fru_device_id:d}')
        else:
            print_sdr_field('FRU Device Address', f'0x{s.fru_device_id:02x}')
            print_sdr_field('Private Bus',
                            f'{logical} {s.logical_physical & 0x7:d}')
        print_sdr_field('Access LUN',
                        f'{logical} {(s.logical_physical >> 3) & 0x3:d}')
        print_sdr_field('Channel', f'[0x{s.channel_number:02x}] '
                                   f'{s.channel_number >> 4:d}')
        print_sdr_field('Device Type',
                        f'0x{s.device_type:02x} '
                        f'modifier 0x{s.device_type_modifier:02x}')
    elif isinstance(s, pyipmi.sdr.SdrManagementControllerDeviceLocator):
        print_sdr_field('Slave Address',
                        f'0x{s.device_slave_address << 1:02x}')
        print_sdr_field('Channel', f'[0x{s.channel_number:02x}] '
                                   f'{s.channel_number:d}')
        print_sdr_list_field('Device Capabilities',
                             [f'[0x{s.device_capabilities:02x}]']
                             + [name for bit, name
                                in enumerate(MC_DEVICE_CAPABILITIES)
                                if s.device_capabilities & (1 << bit)])
    elif isinstance(s,
                    pyipmi.sdr.SdrManagementControllerConfirmationRecord):
        print_sdr_field('Slave Address',
                        f'0x{s.device_slave_address << 1:02x}')
        print_sdr_field('Device ID', f'0x{s.device_id:02x}')
        print_sdr_field('Device Revision', f'[0x{s.device_revision:02x}] '
                                           f'{s.device_revision:d}')
        print_sdr_field('Channel', f'[0x{s.channel_number:02x}] '
                                   f'{s.channel_number:d}')
        print_sdr_field('Firmware Revision',
                        f'[0x{s.firmware_revision_1:02x} '
                        f'0x{s.firmware_revision_2:02x}] '
                        f'{s.firmware_revision_1:d}.'
                        f'{s.firmware_revision_2:02x}')
        print_sdr_field('IPMI Version',
                        f'[0x{s.ipmi_version:02x}] '
                        f'{s.ipmi_version & 0xf:d}.{s.ipmi_version >> 4:d}')
        print_sdr_field('Manufacturer',
                        f'[0x{s.manufacturer_id:05x}] '
                        f'{s.manufacturer_name or "Unknown"}')
        print_sdr_field('Product ID', f'0x{s.product_id:04x}')
    elif isinstance(s, pyipmi.sdr.SdrOEMSensorRecord):
        if s.manufacturer_id is not None:
            print_sdr_field('Manufacturer',
                            f'[0x{s.manufacturer_id:05x}] '
                            f'{s.manufacturer_name or "Unknown"}')
        print_sdr_field('OEM Data', ' '.join(f'{b:02x}' for b in s.oem_data))
    else:
        print_sdr_field('Raw Data', ' '.join(f'{b:02x}' for b in s.data))


def cmd_sdr_show_raw(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        sdr = ipmi.get_device_sdr(args.sdr_id)
        print(' '.join([f'0x{b:02x}' for b in sdr.data]))
    except ValueError:
        print('')


def cmd_sdr_show(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        s = ipmi.get_device_sdr(args.sdr_id)
        sdr_show(s)
    except ValueError:
        print('')


def cmd_sdr_show_all(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for s in ipmi.device_sdr_entries():
        try:
            sdr_show(s)
        except ValueError:
            pass
        print()


def print_sdr_list_entry(record_id: int, number: int | str | None,
                         id_string: str | None, value: object,
                         states: int | None) -> None:
    # sensor number 0 and the states 0 are valid
    number_str = 'na' if number is None else str(number)
    states_str = 'na' if states is None else hex(states)

    print(f"0x{record_id:04x} | {number_str!s:>3} | {id_string!s:<18} | "
          f"{value!s:>9} | {states_str}")


def cmd_sdr_list(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    records = sdr_entries(ipmi)
    if records is None:
        print("Device supports neither SDR repository nor sensor "
              "functions", file=sys.stderr)
        return

    if args.details:
        for s in records:
            sdr_show(s)
            print()
        return

    print("SDR-ID |     | Device String      |")
    print("=======|=====|====================|====================")

    for s in records:
        try:
            number = None
            value: int | str | None = None
            states = None

            if isinstance(s, pyipmi.sdr.SdrFullSensorRecord):
                (raw, states) = ipmi.get_sensor_reading(s.number, s.owner_lun)
                number = s.number
                if raw is not None:
                    value = format_analog_value(
                        s.convert_sensor_raw_to_value(raw))

            elif isinstance(s, pyipmi.sdr.SdrCompactSensorRecord):
                (value, states) = ipmi.get_sensor_reading(s.number,
                                                          s.owner_lun)
                number = s.number

            id_string = getattr(s, 'device_id_string', None)

            print_sdr_list_entry(s.id, number, id_string, value, states)

        except pyipmi.errors.CompletionCodeError as e:
            if s.type in (pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD,
                          pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD):
                print(f'0x{s.id:04x} | {s.number:3d} | {s.device_id_string:18s} | ERR: CC=0x{e.cc:02x}')


# the update types of the SDR repository info
SDR_UPDATE_TYPES = ('unspecified', 'non-modal', 'modal', 'modal and '
                    'non-modal')


def cmd_sdr_info(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    info = ipmi.get_sdr_repository_info()
    ts = pyipmi.sel.timestamp_to_string
    operations = [name for name, supported in (
        ('get_allocation_info', info.support_get_allocation_info),
        ('reserve', info.support_reserve),
        ('partial_add', info.support_partial_add),
        ('delete', info.support_delete)) if supported]
    # 0xffff: unspecified, 0xfffe: 64 KB - 2 bytes or more
    if info.free_space == 0xffff:
        free_space = 'unspecified'
    else:
        free_space = f'{info.free_space:d} bytes'
    print(f'''
Version:                 {info.sdr_version & 0xf:d}.{info.sdr_version >> 4:d}
Records:                 {info.record_count:d}
Free Space:              {free_space}
Last Add Time:           {ts(info.most_recent_addition)}
Last Erase Time:         {ts(info.most_recent_erase)}
Overflow:                {bool(info.support_overflow_flag)}
Update Type:             {SDR_UPDATE_TYPES[info.support_update_type]}
Supported Commands:      {', '.join(operations) or 'none'}
'''[1:-1])
    if info.support_get_allocation_info:
        alloc = ipmi.get_sdr_repository_allocation_info()
        print(f'''
Allocation Units:        {alloc.number_of_units:d}
Allocation Unit Size:    {alloc.unit_size:d} bytes
Free Allocation Units:   {alloc.free_units:d}
Largest Free Block:      {alloc.largest_free_block:d} units
Maximum Record Size:     {alloc.maximum_record_size:d} units
'''[1:-1])


def cmd_sdr_device_info(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    info = ipmi.get_device_sdr_info(sdr_count=args.sdr_count)
    change = info.sensor_population_change
    luns = ', '.join(str(lun) for lun in info.luns_with_sensors)
    print(f'''
{'SDRs:' if args.sdr_count else 'Sensors:':<25}{info.count:d}
LUNs with Sensors:       {luns or 'none'}
Dynamic Population:      {info.dynamic_population}
Population Change:       {'na' if change is None else
                          pyipmi.sel.timestamp_to_string(change)}
'''[1:-1])


def cmd_sdr_time_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    print(pyipmi.sel.timestamp_to_string(ipmi.get_sdr_repository_time()))


def cmd_sdr_time_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_sdr_repository_time(args.time)
    print(pyipmi.sel.timestamp_to_string(ipmi.get_sdr_repository_time()))


def cmd_sdr_add(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    record_id = ipmi.add_sdr(bytes(args.record_data),
                             part_size=args.part_size)
    print(f'Added SDR 0x{record_id:04x}')


def cmd_sdr_delete(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for record_id in args.record_ids:
        ipmi.delete_sdr(record_id)
        print(f'Deleted SDR 0x{record_id:04x}')


def cmd_sdr_update_mode(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.mode == 'enter':
        ipmi.enter_sdr_repository_update_mode()
    else:
        ipmi.exit_sdr_repository_update_mode()


def cmd_fru_read(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    data = ipmi.read_fru_data_full(args.fru_id)
    with open(args.filename, 'wb') as f:
        f.write(data)
    print(f'Read {len(data):d} bytes from FRU {args.fru_id:d} to '
          f'{args.filename}')


def print_fru_inventory(inv: pyipmi.fru.FruInventory, print_all: bool,
                        all_hint: str) -> None:
    """Print a FRU inventory.

    The data of the internal use area and the multirecord area are only
    printed with `print_all`.
    """
    # Internal Use Area
    internal_use_area = inv.internal_use_area
    if internal_use_area:
        data = internal_use_area.internal_use_data
        print('Internal Use Area:')
        print(f'  Format Version:     {internal_use_area.format_version:d}')
        print(f'  Data Length:        {len(data):d}')
        if print_all:
            # 16 bytes per line
            lines = [data[i:i + 16].hex(' ') for i in range(0, len(data), 16)]
            for i, line in enumerate(lines):
                print(f"  {'Data:' if i == 0 else '':<20}{line}")

    # Chassis Info Area
    chassis_area = inv.chassis_info_area
    if chassis_area:
        print(f'''
Chassis Info Area:
  Type:               {chassis_area.type:d}
  Part Number:        {chassis_area.part_number}
  Serial Number:      {chassis_area.serial_number}
'''[1:-1])

        if len(chassis_area.custom_chassis_info) != 0:
            print('  Custom Chassis Info Records:')
            for field in chassis_area.custom_chassis_info:
                print(f'    {field}')

    # Board Info Area
    board_area = inv.board_info_area
    if board_area:
        print(f'''
Board Info Area:
  Mfg. Date / Time:   {board_area.mfg_date}
  Manufacturer:       {board_area.manufacturer}
  Product Name:       {board_area.product_name}
  Serial Number:      {board_area.serial_number}
  Part Number:        {board_area.part_number}
  FRU File ID:        {board_area.fru_file_id}
'''[1:-1])

        if len(board_area.custom_mfg_info) != 0:
            print('  Custom Board Info Records:')
            for field in board_area.custom_mfg_info:
                print(f'    {field}')

    # Product Info Area
    product_area = inv.product_info_area
    if product_area:
        print(f'''
Product Info Area:
  Manufacturer:       {product_area.manufacturer}
  Name:               {product_area.name}
  Part/Model Number:  {product_area.part_number}
  Version:            {product_area.version}
  Serial Number:      {product_area.serial_number}
  Asset:              {product_area.asset_tag}
  FRU File ID:        {product_area.fru_file_id}
'''[1:-1])

        if len(product_area.custom_mfg_info) != 0:
            print('  Custom Board Info Records:')
            for field in product_area.custom_mfg_info:
                print(f'    {field}')

    # Multirecords
    multirecord_area = inv.multirecord_area
    if multirecord_area:
        print('Multirecord Area:')
        if print_all:
            for record in multirecord_area.records:
                print(f'  {record}')
        else:
            print(f'  Skipped. Use "{all_hint}"')


def cmd_fru_print(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    inv = ipmi.get_fru_inventory(args.fru_id)
    print_fru_inventory(inv, args.all == 'all', 'print <fruid> all')


def cmd_fru_print_file(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        inv = pyipmi.fru.get_fru_inventory_from_file(args.filename)
    except (OSError, pyipmi.errors.DecodingError) as e:
        print(f'Cannot read the FRU data of {args.filename}: {e}',
              file=sys.stderr)
        sys.exit(1)
    print_fru_inventory(inv, args.all == 'all', 'print-file <filename> all')


def cmd_raw(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    raw_bytes = array('B', args.data)
    rsp = ipmi.send_raw(args.lun, args.netfn, py3_array_tobytes(raw_bytes))
    print(' '.join(f'{d:02x}' for d in array('B', rsp)))


def cmd_hpm_capabilities(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    cap = ipmi.get_target_upgrade_capabilities()

    for c in cap.components:
        properties = ipmi.get_component_properties(c)
        print(f"Component ID: {c:d}")
        for prop in properties:
            print(f"  {prop}")


def cmd_hpm_check_file(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    cap = pyipmi.hpm.UpgradeImage(args.file)

    print(cap.header)
    for action in cap.actions:
        print(action)


def cmd_hpm_install(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.install_component_from_file(args.file, args.component_id)


def cmd_chassis_status(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    status = ipmi.get_chassis_status()

    if args.json:
        print(json.dumps({
                  'power_on': status.power_on,
                  'overload': status.overload,
                  'interlock': status.interlock,
                  'fault': status.fault,
                  'ctrl_fault': status.control_fault,
                  'restore_policy': status.restore_policy
                 }))
    else:

        print(f'''
Power ON:          {status.power_on}
Overload:          {status.overload}
Interlock:         {status.interlock}
Fault:             {status.fault}
Ctrl Fault:        {status.control_fault}
Restore Policy:    {status.restore_policy}
'''[1:-1])

        for event in status.last_event:
            print(event)
        for state in status.chassis_state:
            print(state)


CHASSIS_POWER_CONTROLS = {
    'off': 'chassis_control_power_down',
    'on': 'chassis_control_power_up',
    'cycle': 'chassis_control_power_cycle',
    'reset': 'chassis_control_hard_reset',
    'diag': 'chassis_control_diagnostic_interrupt',
    'soft': 'chassis_control_soft_shutdown',
}


def cmd_lan_print(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    lan = pyipmi.lan
    channel = args.lan_channel
    if channel is None:
        channel = ipmi.get_lan_channel()

    def parameter(selector: int, convert: Callable) -> object:
        try:
            return convert(ipmi.get_lan_config_param(channel, selector))
        except pyipmi.errors.CompletionCodeError:
            return 'not supported'

    lines: list[tuple[str, object]] = [('Channel', channel)]
    lines.append(('IP Address Source',
                  parameter(lan.LAN_PARAMETER_IP_ADDRESS_SOURCE,
                            lan.data_to_ip_source)))
    lines.append(('IP Address', parameter(lan.LAN_PARAMETER_IP_ADDRESS,
                                          lan.data_to_ip_address)))
    lines.append(('Subnet Mask', parameter(lan.LAN_PARAMETER_SUBNET_MASK,
                                           lan.data_to_ip_address)))
    lines.append(('MAC Address', parameter(lan.LAN_PARAMETER_MAC_ADDRESS,
                                           lan.data_to_mac_address)))
    lines.append(('Default Gateway IP',
                  parameter(lan.LAN_PARAMETER_DEFAULT_GATEWAY_ADDRESS,
                            lan.data_to_ip_address)))
    lines.append(('Default Gateway MAC',
                  parameter(lan.LAN_PARAMETER_DEFAULT_GATEWAY_MAC_ADDRESS,
                            lan.data_to_mac_address)))
    vlan = parameter(lan.LAN_PARAMETER_802_1Q_VLAN_ID, lan.data_to_vlan)
    lines.append(('802.1q VLAN ID', 'disabled' if vlan == 0 else vlan))

    for (name, value) in lines:
        print(f"{name + ':':<21}{value}")


def cmd_lan_set_ipaddr(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_ip_address(args.address, args.lan_channel)


def cmd_lan_set_ipsrc(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_ip_source(args.source, args.lan_channel)


def cmd_lan_set_vlan(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vlan_id(args.vlan, args.lan_channel)


def cmd_chassis_power(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    getattr(ipmi, CHASSIS_POWER_CONTROLS[args.action])()


def cmd_chassis_reset(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.chassis_reset()


def identify_interval(value: str) -> int | str:
    """Argument type for the identify interval, 0 - 255 or 'force'."""
    if value == 'force':
        return value
    try:
        interval = int(value, 0)
    except ValueError:
        interval = -1
    if not 0 <= interval <= 255:
        raise argparse.ArgumentTypeError(f'invalid interval: {value}, use '
                                         '0 - 255 or force')
    return interval


def cmd_chassis_identify(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.interval == 'force':
        ipmi.chassis_identify(force_on=True)
        print('Chassis identify interval: indefinite')
    elif args.interval is None:
        ipmi.chassis_identify()
        print('Chassis identify interval: default (15 seconds)')
    elif args.interval == 0:
        ipmi.chassis_identify(0)
        print('Chassis identify interval: off')
    else:
        ipmi.chassis_identify(args.interval)
        print(f'Chassis identify interval: {args.interval} seconds')


CHASSIS_POWER_RESTORE_POLICIES = {
    'always-off': pyipmi.chassis.POWER_RESTORE_POLICY_ALWAYS_OFF,
    'previous': pyipmi.chassis.POWER_RESTORE_POLICY_RESTORE_PREVIOUS,
    'always-on': pyipmi.chassis.POWER_RESTORE_POLICY_ALWAYS_ON,
}


def cmd_chassis_policy(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.policy == 'list':
        supported = ipmi.get_supported_power_restore_policies()
    else:
        supported = ipmi.set_power_restore_policy(
            CHASSIS_POWER_RESTORE_POLICIES[args.policy])
        print(f'Set chassis power restore policy to {args.policy}')
    names = [name for name, policy in CHASSIS_POWER_RESTORE_POLICIES.items()
             if policy in supported]
    print(f"Supported chassis power restore policies: {' '.join(names)}")


def cmd_chassis_restart_cause(ipmi: pyipmi.Ipmi,
                              args: argparse.Namespace) -> None:
    restart = ipmi.get_system_restart_cause()
    print(f'System restart cause: {restart}')
    if restart.channel_number is not None:
        print(f'Channel:              {restart.channel_number:d}')


def cmd_chassis_poh(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    poh = ipmi.get_poh_counter()
    days, minutes = divmod(poh.minutes, 24 * 60)
    print(f'POH Counter: {days:d} days, {minutes // 60:d} hours')


def cmd_chassis_capabilities(ipmi: pyipmi.Ipmi,
                             args: argparse.Namespace) -> None:
    caps = ipmi.get_chassis_capabilities()
    bridge = caps.bridge_device_address
    print(f'''
Intrusion Sensor:         {caps.intrusion_sensor}
Front Panel Lockout:      {caps.frontpanel_lockout}
Diagnostic Interrupt:     {caps.diagnostic_interrupt}
Power Interlock:          {caps.power_interlock}
FRU Info Device:          0x{caps.fru_info_device_address:02x}
SDR Device:               0x{caps.sdr_device_address:02x}
SEL Device:               0x{caps.sel_device_address:02x}
System Management Device: 0x{caps.system_management_device_address:02x}
Bridge Device:            {'na' if bridge is None else f'0x{bridge:02x}'}
'''[1:-1])


# the front panel buttons: the argument of 'chassis buttons', the name and
# the bit of the button in the front panel button capabilities of the
# chassis status, whose upper 4 bits tell if the button can be disabled
CHASSIS_BUTTONS = (
    ('power-off', 'Power Off', 0),
    ('reset', 'Reset', 1),
    ('diag', 'Diagnostic Interrupt', 2),
    ('standby', 'Standby', 3),
)


def chassis_button(value: str) -> str:
    """Argument type for a front panel button of 'chassis buttons'."""
    # not argparse choices: with nargs='*', Python < 3.12 checks the empty
    # list against the choices and fails
    buttons = [button for button, _, _ in CHASSIS_BUTTONS]
    if value not in buttons:
        raise argparse.ArgumentTypeError(f"invalid button: {value}, use "
                                         f"{', '.join(buttons)}")
    return value


def cmd_chassis_buttons(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    if args.state is not None and not args.buttons:
        print(f'No button to {args.state} given', file=sys.stderr)
        sys.exit(1)

    capabilities = ipmi.get_chassis_status().front_panel_button_capabilities
    if capabilities is None:
        print('The BMC does not report the front panel buttons',
              file=sys.stderr)
        sys.exit(1)

    if args.state is None:
        for _, name, bit in CHASSIS_BUTTONS:
            state = 'disabled' if capabilities & (1 << bit) else 'enabled'
            if not capabilities & (1 << (bit + 4)):
                state += ' (cannot be disabled)'
            print(f'{name + " Button:":<29}{state}')
        return

    # all buttons are set at once, keep the state of the other buttons
    enabled = {button: not capabilities & (1 << bit)
               for button, _, bit in CHASSIS_BUTTONS}
    for button in args.buttons:
        enabled[button] = args.state == 'enable'
    ipmi.set_front_panel_button_enables(
        power_off=enabled['power-off'], reset=enabled['reset'],
        diagnostic_interrupt=enabled['diag'], standby=enabled['standby'])


def cmd_chassis_cycle_interval(ipmi: pyipmi.Ipmi,
                               args: argparse.Namespace) -> None:
    ipmi.set_power_cycle_interval(args.seconds)


def cmd_picmg_get_power(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    pwr = ipmi.get_power_level(0, 0)
    print(pwr)


def print_link_state(p: pyipmi.picmg.LinkDescriptor | None,
                     s: int | None) -> None:
    if p is None or s is None:
        print('Port not supported')
        return
    intf_str = pyipmi.picmg.LinkDescriptor().get_interface_string(p.interface)
    link_str = pyipmi.picmg.LinkDescriptor().get_link_type_string(
            p.type, p.extension, p.sig_class)
    print(f'CH={p.channel:02d} INTF={p.interface:d} FLAGS=0x{p.link_flags:x} '
          f'TYPE={p.type:d} SIG={p.sig_class:d} EXT={p.extension:d} '
          f'STATE={s:d} ({intf_str}/{link_str})')


def cmd_picmg_get_portstate_all(ipmi: pyipmi.Ipmi,
                                args: argparse.Namespace) -> None:
    for interface in range(3):
        for channel in range(16):
            try:
                (p, s) = ipmi.get_port_state(channel, interface)
                if p is not None:
                    print_link_state(p, s)
            except pyipmi.errors.CompletionCodeError as e:
                if e.cc == 0xcc:
                    continue


def cmd_picmg_get_portstate(ipmi: pyipmi.Ipmi,
                            args: argparse.Namespace) -> None:
    (p, s) = ipmi.get_port_state(args.channel, args.interface)
    print_link_state(p, s)


def cmd_picmg_getpower_channel_status(ipmi: pyipmi.Ipmi,
                                      args: argparse.Namespace) -> None:
    ret = ipmi.get_power_channel_status(args.start)
    pprint.pprint(vars(ret))


def cmd_picmg_frucontrol_cold_reset(ipmi: pyipmi.Ipmi,
                                    args: argparse.Namespace) -> None:
    ipmi.fru_control_cold_reset(0)


def cmd_picmg_send_pm_heartbeat(ipmi: pyipmi.Ipmi,
                                args: argparse.Namespace) -> None:
    ipmi.send_pm_heartbeat()


def cmd_picmg_send_channel_power(ipmi: pyipmi.Ipmi,
                                 args: argparse.Namespace) -> None:
    ipmi.send_channel_power(args.channel, args.state == 'on',
                            args.current_limit)


VITA_LED_COLORS = ('reserved', 'BLUE', 'RED', 'GREEN', 'AMBER', 'ORANGE',
                   'WHITE', 'reserved')

VITA_FRU_CONTROL_OPTIONS = ('Cold Reset', 'Warm Reset', 'Graceful Reboot',
                            'Issue Diagnostic Interrupt')


def _vita_led_color(color: int) -> str:
    if 0 <= color < len(VITA_LED_COLORS):
        return VITA_LED_COLORS[color]
    return 'invalid'


def _vita_led_function(function: int) -> str:
    if function == 0x00:
        return 'OFF'
    if function == 0xff:
        return 'ON'
    return 'BLINKING'


def cmd_vita_properties(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_vso_capabilities()
    ipmc = rsp.ipmc_identifier
    ipmb = rsp.ipmb_capabilities
    rev = rsp.specification_revision
    print(f'VSO Identifier    : 0x{rsp.vita_identifier:02x}')
    print(f'IPMC Identifier   : 0x{int(ipmc):02x}')
    print(f'    Tier  {ipmc.tier_functionality + 1:d}')
    print(f'    Layer {ipmc.layer_functionality + 1:d}')
    print(f'IPMB Capabilities : 0x{int(ipmb):02x}')
    frequency = {0: '100', 1: '400'}.get(ipmb.max_frequency, 'RESERVED')
    print(f'    Frequency  {frequency}kHz')
    print(f"    {ipmb.number_ipmbs + 1:d} IPMB interface"
          f"{'s' if ipmb.number_ipmbs else ''} supported")
    print(f"VSO Standard      : "
          f"{'VITA 46.11' if rsp.vso_standard.standard == 0 else 'RESERVED'}")
    print(f'VSO Spec Revision : {rev & 0xf:d}.{rev >> 4:d}')
    print(f'Max FRU Device ID : 0x{rsp.max_fru_id:02x}')
    print(f'FRU Device ID     : 0x{rsp.ipmc_fru_device_id:02x}')


def cmd_vita_frucontrol(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    name = (VITA_FRU_CONTROL_OPTIONS[args.option]
            if args.option < len(VITA_FRU_CONTROL_OPTIONS) else 'Unknown')
    print(f'FRU Device Id: {args.fru_id:d} FRU Control Option: {name}')
    ipmi.vita_fru_control(args.fru_id, args.option)
    print('FRU Control: ok')


def cmd_vita_addrinfo(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_fru_address_info(args.fru_id)
    print(f'Hardware Address : 0x{rsp.hardware_address:02x}')
    print(f'IPMB-0 Address   : 0x{rsp.ipmb_0_address:02x}')
    print(f'FRU ID           : 0x{rsp.fru_id:02x}')
    print(f'Site ID          : 0x{rsp.site_id:02x}')
    print("Site Type        : "
          f"{pyipmi.vita.VITA_SITE_TYPES.get(rsp.site_type, 'Unknown')}")
    if rsp.address_on_channel_7 is not None:
        print(f'Channel 7 Address: 0x{rsp.address_on_channel_7:02x}')


def cmd_vita_activate(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_activation(args.fru_id)
    print('FRU has been successfully activated')


def cmd_vita_deactivate(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_deactivation(args.fru_id)
    print('FRU has been successfully deactivated')


def cmd_vita_policy_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    policy = ipmi.get_vita_fru_state_policy(args.fru_id).activation_policies
    print(f'FRU State Policy Bits:\t{int(policy):x}h')
    print('    Default-Activation-Locked Policy Bit is '
          f'{policy.default_activation_locked:d}')
    print('    Commanded-Deactivation-Ignored Policy Bit is '
          f'{policy.commanded_deactivation_ignored:d}')
    print('    Deactivation-Locked Policy Bit is '
          f'{policy.deactivation_lock:d}')
    print(f'    Activation-Locked Policy Bit is {policy.activation_lock:d}')


def cmd_vita_policy_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_state_policy(args.fru_id, args.mask, args.value)
    print('FRU state policy bits have been updated')


def cmd_vita_led_prop(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_led_properties(args.fru_id)
    print(f'LED Count:\t   {rsp.led_count:#x}')


def cmd_vita_led_cap(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_led_color_capabilities(args.fru_id, args.led_id)
    capabilities = int(rsp.color_capabilities)
    colors = [VITA_LED_COLORS[i] for i in range(8) if capabilities & (1 << i)]
    print(f"LED Color Capabilities: {', '.join(colors)}")
    print('Default LED Color in')
    print('      LOCAL control:  '
          f'{_vita_led_color(rsp.default_color_local_control.value)}')
    print('      OVERRIDE state: '
          f'{_vita_led_color(rsp.default_color_override_control.value)}')
    if rsp.flags is not None:
        print('LED flags:')
        if rsp.flags & 2:
            print('      [HW RESTRICT]')
        if rsp.flags & 1:
            print('      [PAYLOAD PWR]')


def cmd_vita_led_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_led_state(args.fru_id, args.led_id)
    state = rsp.state
    flags = [name for (bit, name) in ((state.ipmc_control, 'LOCAL CONTROL'),
                                      (state.override, 'OVERRIDE'),
                                      (state.lamp_test, 'LAMPTEST'),
                                      (state.hardware_restrict, 'HW RESTRICT'))
             if bit]
    print("LED states:                   "
          f"{int(state):x}\t{' '.join(f'[{flag}]' for flag in flags)}")

    if state.ipmc_control:
        function = _vita_led_function(rsp.local_control_function)
        color = _vita_led_color(rsp.local_control_color & 7)
        print('  Local Control function:     '
              f'{rsp.local_control_function:x}\t[{function}]')
        print('  Local Control On-Duration:  '
              f'{rsp.local_control_on_duration:x}')
        print('  Local Control Color:        '
              f'{rsp.local_control_color:x}\t[{color}]')

    if (state.override or state.lamp_test) and rsp.override_state is not None:
        function = _vita_led_function(rsp.override_state)
        color = _vita_led_color(rsp.override_color & 7)
        print('  Override function:     '
              f'{rsp.override_state:x}\t[{function}]')
        print(f'  Override On-Duration:  {rsp.override_on_duration:x}')
        print('  Override Color:        '
              f'{rsp.override_color:x}\t[{color}]')
        if state.lamp_test and rsp.lamp_test_duration is not None:
            print(f'  Lamp test duration:    {rsp.lamp_test_duration:x}')


def cmd_vita_led_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_led_state(args.fru_id, args.led_id, args.function,
                            args.duration, args.color)
    print('LED state has been updated')


def parse_interface_options(interface_name: str,
                            options: str | None) -> dict[str, Any]:
    interface_options: dict[str, Any] = {}

    for option in options.split(',') if options else []:
        (name, value) = option.split('=', 1)
        if interface_name == 'aardvark':
            if name == 'serial':
                interface_options['serial_number'] = value
            elif (name, value) == ('pullups', 'on'):
                interface_options['enable_i2c_pullups'] = True
            elif (name, value) == ('pullups', 'off'):
                interface_options['enable_i2c_pullups'] = False
            elif (name, value) == ('power', 'on'):
                interface_options['enable_target_power'] = True
            elif (name, value) == ('power', 'off'):
                interface_options['enable_target_power'] = False
            elif (name, value) == ('fastmode', 'on'):
                interface_options['enable_fastmode'] = True
            elif (name, value) == ('fastmode', 'off'):
                interface_options['enable_fastmode'] = False
            else:
                print(f'Warning: unknown option {name}')
        elif interface_name == 'ipmitool':
            if name == 'interface_type':
                interface_options['interface_type'] = value
            elif name == 'cipher':
                interface_options['cipher'] = value
            elif name == 'retries':
                interface_options['retries'] = int(value)
            elif name == 'timeout':
                interface_options['timeout'] = int(value)
            else:
                print(f'Warning: unknown option {name}')
        elif interface_name == 'ipmbdev':
            if name == 'port':
                interface_options['port'] = value
        elif interface_name == 'ipmidev':
            if name == 'port':
                interface_options['port'] = value
            elif name == 'timeout':
                interface_options['timeout'] = float(value)
            else:
                print(f'Warning: unknown option {name}')
        elif interface_name == 'openipmblink':
            if name == 'port':
                interface_options['port'] = value
            elif name == 'bus':
                interface_options['bus'] = int(value)
            elif name == 'address':
                interface_options['slave_address'] = int(value, 0)
            else:
                print(f'Warning: unknown option {name}')
        elif interface_name == 'rmcpplus':
            if name == 'cipher':
                interface_options['cipher_suite'] = int(value)
            elif name == 'kg':
                interface_options['kg'] = bytes.fromhex(value)
            else:
                print(f'Warning: unknown option {name}')

    return interface_options


def create_ipmi_connection(interface_name: str, options: str | None,
                           target_address: int,
                           target_routing: str | list | None,
                           rmcp_host: str | None, rmcp_port: int,
                           rmcp_user: str, rmcp_password: str,
                           rmcp_priv_level: str | None,
                           target_channel: int | None = None
                           ) -> pyipmi.Ipmi | None:
    interface_options = parse_interface_options(interface_name, options)

    try:
        interface = pyipmi.interfaces.create_interface(interface_name,
                                                       **interface_options)
    except RuntimeError as e:
        print(e)
        return None

    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(target_address)

    if target_channel is not None:
        # like ipmitool -t <addr> -b <channel>: the BMC bridges the request
        # to the target on the channel. The requester address of the first
        # hop is the own address of the interface, e.g. 0x81 for RMCP.
        rq_sa = getattr(interface, 'slave_address', 0x81)
        ipmi.target.set_routing([(rq_sa, 0x20, target_channel),
                                 (0x20, target_address, None)])
    elif target_routing is not None:
        ipmi.target.set_routing(target_routing)

    if rmcp_host is not None:
        ipmi.session.set_session_type_rmcp(rmcp_host, rmcp_port)
        ipmi.session.set_auth_type_user(rmcp_user, rmcp_password)

        if rmcp_priv_level is not None:
            ipmi.session.set_priv_level(rmcp_priv_level)

    return ipmi


INTERFACE_OPTIONS_HELP = '''
interface options (-o name=value,...):
  aardvark:
    serial=<SN>        serial number of the device
    pullups=<on|off>   enable/disable pullups
    power=<on|off>     enable/disable target power
    fastmode=<on|off>  enable/disable 400kHz I2C bitrate (default 100kHz)
  ipmitool:
    interface_type     interface type to be used (lan, lanplus, serial, open)
    cipher             cipher to be used (0-255)
    retries=<n>        number of retries for lan/lanplus (ipmitool -R)
    timeout=<sec>      timeout of each try for lan/lanplus (ipmitool -N)
  ipmbdev:
    port=<path>        path to Linux IPMB device (default /dev/ipmb-0)
  ipmidev:
    port=<path>        path to Linux IPMI device (default /dev/ipmi0)
    timeout=<sec>      response timeout in seconds (default 10)
  openipmblink:
    port=<path>        data serial port of the bridge (default /dev/ttyACM1)
                       or pyserial URL of a shared bridge
                       (e.g. socket://localhost:5555)
    bus=<n>            IPMB bus of the bridge (default 0)
    address=<addr>     own IPMB address (default 0x20)
  rmcpplus:
    cipher=<id>        cipher suite (1, 2, 3, 15, 16, 17; default: try 17,
                       then 3)
    kg=<hex>           BMC key K_G as hex string (default: user password)
'''


DCMI_ENTITY_NAMES = {
    'inlet': pyipmi.constants.ENTITY_ID_DCMI_AIR_INLET,
    'cpu': pyipmi.constants.ENTITY_ID_DCMI_CPU,
    'baseboard': pyipmi.constants.ENTITY_ID_DCMI_BASEBOARD,
}

DCMI_CAPABILITY_PARAMETERS = (
    (pyipmi.dcmi.PARAM_SUPPORTED_DCMI_CAPABILITIES,
     'Supported DCMI capabilities'),
    (pyipmi.dcmi.PARAM_MANDATORY_PLATFORM_ATTRIBUTES,
     'Mandatory platform attributes'),
    (pyipmi.dcmi.PARAM_OPTIONAL_PLATFORM_ATTRIBUTES,
     'Optional platform attributes'),
    (pyipmi.dcmi.PARAM_MANAGEABILITY_ACCESS_ATTRIBUTES,
     'Manageability access attributes'),
    (pyipmi.dcmi.PARAM_ENHANCED_SYSTEM_POWER_STATISTICS_ATTRIBUTES,
     'Enhanced system power statistics attributes'),
)

DCMI_CONFIGURATION_PARAMETERS = {
    pyipmi.dcmi.CONF_PARAM_ACTIVATE_DHCP: 'Activate DHCP',
    pyipmi.dcmi.CONF_PARAM_DISCOVERY_CONFIGURATION: 'Discovery configuration',
    pyipmi.dcmi.CONF_PARAM_DHCP_TIMING_1: 'DHCP timing 1',
    pyipmi.dcmi.CONF_PARAM_DHCP_TIMING_2: 'DHCP timing 2',
    pyipmi.dcmi.CONF_PARAM_DHCP_TIMING_3: 'DHCP timing 3',
}

DCMI_POWER_LIMIT_ACTIONS = {
    'no_action': pyipmi.dcmi.POWER_LIMIT_EXCEPTION_NO_ACTION,
    'power_off': pyipmi.dcmi.POWER_LIMIT_EXCEPTION_HARD_POWER_OFF,
    'sel_logging': pyipmi.dcmi.POWER_LIMIT_EXCEPTION_LOG_EVENT_TO_SEL,
}


def dcmi_entity(value: str) -> int:
    """Argument type for DCMI entities, name or number."""
    if value in DCMI_ENTITY_NAMES:
        return DCMI_ENTITY_NAMES[value]
    try:
        return int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid entity: {value} (use {', '.join(DCMI_ENTITY_NAMES)} or "
            "a number)") from None


def dcmi_entity_name(entity_id: int) -> str:
    for name, value in DCMI_ENTITY_NAMES.items():
        if value == entity_id:
            return name
    return f'0x{entity_id:02x}'


def hex_bytes(data: bytes) -> str:
    return ' '.join(f'{b:02x}' for b in data)


def cmd_dcmi_discover(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for selector, name in DCMI_CAPABILITY_PARAMETERS:
        try:
            rsp = ipmi.get_dcmi_capabilities(selector)
        except pyipmi.errors.CompletionCodeError as e:
            print(f'{name!s:<45}: ERR: CC=0x{e.cc:02x}')
            continue
        conformance = rsp.specification_conformance
        print(f'{name!s:<45}: {hex_bytes(rsp.parameter_data)} (DCMI '
              f'{conformance.major:d}.{conformance.minor:d}, revision '
              f'{rsp.parameter_revision:d})')


def cmd_dcmi_power_reading(ipmi: pyipmi.Ipmi,
                           args: argparse.Namespace) -> None:
    rsp = ipmi.get_power_reading(1)
    print(f'Instantaneous power reading : {rsp.current_power:5d} Watts')
    print(f'Minimum power               : {rsp.minimum_power:5d} Watts')
    print(f'Maximum power               : {rsp.maximum_power:5d} Watts')
    print(f'Average power               : {rsp.average_power:5d} Watts')
    print(f'Timestamp                   : {rsp.timestamp:d}')
    print(f'Sampling period             : {rsp.period:d} ms')
    state = 'activated' if rsp.reading_state & 0x40 else 'deactivated'
    print(f'Power reading state         : {state}')


def cmd_dcmi_power_get_limit(ipmi: pyipmi.Ipmi,
                             args: argparse.Namespace) -> None:
    rsp = ipmi.get_power_limit()
    actions = {v: k for (k, v) in DCMI_POWER_LIMIT_ACTIONS.items()}
    action = actions.get(rsp.exception_actions,
                         f'OEM 0x{rsp.exception_actions:02x}')
    print(f'Exception actions      : {action}')
    print(f'Power limit            : {rsp.power_limit:d} Watts')
    print(f'Correction time        : {rsp.correction_time_limit:d} ms')
    print(f'Sampling period        : {rsp.statistics_sampling_period:d} s')


def cmd_dcmi_power_set_limit(ipmi: pyipmi.Ipmi,
                             args: argparse.Namespace) -> None:
    ipmi.set_power_limit(args.limit, args.correction_time,
                         args.sampling_period,
                         DCMI_POWER_LIMIT_ACTIONS[args.action])


def cmd_dcmi_power_activate(ipmi: pyipmi.Ipmi,
                            args: argparse.Namespace) -> None:
    ipmi.activate_power_limit()


def cmd_dcmi_power_deactivate(ipmi: pyipmi.Ipmi,
                              args: argparse.Namespace) -> None:
    ipmi.deactivate_power_limit()


def cmd_dcmi_sensors(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for record_id in ipmi.get_dcmi_sensor_record_ids():
        try:
            sdr = ipmi.get_repository_sdr(record_id)
            name = getattr(sdr, 'device_id_string', '')
        except (pyipmi.errors.CompletionCodeError,
                pyipmi.errors.DecodingError):
            name = ''
        print(f'0x{record_id:04x} | {name}')


def cmd_dcmi_get_temp_reading(ipmi: pyipmi.Ipmi,
                              args: argparse.Namespace) -> None:
    entities = ([args.entity] if args.entity is not None
                else DCMI_ENTITY_NAMES.values())
    for entity_id in entities:
        try:
            readings = ipmi.get_temperature_readings(entity_id)
        except pyipmi.errors.CompletionCodeError as e:
            print(f'{dcmi_entity_name(entity_id)!s:<10} | ERR: '
                  f'CC=0x{e.cc:02x}')
            continue
        for (instance, temperature) in readings:
            print(f'{dcmi_entity_name(entity_id)!s:<10} | {instance:3d} | '
                  f'{temperature:+4d} C')


def cmd_dcmi_thermalpolicy_get(ipmi: pyipmi.Ipmi,
                               args: argparse.Namespace) -> None:
    rsp = ipmi.get_thermal_limit(args.entity, args.instance)
    actions = rsp.exception_actions
    enabled = 'enabled' if actions.enable else 'disabled'
    hard_power_off = 'active' if actions.hard_power_off else 'inactive'
    log_event_to_sel = 'active' if actions.log_event_to_sel else 'inactive'
    print(f'Exception actions    : {enabled}')
    print(f'  Hard power off     : {hard_power_off}')
    print(f'  Log event to SEL   : {log_event_to_sel}')
    print(f'Temperature limit    : {rsp.temperature_limit:d} C')
    print(f'Exception time       : {rsp.exception_time:d} s')


def cmd_dcmi_thermalpolicy_set(ipmi: pyipmi.Ipmi,
                               args: argparse.Namespace) -> None:
    ipmi.set_thermal_limit(args.entity, args.instance, args.limit,
                           args.exception_time,
                           enable=not args.disable,
                           hard_power_off=args.power_off,
                           log_event_to_sel=args.log_sel)


def cmd_dcmi_asset_tag(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    print(f'Asset tag: {ipmi.get_asset_tag()}')


def cmd_dcmi_set_asset_tag(ipmi: pyipmi.Ipmi,
                           args: argparse.Namespace) -> None:
    ipmi.set_asset_tag(args.asset_tag)


def cmd_dcmi_get_mc_id_string(ipmi: pyipmi.Ipmi,
                              args: argparse.Namespace) -> None:
    print('Management controller ID string: '
          f'{ipmi.get_management_controller_id_string()}')


def cmd_dcmi_set_mc_id_string(ipmi: pyipmi.Ipmi,
                              args: argparse.Namespace) -> None:
    ipmi.set_management_controller_id_string(args.id_string)


def cmd_dcmi_get_conf_param(ipmi: pyipmi.Ipmi,
                            args: argparse.Namespace) -> None:
    selectors = ([args.selector] if args.selector is not None
                 else DCMI_CONFIGURATION_PARAMETERS)
    for selector in selectors:
        name = DCMI_CONFIGURATION_PARAMETERS.get(selector,
                                                 f'Parameter {selector:d}')
        try:
            rsp = ipmi.get_dcmi_configuration_parameters(selector)
        except pyipmi.errors.CompletionCodeError as e:
            print(f'{name!s:<24}: ERR: CC=0x{e.cc:02x}')
            continue
        print(f'{name!s:<24}: {hex_bytes(rsp.parameter_data)}')


def cmd_dcmi_set_conf_param(ipmi: pyipmi.Ipmi,
                            args: argparse.Namespace) -> None:
    # DHCP timing 3 is a 2 byte value, all others are 1 byte values
    length = 2 if args.selector == pyipmi.dcmi.CONF_PARAM_DHCP_TIMING_3 else 1
    ipmi.set_dcmi_configuration_parameters(
        args.selector, args.value.to_bytes(length, 'little'))


class _CommandGroups:
    """Helper to build nested subcommands."""

    def __init__(self, subparsers: argparse._SubParsersAction) -> None:
        self._subparsers = subparsers

    def group(self, name: str, help: str) -> _CommandGroups:
        """Add a command with subcommands, e.g. 'sdr' of 'sdr list'."""
        parser = self._subparsers.add_parser(name, help=help,
                                             description=help)
        parser.set_defaults(func=None, help_parser=parser)
        return _CommandGroups(parser.add_subparsers(metavar='<command>'))

    def command(self, name: str, func: Callable, help: str,
                needs_connection: bool = True) -> argparse.ArgumentParser:
        """Add a command, its arguments are added to the returned parser."""
        parser = self._subparsers.add_parser(name, help=help,
                                             description=help)
        parser.set_defaults(func=func, needs_connection=needs_connection)
        return parser


def logger_names() -> list[str]:
    """Return the names of the pyipmi loggers, relative to 'pyipmi'."""
    return sorted(name.removeprefix('pyipmi.')
                  for name, logger in logging.root.manager.loggerDict.items()
                  if name.startswith('pyipmi.')
                  and isinstance(logger, logging.Logger))


def log_level_help() -> str:
    names = textwrap.fill(', '.join(logger_names()), width=76,
                          initial_indent='  ', subsequent_indent='  ')
    return f'''
loggers (--log-level <logger>=<level>):
{names}
  A parent name sets all its children, e.g. 'interfaces', and without a
  name the level applies to all loggers.
'''


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='ipmitool.py',
        description='Pure python IPMI tool',
        epilog=INTERFACE_OPTIONS_HELP + log_level_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.set_defaults(func=None, help_parser=parser)

    parser.add_argument('-V', '--version', action='version',
                        version=f'ipmitool v{pyipmi.__version__}')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='be verbose')
    parser.add_argument('--log-level', dest='log_levels',
                        metavar='[<logger>=]<level>', type=log_level,
                        action='append', default=[],
                        help='set the log level of a logger, e.g. '
                             'interfaces.aardvark=DEBUG (can be repeated)')
    parser.add_argument('-J', '--json', action='store_true',
                        help='print the output as JSON (if supported)')
    parser.add_argument('-I', dest='interface', metavar='<interface>',
                        help='interface (rmcp, rmcpplus, aardvark, ipmitool, '
                             'ipmbdev, ipmidev, openipmblink)')
    parser.add_argument('-o', dest='options', metavar='<options>',
                        default='',
                        help='interface specific options (name=value, '
                             'separated by commas, see below)')
    parser.add_argument('-t', dest='target', metavar='<addr>', type=auto_int,
                        default=0x20, help='target IPMB address')
    parser.add_argument('-b', dest='channel', metavar='<channel>', type=int,
                        help='target channel')
    parser.add_argument('-r', dest='routing', metavar='<routing>',
                        help='target routing')
    parser.add_argument('-H', dest='host', metavar='<host>', help='RMCP host')
    parser.add_argument('-p', dest='port', metavar='<port>', type=auto_int,
                        default=623, help='RMCP port (default 623)')
    parser.add_argument('-U', dest='user', metavar='<user>', default='',
                        help='RMCP user')
    parser.add_argument('-P', dest='password', metavar='<password>',
                        default='', help='RMCP password')
    parser.add_argument('-L', dest='priv_level', metavar='<level>',
                        type=str.lower,
                        choices=list(pyipmi.session.Session.PRIV_LEVELS),
                        help='RMCP privilege level (user, operator, '
                             'administrator)')

    commands = _CommandGroups(parser.add_subparsers(metavar='<command>'))

    p = commands.command('raw', cmd_raw,
                         'Send a RAW IPMI request and print response')
    p.add_argument('-l', '--lun', type=auto_int, default=0, help='LUN')
    p.add_argument('netfn', type=auto_int)
    p.add_argument('data', type=auto_int, nargs='+',
                   help='command id and data bytes')

    group = commands.group('bmc', 'Management Controller status and '
                           'global enables')
    group.command('info', cmd_bmc_info, 'BMC Device ID information')
    p = group.command('reset', cmd_bmc_reset, 'BMC reset control')
    p.add_argument('type', choices=('cold', 'warm'))

    group = commands.group('chassis', 'Get the chassis status, control the '
                           'power and set the chassis settings')
    group.command('status', cmd_chassis_status, 'Get chassis status')
    p = group.command('power', cmd_chassis_power, 'Set power state')
    p.add_argument('action', choices=tuple(CHASSIS_POWER_CONTROLS))
    group.command('reset', cmd_chassis_reset,
                  'Reset the chassis with the Chassis Reset command')
    p = group.command('identify', cmd_chassis_identify,
                      'Turn on the chassis identification, e.g. an LED')
    p.add_argument('interval', type=identify_interval, nargs='?',
                   metavar='{<seconds>,force}',
                   help='the time in seconds, 0 turns it off, force turns '
                        'it on until it is turned off (default: 15 '
                        'seconds)')
    p = group.command('policy', cmd_chassis_policy,
                      'Set the power restore policy after AC power returns')
    p.add_argument('policy', choices=('list',)
                   + tuple(CHASSIS_POWER_RESTORE_POLICIES),
                   help='list prints the supported policies')
    group.command('restart-cause', cmd_chassis_restart_cause,
                  'Print the cause of the last system restart')
    group.command('poh', cmd_chassis_poh,
                  'Print the power-on hours counter')
    group.command('capabilities', cmd_chassis_capabilities,
                  'Print the chassis capabilities')
    p = group.command('buttons', cmd_chassis_buttons,
                      'Print, enable or disable the front panel buttons')
    p.add_argument('state', choices=('enable', 'disable'), nargs='?',
                   help='print the state of the buttons if not given')
    p.add_argument('buttons', nargs='*', type=chassis_button,
                   metavar='<button>',
                   help='the buttons: '
                        f"{', '.join(b for b, _, _ in CHASSIS_BUTTONS)}")
    p = group.command('cycle-interval', cmd_chassis_cycle_interval,
                      'Set the time the power stays off in a power cycle')
    p.add_argument('seconds', type=auto_int, choices=range(256),
                   metavar='<seconds>', help='0 - 255')

    group = commands.group('fru', 'Print and read built-in FRU')
    p = group.command('print', cmd_fru_print, 'Print FRU inventory')
    p.add_argument('fru_id', type=auto_int, nargs='?', default=0)
    p.add_argument('all', nargs='?', choices=('all',),
                   help='also print the multirecord area')
    p = group.command('read', cmd_fru_read,
                      'Read the FRU data and write it to a file')
    p.add_argument('fru_id', type=auto_int)
    p.add_argument('filename', help='file to write the FRU data to')
    p = group.command('print-file', cmd_fru_print_file,
                      'Print the FRU inventory of a file',
                      needs_connection=False)
    p.add_argument('filename', help='file with the FRU data, e.g. written '
                                    'by "fru read"')
    p.add_argument('all', nargs='?', choices=('all',),
                   help='also print the multirecord area')

    group = commands.group('lan', 'Print and set the LAN configuration')
    lan_channel_help = 'the LAN channel, the first LAN channel if not given'
    p = group.command('print', cmd_lan_print, 'Print the LAN configuration')
    p.add_argument('lan_channel', metavar='channel', type=auto_int, nargs='?',
                   help=lan_channel_help)
    sub = group.group('set', 'Set the LAN configuration')
    p = sub.command('ipaddr', cmd_lan_set_ipaddr, 'Set the IP address')
    p.add_argument('address', type=ipv4_address,
                   help='the IP address, xxx.xxx.xxx.xxx')
    p.add_argument('lan_channel', metavar='channel', type=auto_int, nargs='?',
                   help=lan_channel_help)
    p = sub.command('ipsrc', cmd_lan_set_ipsrc, 'Set the IP address source')
    p.add_argument('source', choices=('static', 'dhcp'))
    p.add_argument('lan_channel', metavar='channel', type=auto_int, nargs='?',
                   help=lan_channel_help)
    p = sub.command('vlan', cmd_lan_set_vlan, 'Set the 802.1q VLAN ID')
    p.add_argument('vlan', type=vlan_id, metavar='{<id>,off}',
                   help='the VLAN ID 1 - 4095, off to disable the VLAN')
    p.add_argument('lan_channel', metavar='channel', type=auto_int, nargs='?',
                   help=lan_channel_help)

    group = commands.group('sdr', 'Print and manage the Sensor Data '
                           'Repository (SDR) and the sensor readings')
    p = group.command('list', cmd_sdr_list, 'List all SDRs')
    p.add_argument('-d', '--details', action='store_true',
                   help='print all fields of the records')
    p = group.command('raw', cmd_sdr_show_raw, 'Show SDR raw data')
    p.add_argument('sdr_id', type=auto_int)
    p = group.command('show', cmd_sdr_show, 'Show detail for one SDR')
    p.add_argument('sdr_id', type=auto_int)
    group.command('showall', cmd_sdr_show_all, 'Show detail for all SDRs')
    group.command('info', cmd_sdr_info,
                  'Print the information about the SDR repository')
    p = group.command('device-info', cmd_sdr_device_info,
                      'Print the information about the device SDRs')
    p.add_argument('-c', '--sdr-count', action='store_true',
                   help='print the number of SDRs instead of sensors')
    sub = group.group('time', 'Get or set the SDR repository time (UTC)')
    sub.command('get', cmd_sdr_time_get, 'Print the SDR repository time')
    p = sub.command('set', cmd_sdr_time_set, 'Set the SDR repository time')
    p.add_argument('time', type=sel_time,
                   metavar='{"YYYY-MM-DD HH:MM:SS",now}',
                   help='the time in UTC, or now for the time of this host')
    p = group.command('add', cmd_sdr_add,
                      'Add a record to the SDR repository')
    p.add_argument('record_data', type=byte_value, nargs='+',
                   metavar='<byte>',
                   help='the record, starting with the record header; the '
                        'BMC sets the record ID')
    p.add_argument('-p', '--part-size', type=auto_int, metavar='<bytes>',
                   help='send the record in parts of this size (Partial Add '
                        'SDR)')
    p = group.command('delete', cmd_sdr_delete,
                      'Delete records of the SDR repository')
    p.add_argument('record_ids', type=auto_int, nargs='+',
                   metavar='<record id>')
    p = group.command('update-mode', cmd_sdr_update_mode,
                      'Enter or exit the SDR repository update mode')
    p.add_argument('mode', choices=('enter', 'exit'))

    group = commands.group('sel', 'Print and manage the System Event '
                           'Log (SEL)')
    p = group.command('list', cmd_sel_list, 'List all SEL entries')
    p.add_argument('-d', '--details', action='store_true',
                   help='print all fields of the entries')
    p.add_argument('-s', '--sdr', action='store_true',
                   help='read the SDRs to print the sensor names and the '
                        'converted values of threshold events')
    group.command('clear', cmd_sel_clear, 'Clear SEL')
    group.command('info', cmd_sel_info,
                  'Print the information about the SEL')
    sub = group.group('time', 'Get or set the SEL time (UTC)')
    sub.command('get', cmd_sel_time_get, 'Print the SEL time')
    p = sub.command('set', cmd_sel_time_set, 'Set the SEL time')
    p.add_argument('time', type=sel_time,
                   metavar='{"YYYY-MM-DD HH:MM:SS",now}',
                   help='the time in UTC, or now for the time of this host')
    p = group.command('utc-offset', cmd_sel_utc_offset,
                      'Print or set the offset of the SEL time to UTC')
    p.add_argument('offset', type=utc_offset, nargs='?',
                   metavar='{<minutes>,unspecified}',
                   help='-1440 - 1440, print the offset if not given')
    p = group.command('get', cmd_sel_get,
                      'Print the details of SEL entries')
    p.add_argument('record_ids', type=auto_int, nargs='+',
                   metavar='<record id>')
    p.add_argument('-s', '--sdr', action='store_true',
                   help='read the SDRs to print the sensor names and the '
                        'converted values of threshold events')
    p = group.command('add', cmd_sel_add, 'Add an entry to the SEL')
    p.add_argument('record_data', type=byte_value, nargs=16,
                   metavar='<byte>',
                   help='the 16 bytes of the record, the BMC sets the record '
                        'ID and the timestamp')
    p.add_argument('-p', '--partial', action='store_true',
                   help='send the record in parts (Partial Add SEL Entry)')
    p = group.command('delete', cmd_sel_delete, 'Delete SEL entries')
    p.add_argument('record_ids', type=auto_int, nargs='+',
                   metavar='<record id>')
    p = group.command('aux-status', cmd_sel_aux_status,
                      'Print the status data of an auxiliary log')
    p.add_argument('log', choices=tuple(SEL_AUXILIARY_LOGS))

    group = commands.group('sensor', 'Sensor commands')
    p = group.command('rearm', cmd_sensor_rearm, 'Rearm sensor events')
    p.add_argument('number', type=auto_int, help='sensor number')

    def sensor_command(name: str, func: Callable,
                       help: str) -> argparse.ArgumentParser:
        p = group.command(name, func, help)
        p.add_argument('number', type=auto_int, help='sensor number')
        p.add_argument('-l', '--lun', type=auto_int, default=0,
                       help='LUN of the sensor owner (default 0)')
        return p

    p = sensor_command('type', cmd_sensor_type,
                       'Print or set the sensor type')
    p.add_argument('-s', '--set', dest='type', nargs=2, type=byte_value,
                   metavar=('<sensor type>', '<event/reading type>'),
                   help='set the sensor type and the event/reading type')
    p = sensor_command('hysteresis', cmd_sensor_hysteresis,
                       'Print or set the hysteresis of a threshold sensor')
    p.add_argument('-s', '--set', dest='hysteresis', nargs=2,
                   type=byte_value, metavar=('<positive>', '<negative>'),
                   help='set the raw positive- and negative-going '
                        'hysteresis')
    p = sensor_command('events', cmd_sensor_events,
                       'Print the enabled and the asserted events, enable '
                       'or disable the event messages and the scanning')
    p.add_argument('-m', '--messages', choices=('on', 'off'),
                   help='enable or disable the event messages')
    p.add_argument('-s', '--scanning', choices=('on', 'off'),
                   help='enable or disable the sensor scanning')
    p = sensor_command('factors', cmd_sensor_factors,
                       'Print the conversion factors for a raw reading')
    p.add_argument('reading', type=byte_value, help='raw reading')
    p = sensor_command('set-reading', cmd_sensor_set_reading,
                       'Set the reading of a sensor (Set Sensor Reading and '
                       'Event Status)')
    p.add_argument('reading', type=byte_value, help='raw reading')

    group = commands.group('hpm', 'HPM.1 commands')
    group.command('capabilities', cmd_hpm_capabilities,
                  'Request the target upgrade capabilities')
    p = group.command('check', cmd_hpm_check_file,
                      'Check the specified HPM.1 file',
                      needs_connection=False)
    p.add_argument('file')
    p = group.command('install', cmd_hpm_install,
                      'Install the specified HPM.1 file to the controller')
    p.add_argument('file')
    p.add_argument('component_id', type=int)

    group = commands.group('picmg', 'PICMG commands')
    sub = group.group('frucontrol', 'FRU control')
    sub.command('cr', cmd_picmg_frucontrol_cold_reset, 'Cold reset')
    sub = group.group('power', 'Power level')
    sub.command('get', cmd_picmg_get_power, 'Request the power level')
    sub = group.group('portstate', 'Port state')
    p = sub.command('get', cmd_picmg_get_portstate,
                    'Request the port state for an interface')
    p.add_argument('channel', type=auto_int)
    p.add_argument('interface', type=auto_int)
    sub.command('getall', cmd_picmg_get_portstate_all,
                'Request all port states for all interfaces')
    sub = group.group('channel', 'Power channel')
    p = sub.command('status', cmd_picmg_getpower_channel_status,
                    'Request the power channel status')
    p.add_argument('start', type=auto_int, help='starting power channel')
    p = sub.command('power', cmd_picmg_send_channel_power,
                    'Send channel power')
    p.add_argument('channel', type=auto_int)
    p.add_argument('state', choices=('on', 'off'),
                   help='enable or disable the payload power')
    p.add_argument('current_limit', type=float,
                   help='current limit in amperes')
    sub = group.group('send', 'Send')
    sub.command('heartbeat', cmd_picmg_send_pm_heartbeat,
                'Send PM heartbeat')

    group = commands.group('dcmi', 'Data Center Manageability Interface '
                           '(DCMI) commands')
    group.command('discover', cmd_dcmi_discover,
                  'Discover the supported DCMI capabilities')
    group.command('sensors', cmd_dcmi_sensors,
                  'List the DCMI temperature sensors')
    p = group.command('get_temp_reading', cmd_dcmi_get_temp_reading,
                      'Get the temperature readings')
    p.add_argument('entity', type=dcmi_entity, nargs='?',
                   help='inlet, cpu, baseboard or entity ID '
                        '(default: all DCMI entities)')

    sub = group.group('power', 'Platform power management')
    sub.command('reading', cmd_dcmi_power_reading,
                'Get the power reading')
    sub.command('get_limit', cmd_dcmi_power_get_limit,
                'Get the power limit')
    p = sub.command('set_limit', cmd_dcmi_power_set_limit,
                    'Set the power limit')
    p.add_argument('limit', type=auto_int, help='power limit in watts')
    p.add_argument('correction_time', type=auto_int,
                   help='correction time limit in milliseconds')
    p.add_argument('sampling_period', type=auto_int,
                   help='statistics sampling period in seconds')
    p.add_argument('--action', choices=tuple(DCMI_POWER_LIMIT_ACTIONS),
                   default='no_action',
                   help='exception action (default: no_action)')
    sub.command('activate', cmd_dcmi_power_activate,
                'Activate the power limit')
    sub.command('deactivate', cmd_dcmi_power_deactivate,
                'Deactivate the power limit')

    sub = group.group('thermalpolicy', 'Thermal limit policy')
    p = sub.command('get', cmd_dcmi_thermalpolicy_get,
                    'Get the thermal limit')
    p.add_argument('entity', type=dcmi_entity,
                   help='inlet, cpu, baseboard or entity ID')
    p.add_argument('instance', type=auto_int, help='entity instance')
    p = sub.command('set', cmd_dcmi_thermalpolicy_set,
                    'Set the thermal limit')
    p.add_argument('entity', type=dcmi_entity,
                   help='inlet, cpu, baseboard or entity ID')
    p.add_argument('instance', type=auto_int, help='entity instance')
    p.add_argument('limit', type=auto_int,
                   help='temperature limit in degree Celsius')
    p.add_argument('exception_time', type=auto_int,
                   help='exception time in seconds')
    p.add_argument('--power-off', action='store_true',
                   help='hard power off and log event to SEL')
    p.add_argument('--log-sel', action='store_true',
                   help='log event to SEL only')
    p.add_argument('--disable', action='store_true',
                   help='disable the exception actions')

    group.command('asset_tag', cmd_dcmi_asset_tag, 'Get the asset tag')
    p = group.command('set_asset_tag', cmd_dcmi_set_asset_tag,
                      'Set the asset tag')
    p.add_argument('asset_tag')
    group.command('get_mc_id_string', cmd_dcmi_get_mc_id_string,
                  'Get the management controller identifier string')
    p = group.command('set_mc_id_string', cmd_dcmi_set_mc_id_string,
                      'Set the management controller identifier string')
    p.add_argument('id_string')

    p = group.command('get_conf_param', cmd_dcmi_get_conf_param,
                      'Get the DCMI configuration parameters')
    p.add_argument('selector', type=auto_int, nargs='?',
                   help='parameter selector (default: all)')
    p = group.command('set_conf_param', cmd_dcmi_set_conf_param,
                      'Set a DCMI configuration parameter')
    p.add_argument('selector', type=auto_int,
                   choices=tuple(DCMI_CONFIGURATION_PARAMETERS),
                   help='1: activate DHCP, 2: discovery configuration, '
                        '3-5: DHCP timing 1-3')
    p.add_argument('value', type=auto_int)

    group = commands.group('vita', 'VITA 46.11 commands')
    group.command('properties', cmd_vita_properties, 'Get VSO properties')
    p = group.command('frucontrol', cmd_vita_frucontrol, 'FRU control')
    p.add_argument('fru_id', type=auto_int)
    p.add_argument('option', type=auto_int,
                   help='0: cold reset, 1: warm reset, 2: graceful reboot, '
                        '3: diagnostic interrupt')
    p = group.command('addrinfo', cmd_vita_addrinfo,
                      'Get address information')
    p.add_argument('fru_id', type=auto_int, nargs='?', default=0)
    p = group.command('activate', cmd_vita_activate, 'Activate a FRU')
    p.add_argument('fru_id', type=auto_int)
    p = group.command('deactivate', cmd_vita_deactivate, 'Deactivate a FRU')
    p.add_argument('fru_id', type=auto_int)

    sub = group.group('policy', 'FRU state policy bits')
    p = sub.command('get', cmd_vita_policy_get,
                    'Get the FRU activation policy')
    p.add_argument('fru_id', type=auto_int)
    p = sub.command('set', cmd_vita_policy_set,
                    'Set the FRU activation policy')
    p.add_argument('fru_id', type=auto_int)
    policy_bits = ('bit 0: activation locked, 1: deactivation locked, '
                   '2: commanded deactivation ignored, '
                   '3: default activation locked')
    p.add_argument('mask', type=auto_int,
                   help=f'policy bits to change ({policy_bits})')
    p.add_argument('value', type=auto_int, help='new policy bits')

    sub = group.group('led', 'FRU LED commands')
    p = sub.command('prop', cmd_vita_led_prop, 'Get LED properties')
    p.add_argument('fru_id', type=auto_int)
    for name, func, help in (
            ('cap', cmd_vita_led_cap, 'Get LED color capabilities'),
            ('get', cmd_vita_led_get, 'Get LED state')):
        p = sub.command(name, func, help)
        p.add_argument('fru_id', type=auto_int)
        p.add_argument('led_id', type=auto_int)
    p = sub.command('set', cmd_vita_led_set, 'Set LED state')
    p.add_argument('fru_id', type=auto_int)
    p.add_argument('led_id', type=auto_int,
                   help='0-0xfe: LED, 0xff: all LEDs')
    p.add_argument('function', type=auto_int,
                   help='0: off, 1-250: blinking (off duration), '
                        '251: lamp test, 252: local control, 255: on')
    p.add_argument('duration', type=auto_int,
                   help='lamp test or on duration')
    p.add_argument('color', type=auto_int,
                   help='1: blue, 2: red, 3: green, 4: amber, 5: orange, '
                        '6: white, 0xe: do not change, 0xf: default')

    return parser


def setup_logging(verbose: bool,
                  log_levels: list[tuple[str, int]]) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    pyipmi.logger.add_log_handler(handler)
    pyipmi.logger.set_log_level(logging.DEBUG if verbose else logging.INFO)
    for name, level in log_levels:
        logging.getLogger(name).setLevel(level)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.func is None:
        args.help_parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose, args.log_levels)

    ipmi = None
    if args.needs_connection:
        ipmi = create_ipmi_connection(args.interface, args.options,
                                      args.target, args.routing,
                                      args.host, args.port, args.user,
                                      args.password, args.priv_level,
                                      args.channel)
        if ipmi is None:
            sys.exit(1)  # interface could not be created, error is printed

    try:
        if ipmi is not None:
            ipmi.open()  # this will open interface and session
        args.func(ipmi, args)
    except pyipmi.errors.CompletionCodeError as e:
        print(f'Command returned with completion code 0x{e.cc:02x}')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except pyipmi.errors.IpmiTimeoutError:
        print('Command timed out')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except pyipmi.errors.IpmiConnectionError as e:
        print(f'Connection error: {e}')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except pyipmi.errors.HpmError as e:
        print(f'HPM error: {e}')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    finally:
        if ipmi is not None:
            ipmi.close()  # this will close interface and session


if __name__ == '__main__':
    main()
