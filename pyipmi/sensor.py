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
    Print the value of the temperature sensors whose name starts with
    ``CPU``::

        for record in ipmi.find_sensors(name='CPU*',
                                        sensor_type='temperature'):
            reading = ipmi.read_sensor(record)
            print(reading.name, reading.value, reading.unit)
"""

from __future__ import annotations

from array import array
from collections.abc import Generator, Iterator
from fnmatch import fnmatchcase

from .errors import NotSupportedError
from .utils import check_rsp_completion_code, ByteSequence
from .msgs import create_request_by_name, Message
from .state import State

from .helper import (get_sdr_data_helper, get_sdr_chunk_helper,
                     ReadLength)

from . import sdr
from .mixin import IpmiMixin


# The operations on the event status bits of
# Sensor.set_sensor_reading_and_event_status
EVENT_BITS_SET = 1
EVENT_BITS_CLEAR = 2
EVENT_BITS_WRITE = 3

# Generator ID of system management software (software ID 0x20), sent in a
# Platform Event request over the system interface
GENERATOR_ID_SMS = 0x41

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

# Names of the sensor types (IPMI v2.0 table 42-3, PICMG 3.0 table 3-3)
SENSOR_TYPE_NAMES = {
    0x01: 'Temperature',
    0x02: 'Voltage',
    0x03: 'Current',
    0x04: 'Fan',
    0x05: 'Physical Security',
    0x06: 'Platform Security',
    0x07: 'Processor',
    0x08: 'Power Supply',
    0x09: 'Power Unit',
    0x0a: 'Cooling Device',
    0x0b: 'Other Units-based Sensor',
    0x0c: 'Memory',
    0x0d: 'Drive Slot / Bay',
    0x0e: 'POST Memory Resize',
    0x0f: 'System Firmware Progress',
    0x10: 'Event Logging Disabled',
    0x11: 'Watchdog 1',
    0x12: 'System Event',
    0x13: 'Critical Interrupt',
    0x14: 'Button / Switch',
    0x15: 'Module / Board',
    0x16: 'Microcontroller / Coprocessor',
    0x17: 'Add-in Card',
    0x18: 'Chassis',
    0x19: 'Chip Set',
    0x1a: 'Other FRU',
    0x1b: 'Cable / Interconnect',
    0x1c: 'Terminator',
    0x1d: 'System Boot / Restart Initiated',
    0x1e: 'Boot Error',
    0x1f: 'Base OS Boot / Installation Status',
    0x20: 'OS Stop / Shutdown',
    0x21: 'Slot / Connector',
    0x22: 'System ACPI Power State',
    0x23: 'Watchdog 2',
    0x24: 'Platform Alert',
    0x25: 'Entity Presence',
    0x26: 'Monitor ASIC / IC',
    0x27: 'LAN',
    0x28: 'Management Subsystem Health',
    0x29: 'Battery',
    0x2a: 'Session Audit',
    0x2b: 'Version Change',
    0x2c: 'FRU State',
    0xf0: 'FRU Hot Swap',
    0xf1: 'IPMB Physical Link',
    0xf2: 'Module Hot Swap',
    0xf3: 'Power Channel Notification',
    0xf4: 'Telco Alarm Input',
}

# The event offsets of the generic event/reading types (IPMI v2.0 table
# 42-2), by event/reading type
GENERIC_EVENT_STRINGS = {
    0x01: ('Lower Non-critical going low',
           'Lower Non-critical going high',
           'Lower Critical going low',
           'Lower Critical going high',
           'Lower Non-recoverable going low',
           'Lower Non-recoverable going high',
           'Upper Non-critical going low',
           'Upper Non-critical going high',
           'Upper Critical going low',
           'Upper Critical going high',
           'Upper Non-recoverable going low',
           'Upper Non-recoverable going high'),
    0x02: ('Transition to Idle',
           'Transition to Active',
           'Transition to Busy'),
    0x03: ('State Deasserted',
           'State Asserted'),
    0x04: ('Predictive Failure deasserted',
           'Predictive Failure asserted'),
    0x05: ('Limit Not Exceeded',
           'Limit Exceeded'),
    0x06: ('Performance Met',
           'Performance Lags'),
    0x07: ('Transition to OK',
           'Transition to Non-Critical from OK',
           'Transition to Critical from less severe',
           'Transition to Non-recoverable from less severe',
           'Transition to Non-Critical from more severe',
           'Transition to Critical from Non-recoverable',
           'Transition to Non-recoverable',
           'Monitor',
           'Informational'),
    0x08: ('Device Absent',
           'Device Present'),
    0x09: ('Device Disabled',
           'Device Enabled'),
    0x0a: ('Transition to Running',
           'Transition to In Test',
           'Transition to Power Off',
           'Transition to On Line',
           'Transition to Off Line',
           'Transition to Off Duty',
           'Transition to Degraded',
           'Transition to Power Save',
           'Install Error'),
    0x0b: ('Fully Redundant',
           'Redundancy Lost',
           'Redundancy Degraded',
           'Non-redundant: Sufficient Resources from Redundant',
           'Non-redundant: Sufficient Resources from Insufficient Resources',
           'Non-redundant: Insufficient Resources',
           'Redundancy Degraded from Fully Redundant',
           'Redundancy Degraded from Non-redundant'),
    0x0c: ('D0 Power State',
           'D1 Power State',
           'D2 Power State',
           'D3 Power State'),
}

_FRU_STATES = ('M0 - FRU Not Installed',
               'M1 - FRU Inactive',
               'M2 - FRU Activation Request',
               'M3 - FRU Activation In Progress',
               'M4 - FRU Active',
               'M5 - FRU Deactivation Request',
               'M6 - FRU Deactivation In Progress',
               'M7 - FRU Communication Lost')

# The event offsets of the sensor-specific event/reading type 0x6f (IPMI
# v2.0 table 42-3, PICMG 3.0 table 3-3), by sensor type. None marks a
# reserved offset.
SENSOR_SPECIFIC_EVENT_STRINGS = {
    0x05: ('General Chassis Intrusion',
           'Drive Bay Intrusion',
           'I/O Card Area Intrusion',
           'Processor Area Intrusion',
           'LAN Leash Lost',
           'Unauthorized Dock',
           'Fan Area Intrusion'),
    0x06: ('Secure Mode Violation Attempt',
           'Pre-boot Password Violation - User Password',
           'Pre-boot Password Violation - Setup Password',
           'Pre-boot Password Violation - Network Boot Password',
           'Other Pre-boot Password Violation',
           'Out-of-band Access Password Violation'),
    0x07: ('IERR',
           'Thermal Trip',
           'FRB1/BIST Failure',
           'FRB2/Hang in POST Failure',
           'FRB3/Processor Startup/Initialization Failure',
           'Configuration Error',
           'SM BIOS Uncorrectable CPU-complex Error',
           'Processor Presence Detected',
           'Processor Disabled',
           'Terminator Presence Detected',
           'Processor Automatically Throttled',
           'Machine Check Exception (Uncorrectable)',
           'Correctable Machine Check Error'),
    0x08: ('Presence Detected',
           'Power Supply Failure Detected',
           'Predictive Failure',
           'Power Supply Input Lost (AC/DC)',
           'Power Supply Input Lost or Out-of-range',
           'Power Supply Input Out-of-range, but Present',
           'Configuration Error',
           'Power Supply Inactive'),
    0x09: ('Power Off / Power Down',
           'Power Cycle',
           '240VA Power Down',
           'Interlock Power Down',
           'AC Lost / Power Input Lost',
           'Soft Power Control Failure',
           'Power Unit Failure Detected',
           'Predictive Failure'),
    0x0c: ('Correctable ECC / Other Correctable Memory Error',
           'Uncorrectable ECC / Other Uncorrectable Memory Error',
           'Parity',
           'Memory Scrub Error',
           'Memory Device Disabled',
           'Correctable ECC / Other Correctable Memory Error Logging Limit '
           'Reached',
           'Presence Detected',
           'Configuration Error',
           'Spare',
           'Memory Automatically Throttled',
           'Critical Overtemperature'),
    0x0d: ('Drive Presence',
           'Drive Fault',
           'Predictive Failure',
           'Hot Spare',
           'Consistency Check / Parity Check in Progress',
           'In Critical Array',
           'In Failed Array',
           'Rebuild/Remap in Progress',
           'Rebuild/Remap Aborted'),
    0x0f: ('System Firmware Error (POST Error)',
           'System Firmware Hang',
           'System Firmware Progress'),
    0x10: ('Correctable Memory Error Logging Disabled',
           'Event Type Logging Disabled',
           'Log Area Reset/Cleared',
           'All Event Logging Disabled',
           'SEL Full',
           'SEL Almost Full',
           'Correctable Machine Check Error Logging Disabled'),
    0x11: ('BIOS Watchdog Reset',
           'OS Watchdog Reset',
           'OS Watchdog Shut Down',
           'OS Watchdog Power Down',
           'OS Watchdog Power Cycle',
           'OS Watchdog NMI / Diagnostic Interrupt',
           'OS Watchdog Expired, Status Only',
           'OS Watchdog Pre-timeout Interrupt, non-NMI'),
    0x12: ('System Reconfigured',
           'OEM System Boot Event',
           'Undetermined System Hardware Failure',
           'Entry Added to Auxiliary Log',
           'PEF Action',
           'Timestamp Clock Synch'),
    0x13: ('Front Panel NMI / Diagnostic Interrupt',
           'Bus Timeout',
           'I/O Channel Check NMI',
           'Software NMI',
           'PCI PERR',
           'PCI SERR',
           'EISA Fail Safe Timeout',
           'Bus Correctable Error',
           'Bus Uncorrectable Error',
           'Fatal NMI',
           'Bus Fatal Error',
           'Bus Degraded'),
    0x14: ('Power Button Pressed',
           'Sleep Button Pressed',
           'Reset Button Pressed',
           'FRU Latch Open',
           'FRU Service Request Button'),
    0x19: ('Soft Power Control Failure',
           'Thermal Trip'),
    0x1b: ('Cable/Interconnect is Connected',
           'Configuration Error - Incorrect Cable Connected / Incorrect '
           'Interconnection'),
    0x1d: ('Initiated by Power Up',
           'Initiated by Hard Reset',
           'Initiated by Warm Reset',
           'User Requested PXE Boot',
           'Automatic Boot to Diagnostic',
           'OS / Run-time Software Initiated Hard Reset',
           'OS / Run-time Software Initiated Warm Reset',
           'System Restart'),
    0x1e: ('No Bootable Media',
           'Non-bootable Diskette Left in Drive',
           'PXE Server Not Found',
           'Invalid Boot Sector',
           'Timeout Waiting for User Selection of Boot Source'),
    0x1f: ('A: Boot Completed',
           'C: Boot Completed',
           'PXE Boot Completed',
           'Diagnostic Boot Completed',
           'CD-ROM Boot Completed',
           'ROM Boot Completed',
           'Boot Completed - Boot Device Not Specified',
           'Base OS/Hypervisor Installation Started',
           'Base OS/Hypervisor Installation Completed',
           'Base OS/Hypervisor Installation Aborted',
           'Base OS/Hypervisor Installation Failed'),
    0x20: ('Critical Stop During OS Load / Initialization',
           'Run-time Critical Stop',
           'OS Graceful Stop',
           'OS Graceful Shutdown',
           'Soft Shutdown Initiated by PEF',
           'Agent Not Responding'),
    0x21: ('Fault Status Asserted',
           'Identify Status Asserted',
           'Slot / Connector Device Installed/Attached',
           'Slot / Connector Ready for Device Installation',
           'Slot / Connector Ready for Device Removal',
           'Slot Power is Off',
           'Slot / Connector Device Removal Request',
           'Interlock Asserted',
           'Slot is Disabled',
           'Slot Holds Spare Device'),
    0x22: ('S0/G0 Working',
           'S1 Sleeping with System H/W & Processor Context Maintained',
           'S2 Sleeping, Processor Context Lost',
           'S3 Sleeping, Processor & H/W Context Lost, Memory Retained',
           'S4 Non-volatile Sleep / Suspend-to-disk',
           'S5/G2 Soft-off',
           'S4/S5 Soft-off, Particular S4/S5 State Cannot Be Determined',
           'G3/Mechanical Off',
           'Sleeping in an S1, S2, or S3 State',
           'G1 Sleeping',
           'S5 Entered by Override',
           'Legacy ON State',
           'Legacy OFF State',
           None,
           'Unknown'),
    0x23: ('Timer Expired, Status Only',
           'Hard Reset',
           'Power Down',
           'Power Cycle',
           None,
           None,
           None,
           None,
           'Timer Interrupt'),
    0x24: ('Platform Generated Page',
           'Platform Generated LAN Alert',
           'Platform Event Trap Generated',
           'Platform Generated SNMP Trap'),
    0x25: ('Entity Present',
           'Entity Absent',
           'Entity Disabled'),
    0x27: ('LAN Heartbeat Lost',
           'LAN Heartbeat'),
    0x28: ('Sensor Access Degraded or Unavailable',
           'Controller Access Degraded or Unavailable',
           'Management Controller Off-line',
           'Management Controller Unavailable',
           'Sensor Failure',
           'FRU Failure'),
    0x29: ('Battery Low (Predictive Failure)',
           'Battery Failed',
           'Battery Presence Detected'),
    0x2a: ('Session Activated',
           'Session Deactivated',
           'Invalid Username or Password',
           'Invalid Password Disable'),
    0x2b: ('Hardware Change Detected',
           'Firmware or Software Change Detected',
           'Hardware Incompatibility Detected',
           'Firmware or Software Incompatibility Detected',
           'Invalid or Unsupported Hardware Version',
           'Invalid or Unsupported Firmware or Software Version',
           'Hardware Change Detected Was Successful',
           'Software or Firmware Change Detected Was Successful'),
    0x2c: ('FRU Not Installed',
           'FRU Inactive',
           'FRU Activation Requested',
           'FRU Activation In Progress',
           'FRU Active',
           'FRU Deactivation Requested',
           'FRU Deactivation In Progress',
           'FRU Communication Lost'),
    0xf0: _FRU_STATES,
    0xf2: ('Module Handle Closed',
           'Module Handle Opened',
           'Quiesced',
           'Backend Power Failure',
           'Backend Power Shut Down'),
}


def sensor_type_to_string(sensor_type: int) -> str:
    """Return the name of a sensor type.

    Args:
        sensor_type: The sensor type.

    Returns:
        The name of the sensor type, the type as hex number for an unknown
        or OEM type.
    """
    name = SENSOR_TYPE_NAMES.get(sensor_type)
    if name is None:
        if sensor_type >= 0xc0:
            return f'OEM (0x{sensor_type:02x})'
        return f'Unknown (0x{sensor_type:02x})'
    return name


def event_reading_type_to_string(event_reading_type: int) -> str:
    """Return the name of an event/reading type.

    Args:
        event_reading_type: The event/reading type.

    Returns:
        'Threshold', 'Generic Discrete', 'Sensor-specific', 'OEM' or
        'Unspecified'.
    """
    if event_reading_type == EVENT_READING_TYPE_CODE_THRESHOLD:
        return 'Threshold'
    if event_reading_type in GENERIC_EVENT_STRINGS:
        return 'Generic Discrete'
    if event_reading_type == EVENT_READING_TYPE_SENSOR_SPECIFIC:
        return 'Sensor-specific'
    if 0x70 <= event_reading_type <= 0x7f:
        return 'OEM'
    return 'Unspecified'


def event_offset_to_string(event_reading_type: int, sensor_type: int,
                           offset: int) -> str | None:
    """Return the description of an event offset or discrete state.

    The offset is looked up in the generic event offsets of the
    event/reading type, or in the sensor-specific offsets of the sensor
    type for the event/reading type ``EVENT_READING_TYPE_SENSOR_SPECIFIC``.

    Args:
        event_reading_type: The event/reading type.
        sensor_type: The sensor type.
        offset: The event offset, or the bit number of a discrete state.

    Returns:
        The description, None for an unknown offset.
    """
    if event_reading_type == EVENT_READING_TYPE_SENSOR_SPECIFIC:
        strings = SENSOR_SPECIFIC_EVENT_STRINGS.get(sensor_type)
    else:
        strings = GENERIC_EVENT_STRINGS.get(event_reading_type)
    if strings is None or offset >= len(strings):
        return None
    return strings[offset]


def _normalize_type_name(name: str) -> str:
    # 'Drive Slot / Bay', 'drive-slot-bay' and 'drive_slot_bay' are equal
    return ''.join(c for c in name.lower() if c.isalnum())


def sensor_type_from_string(name: str) -> int:
    """Return the sensor type of a name.

    Case, spaces and punctuation are ignored, e.g. ``'temperature'``,
    ``'Power Supply'`` and ``'power-supply'`` are valid names.

    Args:
        name: The name of the sensor type, as returned by
            :func:`sensor_type_to_string`, or the number of the sensor
            type, decimal or with 0x prefix.

    Returns:
        The sensor type.

    Raises:
        ValueError: The name is no known sensor type.
    """
    try:
        sensor_type = int(name, 0)
    except ValueError:
        pass
    else:
        if not 0 <= sensor_type <= 0xff:
            raise ValueError(f'sensor type out of range: {name}')
        return sensor_type
    normalized = _normalize_type_name(name)
    for sensor_type, type_name in SENSOR_TYPE_NAMES.items():
        if _normalize_type_name(type_name) == normalized:
            return sensor_type
    raise ValueError(f'unknown sensor type: {name}')


# The threshold comparison states of a threshold sensor, by bit of the
# states of Get Sensor Reading
THRESHOLD_STATE_NAMES = (
    'Lower Non-critical',
    'Lower Critical',
    'Lower Non-recoverable',
    'Upper Non-critical',
    'Upper Critical',
    'Upper Non-recoverable',
)


class SensorReading:
    """The reading of a sensor, see :meth:`Sensor.read_sensor`.

    Attributes:
        record (SdrFullSensorRecord | SdrCompactSensorRecord): The record
            of the sensor.
        raw (int | None): The raw reading, None while the initial update of
            the sensor is in progress.
        value (float | None): The reading converted to the sensor unit.
            None for a sensor without numeric reading, e.g. a discrete
            sensor of a compact record, or if ``raw`` is None.
        unit (str): The unit of ``value``, e.g. ``'degrees C'``. An empty
            string for a sensor without numeric reading or unit.
        states (int | None): The states bit mask, the threshold comparison
            status of a threshold sensor in bits 0-5 (see
            ``THRESHOLD_STATE_NAMES``) or the asserted states of a discrete
            sensor in bits 0-14. The reserved bits are cleared. None if
            the sensor does not report them.
    """

    def __init__(self, record: sdr.SdrFullSensorRecord
                 | sdr.SdrCompactSensorRecord, raw: int | None,
                 value: float | None, unit: str,
                 states: int | None) -> None:
        """Initialize the reading.

        Args:
            record: The record of the sensor.
            raw: The raw reading.
            value: The converted reading.
            unit: The unit of the converted reading.
            states: The states bit mask.
        """
        self.record = record
        self.raw = raw
        self.value = value
        self.unit = unit
        self.states = states

    def __repr__(self) -> str:
        """Return the name, the value, the unit and the states."""
        return (f'SensorReading(name={self.name!r}, value={self.value!r}, '
                f'unit={self.unit!r}, states={self.states!r})')

    @property
    def name(self) -> str:
        """The name of the sensor, the device ID string of its record."""
        return str(self.record.device_id_string)

    def state_names(self) -> list[str]:
        """Return the names of the asserted states.

        The states of a threshold sensor are the crossed thresholds, e.g.
        ``'Upper Critical'``. The states of a discrete sensor are named by
        :func:`event_offset_to_string`, an unknown state as
        ``'Offset 0x..'``.

        Returns:
            The names, an empty list if no state is asserted or the
            sensor does not report states.
        """
        if self.states is None:
            return []
        event_reading_type = self.record.event_reading_type_code
        names = []
        if event_reading_type == EVENT_READING_TYPE_CODE_THRESHOLD:
            for (bit, name) in enumerate(THRESHOLD_STATE_NAMES):
                if self.states & (1 << bit):
                    names.append(name)
            return names
        for offset in range(15):
            if self.states & (1 << offset):
                description = event_offset_to_string(
                    event_reading_type, self.record.sensor_type_code, offset)
                names.append(description or f'Offset 0x{offset:02x}')
        return names


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

    def get_device_sdr_info(self,
                            sdr_count: bool = False) -> DeviceSdrInfo:
        """Get the information about the device SDR repository.

        Args:
            sdr_count: Return the number of SDRs instead of the number of
                sensors in ``count``.

        Returns:
            The number of sensors or SDRs, the LUNs with sensors, and if
            the sensors are populated dynamically.
        """
        if sdr_count:
            rsp = self.send_message_by_name('GetDeviceSdrInfo', operation=1)
        else:
            rsp = self.send_message_by_name('GetDeviceSdrInfo')
        return DeviceSdrInfo(rsp)

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

        rsp = get_sdr_chunk_helper(self.send_message, req)

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
        return self._get_device_sdr(record_id, reservation_id)[0]

    def _get_device_sdr(self, record_id: int, reservation_id: int | None
                        ) -> tuple[sdr.SdrCommon, int]:
        # returns the reservation ID too, a new one if it was canceled
        (next_id, record_data, reservation_id) = \
            get_sdr_data_helper(self.reserve_device_sdr_repository,
                                self._get_device_sdr_chunk,
                                record_id, reservation_id,
                                self._device_sdr_read_length)

        return (sdr.SdrCommon.from_data(record_data, next_id), reservation_id)

    def device_sdr_entries(self) -> Generator[sdr.SdrCommon, None, None]:
        """Return a generator of all records of the device SDR repository.

        The repository is reserved once, and again if the reservation is
        canceled. The records are read starting with record ID 0 until the
        next record ID is 0xffff.

        Yields:
            The decoded records.
        """
        reservation_id = self.reserve_device_sdr_repository()
        record_id = 0

        while True:
            (record, reservation_id) = self._get_device_sdr(record_id,
                                                            reservation_id)
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

    def sdr_entries(self) -> Iterator[sdr.SdrCommon]:
        """Return the records that describe the sensors of the device.

        The records are read from the SDR repository, or from the device
        SDR repository if the device has no SDR repository. A BMC normally
        holds its records in the SDR repository, the device SDR repository
        is mostly used by satellite controllers.

        Returns:
            A generator of the decoded records.

        Raises:
            NotSupportedError: The device has neither an SDR repository
                nor a device SDR repository.
        """
        device_id = self.get_device_id()
        if device_id.supports_function('sdr_repository'):
            return self.sdr_repository_entries()
        if device_id.supports_function('sensor'):
            return self.device_sdr_entries()
        raise NotSupportedError('device supports neither SDR repository '
                                'nor sensor functions')

    def find_sensors(self, name: str | None = None,
                     sensor_type: int | str | None = None,
                     ) -> list[sdr.SdrFullSensorRecord
                               | sdr.SdrCompactSensorRecord]:
        """Search the sensors of the device by name and type.

        The sensors are the full and compact sensor records of
        :meth:`sdr_entries`. Reading the records is slow, so keep the
        records to read the sensors repeatedly with :meth:`read_sensor`.

        Args:
            name: A glob pattern for the sensor name, matched against the
                whole device ID string and ignoring case, e.g. ``'CPU*'``
                or ``'*temp*'``. None matches all names.
            sensor_type: The sensor type, a ``SENSOR_TYPE_*`` constant or
                a name for :func:`sensor_type_from_string`, e.g.
                ``'temperature'`` or ``'voltage'``. None matches all types.

        Returns:
            The records of the matching sensors, in repository order.

        Raises:
            NotSupportedError: The device has neither an SDR repository
                nor a device SDR repository.
            ValueError: The sensor type name is unknown.
        """
        if isinstance(sensor_type, str):
            sensor_type = sensor_type_from_string(sensor_type)
        pattern = None if name is None else name.lower()

        sensors: list[sdr.SdrFullSensorRecord
                      | sdr.SdrCompactSensorRecord] = []
        for record in self.sdr_entries():
            if not isinstance(record, (sdr.SdrFullSensorRecord,
                                       sdr.SdrCompactSensorRecord)):
                continue
            if (sensor_type is not None
                    and record.sensor_type_code != sensor_type):
                continue
            if (pattern is not None and not fnmatchcase(
                    str(record.device_id_string).lower(), pattern)):
                continue
            sensors.append(record)
        return sensors

    def read_sensor(self, record: sdr.SdrFullSensorRecord
                    | sdr.SdrCompactSensorRecord) -> SensorReading:
        """Read a sensor and convert the reading to the sensor unit.

        The reading of a full sensor record with a numeric reading is
        converted with the factors of the record, or with the factors
        of the reading for a non-linear sensor. The reading of a compact
        sensor record is not converted.

        The sensor is read with the LUN of the record on the current
        target. A sensor of another controller (``owner_id`` of the record)
        is only read correctly if the target is set to that controller.

        Args:
            record: The record of the sensor, e.g. of
                :meth:`find_sensors`.

        Returns:
            The raw and the converted reading, the unit and the states.

        Raises:
            CompletionCodeError: The sensor cannot be read, e.g. the
                sensor is not present.
            DecodingError: The linearization of the record is unknown.
        """
        (raw, states) = self.get_sensor_reading(record.number,
                                                record.owner_lun)
        if states is not None:
            # the bits 7:6 of a threshold sensor are reserved, and often set
            if (record.event_reading_type_code
                    == EVENT_READING_TYPE_CODE_THRESHOLD):
                states &= 0x3f
            else:
                states &= 0x7fff
        value = None
        unit = ''
        if (isinstance(record, sdr.SdrFullSensorRecord)
                and record.analog_data_format
                != record.DATA_FMT_NONE):
            unit = sdr.units_to_string(record.units_1, record.units_2,
                                       record.units_3)
            if raw is not None:
                factors = None
                if record.is_non_linear:
                    factors = self.get_sensor_reading_factors(
                        record.number, raw, lun=record.owner_lun)
                value = record.convert_sensor_raw_to_value(raw, factors)
        return SensorReading(record, raw, value, unit, states)

    def get_sensor_reading_factors(self, sensor_number: int, reading: int,
                                   lun: int = 0) -> SensorReadingFactors:
        """Get the conversion factors of a sensor for a raw reading.

        The factors of a non-linear sensor depend on the reading. They are
        valid up to the next reading that is returned.

        Args:
            sensor_number: The sensor number.
            reading: The raw reading.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            The factors M, B, K1 (B exponent) and K2 (result exponent), the
            tolerance and the accuracy, as in a full sensor record.
        """
        rsp = self.send_message_by_name('GetSensorReadingFactors',
                                        sensor_number=sensor_number,
                                        reading=reading, lun=lun)
        return SensorReadingFactors(rsp)

    def set_sensor_hysteresis(self, sensor_number: int, positive: int,
                              negative: int, lun: int = 0) -> None:
        """Set the hysteresis of a threshold sensor.

        Args:
            sensor_number: The sensor number.
            positive: The raw positive-going hysteresis.
            negative: The raw negative-going hysteresis.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Raises:
            CompletionCodeError: The device rejected the request, e.g. if the
                hysteresis is not settable.
        """
        self.send_message_by_name('SetSensorHysteresis',
                                  sensor_number=sensor_number,
                                  positive_going_hysteresis=positive,
                                  negative_going_hysteresis=negative,
                                  lun=lun)

    def get_sensor_hysteresis(self, sensor_number: int,
                              lun: int = 0) -> tuple[int, int]:
        """Get the hysteresis of a threshold sensor.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            A tuple of the raw positive-going and negative-going hysteresis.
        """
        rsp = self.send_message_by_name('GetSensorHysteresis',
                                        sensor_number=sensor_number,
                                        lun=lun)
        return (rsp.positive_going_hysteresis, rsp.negative_going_hysteresis)

    def set_sensor_event_enable(self, sensor_number: int,
                                event_messages: bool = True,
                                sensor_scanning: bool = True,
                                assertion_mask: int | None = None,
                                deassertion_mask: int | None = None,
                                enable: bool = True, lun: int = 0) -> None:
        """Enable or disable the event messages and the scanning of a sensor.

        Args:
            sensor_number: The sensor number.
            event_messages: Enable the event messages of the sensor, False
                disables all of them.
            sensor_scanning: Enable the scanning of the sensor.
            assertion_mask: The assertion events (bits 0 - 14) to enable or
                disable, the individual events are not changed if both
                masks are None.
            deassertion_mask: The deassertion events to enable or disable.
            enable: Enable the events of the masks, False disables them.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Raises:
            CompletionCodeError: The device rejected the request.
        """
        req = create_request_by_name('SetSensorEventEnable')
        req.sensor_number = sensor_number
        req.lun = lun
        req.enable.event_message = int(event_messages)
        req.enable.sensor_scanning = int(sensor_scanning)
        if assertion_mask is not None or deassertion_mask is not None:
            # 1 enables, 2 disables the selected events
            req.enable.config = 1 if enable else 2
            assertion_mask = assertion_mask or 0
            deassertion_mask = deassertion_mask or 0
            req.byte3 = assertion_mask & 0xff
            req.byte4 = (assertion_mask >> 8) & 0x7f
            req.byte5 = deassertion_mask & 0xff
            req.byte6 = (deassertion_mask >> 8) & 0x7f
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def get_sensor_event_enable(self, sensor_number: int,
                                lun: int = 0) -> SensorEventEnable:
        """Get which event messages of a sensor are enabled.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            If the event messages and the scanning are enabled, and the
            enabled assertion and deassertion events.
        """
        rsp = self.send_message_by_name('GetSensorEventEnable',
                                        sensor_number=sensor_number,
                                        lun=lun)
        return SensorEventEnable(rsp)

    def get_sensor_event_status(self, sensor_number: int,
                                lun: int = 0) -> SensorEventStatus:
        """Get the asserted and deasserted events of a sensor.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            If the event messages and the scanning are enabled, if the
            reading is unavailable, and the asserted and deasserted events.
        """
        rsp = self.send_message_by_name('GetSensorEventStatus',
                                        sensor_number=sensor_number,
                                        lun=lun)
        return SensorEventStatus(rsp)

    def set_sensor_type(self, sensor_number: int, sensor_type: int,
                        event_reading_type: int, lun: int = 0) -> None:
        """Set the sensor type and the event/reading type of a sensor.

        Args:
            sensor_number: The sensor number.
            sensor_type: The sensor type, one of the ``SENSOR_TYPE_*``
                constants.
            event_reading_type: The event/reading type, one of the
                ``EVENT_READING_TYPE_*`` constants.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Raises:
            CompletionCodeError: The device rejected the request.
        """
        req = create_request_by_name('SetSensorType')
        req.sensor_number = sensor_number
        req.lun = lun
        req.sensor_type = sensor_type
        req.event_reading_type.code = event_reading_type
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def get_sensor_type(self, sensor_number: int,
                        lun: int = 0) -> tuple[int, int]:
        """Get the sensor type and the event/reading type of a sensor.

        Args:
            sensor_number: The sensor number.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Returns:
            A tuple of the sensor type and the event/reading type, see
            :func:`sensor_type_to_string` and
            :func:`event_reading_type_to_string`.
        """
        rsp = self.send_message_by_name('GetSensorType',
                                        sensor_number=sensor_number,
                                        lun=lun)
        return (rsp.sensor_type, rsp.event_reading_type.code)

    def set_sensor_reading_and_event_status(
            self, sensor_number: int, reading: int | None = None,
            assertion_mask: int | None = None,
            deassertion_mask: int | None = None,
            mask_operation: int = EVENT_BITS_WRITE,
            event_data: ByteSequence | None = None,
            event_data_with_offset: bool = False,
            lun: int = 0) -> None:
        """Set the reading and the event status of a sensor.

        This is used by a controller whose sensors are read by software
        and set in the BMC. Only the given values are changed.

        Args:
            sensor_number: The sensor number.
            reading: The raw reading.
            assertion_mask: The assertion event status bits (bits 0 - 14).
            deassertion_mask: The deassertion event status bits.
            mask_operation: How the bits of the masks are applied, one of
                ``EVENT_BITS_SET``, ``EVENT_BITS_CLEAR`` and
                ``EVENT_BITS_WRITE``.
            event_data: The 3 event data bytes of the event message, the BMC
                generates them if not given.
            event_data_with_offset: Use the event offset of the event data
                byte 1 instead of the offset the BMC determines.
            lun: The LUN of the sensor owner, ``owner_lun`` of its record.

        Raises:
            ValueError: The event data is not 3 bytes long or the mask
                operation is unknown.
            CompletionCodeError: The device rejected the request.
        """
        if mask_operation not in (EVENT_BITS_SET, EVENT_BITS_CLEAR,
                                  EVENT_BITS_WRITE):
            raise ValueError(f'unknown mask operation {mask_operation}')
        if event_data is not None and len(event_data) != 3:
            raise ValueError(f'event data has {len(event_data)} bytes, not 3')

        req = create_request_by_name('SetSensorReadingAndEventStatus')
        req.sensor_number = sensor_number
        req.lun = lun
        # each optional byte needs the bytes before it, they are sent with
        # the operation "don't change"
        if reading is not None:
            req.operation.reading = 1
            req.sensor_reading = reading
        if assertion_mask is not None:
            req.operation.assertion_bits = mask_operation
            req.assertion_mask = assertion_mask & 0x7fff
        if deassertion_mask is not None:
            req.operation.deassertion_bits = mask_operation
            req.deassertion_mask = deassertion_mask & 0x7fff
        if event_data is not None:
            req.operation.event_data = 2 if event_data_with_offset else 1
            req.event_data = array('B', event_data)

        fields = ('sensor_reading', 'assertion_mask', 'deassertion_mask',
                  'event_data')
        given = [i for i, name in enumerate(fields)
                 if getattr(req, name) is not None]
        for name in fields[:max(given, default=0)]:
            if getattr(req, name) is None:
                setattr(req, name, 0)

        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

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
        check_rsp_completion_code(rsp)

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
                            event_data: list[int] | None = None,
                            generator_id: int = GENERATOR_ID_SMS) -> None:
        """Send a platform event message to the event receiver.

        The Generator ID is only sent over the system interface, where the
        request has to contain it. Otherwise the event receiver takes it from
        the requester address.

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
            generator_id: The Generator ID sent over the system interface,
                by default ``GENERATOR_ID_SMS`` (0x41) like ipmitool.

        Raises:
            CompletionCodeError: The device rejected the event.
        """
        req = create_request_by_name('PlatformEvent')
        if self.interface.is_system_interface(self.target):
            req.generator_id = generator_id
        req.sensor_type = sensor_type
        req.sensor_number = sensor_number
        req.event_type.type = event_type
        req.event_type.dir = 0 if asserted else 1
        req.event_data = [0] if event_data is None else event_data
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)


class DeviceSdrInfo(State):
    """The information about the device SDR repository.

    Attributes:
        count (int): The number of sensors on the LUN of the request, or
            the number of SDRs, see :meth:`Sensor.get_device_sdr_info`.
        luns_with_sensors (list[int]): The LUNs that have sensors.
        dynamic_population (bool): The sensors are populated dynamically.
        sensor_population_change (int | None): The time of the last change
            of the sensor population, None if the sensors are static or the
            device does not report it.
    """

    def _from_response(self, rsp: Message) -> None:
        self.count = rsp.number_of_sensors
        self.luns_with_sensors = [
            lun for lun in range(4)
            if getattr(rsp.flags, f'lun{lun}_has_sensors')]
        self.dynamic_population = bool(rsp.flags.dynamic_population)
        self.sensor_population_change = rsp.sensor_population_change


class SensorReadingFactors(State):
    """The conversion factors of a sensor for a reading.

    The reading is converted with ``y = (M * x + B * 10^K1) * 10^K2``, see
    :meth:`pyipmi.sdr.SdrFullSensorRecord.convert_sensor_raw_to_value`.

    Attributes:
        next_reading (int): The next raw reading at which the factors
            change.
        m (int): The conversion factor M.
        tolerance (int): The tolerance in +/- half raw counts.
        b (int): The conversion offset B.
        accuracy (int): The accuracy in 0.01 percent units.
        accuracy_exp (int): The accuracy exponent.
        k1 (int): The exponent of B.
        k2 (int): The result exponent.
    """

    def _from_response(self, rsp: Message) -> None:
        self.next_reading = rsp.next_reading
        (m, m_tol, b, b_acc, acc_accexp, rexp_bexp) = rsp.factors
        complement = sdr.SdrFullSensorRecord._convert_complement
        self.m = complement((m & 0xff) | ((m_tol & 0xc0) << 2), 10)
        self.tolerance = m_tol & 0x3f
        self.b = complement((b & 0xff) | ((b_acc & 0xc0) << 2), 10)
        self.accuracy = (b_acc & 0x3f) | ((acc_accexp & 0xf0) << 2)
        self.accuracy_exp = (acc_accexp & 0x0c) >> 2
        self.k2 = complement((rexp_bexp & 0xf0) >> 4, 4)
        self.k1 = complement(rexp_bexp & 0x0f, 4)


def _event_mask(low: int | None, high: int | None) -> int | None:
    """Combine the event bytes 0 - 7 and 8 - 14 to a mask."""
    if low is None:
        return None
    return low | ((high or 0) & 0x7f) << 8


class SensorEventEnable(State):
    """The enabled event messages of a sensor.

    Attributes:
        event_messages (bool): The event messages are enabled.
        sensor_scanning (bool): The scanning of the sensor is enabled.
        assertion_mask (int | None): The enabled assertion events, bits
            0 - 14, None if the sensor does not report them.
        deassertion_mask (int | None): The enabled deassertion events.
    """

    def _from_response(self, rsp: Message) -> None:
        self.event_messages = bool(rsp.enabled.event_message)
        self.sensor_scanning = bool(rsp.enabled.sensor_scanning)
        self.assertion_mask = _event_mask(rsp.byte3, rsp.byte4)
        self.deassertion_mask = _event_mask(rsp.byte5, rsp.byte6)


class SensorEventStatus(State):
    """The event status of a sensor.

    Attributes:
        event_messages_enabled (bool): The event messages are enabled.
        sensor_scanning_enabled (bool): The scanning of the sensor is
            enabled.
        reading_unavailable (bool): The reading or state is unavailable.
        asserted (int | None): The asserted events, bits 0 - 14, None if
            the sensor does not report them.
        deasserted (int | None): The deasserted events.
    """

    def _from_response(self, rsp: Message) -> None:
        self.event_messages_enabled = bool(rsp.status.event_messages_enabled)
        self.sensor_scanning_enabled = \
            bool(rsp.status.sensor_scanning_enabled)
        self.reading_unavailable = bool(rsp.status.reading_unavailable)
        self.asserted = _event_mask(rsp.assertion_events_low,
                                    rsp.assertion_events_high)
        self.deasserted = _event_mask(rsp.deassertion_events_low,
                                      rsp.deassertion_events_high)
