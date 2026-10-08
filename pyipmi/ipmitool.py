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
import traceback
from array import array
from collections.abc import Callable
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


def cmd_sel_list(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for entry in ipmi.sel_entries():
        print(entry)


def cmd_sel_clear(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.clear_sel()


def cmd_sensor_rearm(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.rearm_sensor_events(args.number)


def format_analog_value(value: float | None) -> str:
    """Format a converted analog sensor value with 3 decimal places."""
    if value is None:
        return 'na'
    return f'{value:.3f}'


def format_states(states: int | None) -> str:
    if states is None:
        return 'na'
    return f'0x{states:x}'


def sdr_show(ipmi: pyipmi.Ipmi, s: pyipmi.sdr.SdrCommon) -> None:

    print(f"SDR record ID:    0x{s.id:04x}")
    print(f"SDR type:         0x{s.type:02x}")
    # not all record types have an ID string and entity
    if hasattr(s, 'device_id_string'):
        print(f"Device Id string: {s.device_id_string}")
    if hasattr(s, 'entity_id'):
        print(f"Entity:           {s.entity_id}.{s.entity_instance}")
    if isinstance(s, pyipmi.sdr.SdrFullSensorRecord):
        (raw, states) = ipmi.get_sensor_reading(s.number, s.owner_lun)
        value = format_analog_value(s.convert_sensor_raw_to_value(raw))
        t_unr = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['unr']))
        t_ucr = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['ucr']))
        t_unc = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['unc']))
        t_lnc = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['lnc']))
        t_lcr = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['lcr']))
        t_lnr = format_analog_value(
            s.convert_sensor_raw_to_value(s.threshold['lnr']))
        print(f"Reading value:    {value}")
        print(f"Reading state:    {format_states(states)}")
        print(f"UNR:              {t_unr}")
        print(f"UCR:              {t_ucr}")
        print(f"UNC:              {t_unc}")
        print(f"LNC:              {t_lnc}")
        print(f"LCR:              {t_lcr}")
        print(f"LNR:              {t_lnr}")
    elif isinstance(s, pyipmi.sdr.SdrCompactSensorRecord):
        (raw, states) = ipmi.get_sensor_reading(s.number, s.owner_lun)
        print(f"Reading:          {raw}")
        print(f"Reading state:    {format_states(states)}")
    elif isinstance(s,
                    pyipmi.sdr.SdrManagementControllerConfirmationRecord):
        print(f"Slave address:    0x{s.device_slave_address << 1:02x}")
        print(f"Device ID:        0x{s.device_id:02x}")
        print(f"Device revision:  {s.device_revision:d}")
        print(f"Channel:          {s.channel_number:d}")
        print("Firmware:         "
              f"{s.firmware_revision_1:d}.{s.firmware_revision_2:02x}")
        print("IPMI version:     "
              f"{s.ipmi_version & 0xf:d}.{s.ipmi_version >> 4:d}")
        print(f"Manufacturer ID:  0x{s.manufacturer_id:05x}")
        print(f"Manufacturer Name: {s.manufacturer_name or 'Unknown'}")
        print(f"Product ID:       0x{s.product_id:04x}")


def cmd_sdr_show_raw(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        sdr = ipmi.get_device_sdr(args.sdr_id)
        print(' '.join([f'0x{b:02x}' for b in sdr.data]))
    except ValueError:
        print('')


def cmd_sdr_show(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        s = ipmi.get_device_sdr(args.sdr_id)
        sdr_show(ipmi, s)
    except ValueError:
        print('')


def cmd_sdr_show_all(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    for s in ipmi.device_sdr_entries():
        try:
            sdr_show(ipmi, s)
        except ValueError:
            print('')
        print("\n")


def print_sdr_list_entry(record_id: int, number: int | str | None,
                         id_string: str | None, value: object,
                         states: int | None) -> None:
    # sensor number 0 and the states 0 are valid
    number_str = 'na' if number is None else str(number)
    states_str = 'na' if states is None else hex(states)

    print(f"0x{record_id:04x} | {number_str!s:>3} | {id_string!s:<18} | "
          f"{value!s:>9} | {states_str}")


def cmd_sdr_list(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    iter_fct = None

    device_id = ipmi.get_device_id()
    if device_id.supports_function('sdr_repository'):
        iter_fct = ipmi.sdr_repository_entries
    elif device_id.supports_function('sensor'):
        iter_fct = ipmi.device_sdr_entries
    else:
        print("Device supports neither SDR repository nor sensor "
              "functions", file=sys.stderr)
        return

    print("SDR-ID |     | Device String      |")
    print("=======|=====|====================|====================")

    for s in iter_fct():
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

    group = commands.group('chassis', 'Get chassis status and set power '
                           'state')
    group.command('status', cmd_chassis_status, 'Get chassis status')
    p = group.command('power', cmd_chassis_power, 'Set power state')
    p.add_argument('action', choices=tuple(CHASSIS_POWER_CONTROLS))

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

    group = commands.group('sdr', 'Print Sensor Data Repository entries '
                           'and readings')
    group.command('list', cmd_sdr_list, 'List all SDRs')
    p = group.command('raw', cmd_sdr_show_raw, 'Show SDR raw data')
    p.add_argument('sdr_id', type=auto_int)
    p = group.command('show', cmd_sdr_show, 'Show detail for one SDR')
    p.add_argument('sdr_id', type=auto_int)
    group.command('showall', cmd_sdr_show_all, 'Show detail for all SDRs')

    group = commands.group('sel', 'Print System Event Log (SEL)')
    group.command('list', cmd_sel_list, 'List all SEL entries')
    group.command('clear', cmd_sel_clear, 'Clear SEL')

    group = commands.group('sensor', 'Sensor commands')
    p = group.command('rearm', cmd_sensor_rearm, 'Rearm sensor events')
    p.add_argument('number', type=auto_int, help='sensor number')

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
