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
import json
import logging
import pprint
import sys
import traceback
from array import array
from typing import Callable

import pyipmi
import pyipmi.interfaces
from pyipmi.utils import py3_array_tobytes


def auto_int(value: str) -> int:
    """Argument type for numbers, decimal or with 0x prefix."""
    return int(value, 0)


def cmd_bmc_info(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    device_id = ipmi.get_device_id()
    print('''
Device ID:          %(device_id)s
Device Revision:    %(revision)s
Firmware Revision:  %(fw_revision)s
IPMI Version:       %(ipmi_version)s
Manufacturer ID:    %(manufacturer_id)d (0x%(manufacturer_id)04x)
Product ID:         %(product_id)d (0x%(product_id)04x)
Device Available:   %(available)d
Provides SDRs:      %(provides_sdrs)d
Additional Device Support:
'''[1:-1] % device_id.__dict__)

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
            print('  %s' % s)

    if device_id.aux is not None:
        print('Aux Firmware Rev Info:  [{:s}]'.format(
              ' '.join('%02x' % d for d in device_id.aux)))


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


def sdr_show(ipmi: pyipmi.Ipmi, s: pyipmi.sdr.SdrCommon) -> None:

    print("SDR record ID:    0x%04x" % s.id)
    print("SDR type:         0x%02x" % s.type)
    # not all record types have an ID string and entity
    if hasattr(s, 'device_id_string'):
        print("Device Id string: %s" % s.device_id_string)
    if hasattr(s, 'entity_id'):
        print("Entity:           %s.%s" % (s.entity_id, s.entity_instance))
    if s.type is pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD:
        (raw, states) = ipmi.get_sensor_reading(s.number, s.owner_lun)
        value = s.convert_sensor_raw_to_value(raw)
        if value is None:
            value = "na"
        t_unr = s.convert_sensor_raw_to_value(s.threshold['unr'])
        t_ucr = s.convert_sensor_raw_to_value(s.threshold['ucr'])
        t_unc = s.convert_sensor_raw_to_value(s.threshold['unc'])
        t_lnc = s.convert_sensor_raw_to_value(s.threshold['lnc'])
        t_lcr = s.convert_sensor_raw_to_value(s.threshold['lcr'])
        t_lnr = s.convert_sensor_raw_to_value(s.threshold['lnr'])
        print("Reading value:    %s" % value)
        print("Reading state:    0x%x" % states)
        print("UNR:              %s" % t_unr)
        print("UCR:              %s" % t_ucr)
        print("UNC:              %s" % t_unc)
        print("LNC:              %s" % t_lnc)
        print("LCR:              %s" % t_lcr)
        print("LNR:              %s" % t_lnr)
    elif s.type is pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD:
        (raw, states) = ipmi.get_sensor_reading(s.number)
        print("Reading:          %s" % raw)
        print("Reading state:    0x%x" % states)
    elif s.type is \
            pyipmi.sdr.SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD:
        print("Slave address:    0x%02x" % (s.device_slave_address << 1))
        print("Device ID:        0x%02x" % s.device_id)
        print("Device revision:  %d" % s.device_revision)
        print("Channel:          %d" % s.channel_number)
        print("Firmware:         %d.%02x" % (s.firmware_revision_1,
                                             s.firmware_revision_2))
        print("IPMI version:     %d.%d" % (s.ipmi_version & 0xf,
                                           s.ipmi_version >> 4))
        print("Manufacturer ID:  0x%05x" % s.manufacturer_id)
        print("Product ID:       0x%04x" % s.product_id)


def cmd_sdr_show_raw(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    try:
        sdr = ipmi.get_device_sdr(args.sdr_id)
        print(' '.join(['0x%02x' % b for b in sdr.data]))
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
    if number:
        number = str(number)
    else:
        number = 'na'

    if states:
        states = hex(states)
    else:
        states = 'na'

    print("0x%04x | %3s | %-18s | %9s | %s" % (record_id, number,
                                               id_string, value, states))


def cmd_sdr_list(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    iter_fct = None

    device_id = ipmi.get_device_id()
    if device_id.supports_function('sdr_repository'):
        iter_fct = ipmi.sdr_repository_entries
    elif device_id.supports_function('sensor'):
        iter_fct = ipmi.device_sdr_entries

    print("SDR-ID |     | Device String      |")
    print("=======|=====|====================|====================")

    for s in iter_fct():
        try:
            number = None
            value = None
            states = None

            if s.type is pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD:
                (value, states) = ipmi.get_sensor_reading(s.number)
                number = s.number
                if value is not None:
                    value = s.convert_sensor_raw_to_value(value)

            elif s.type is pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD:
                (value, states) = ipmi.get_sensor_reading(s.number)
                number = s.number

            id_string = getattr(s, 'device_id_string', None)

            print_sdr_list_entry(s.id, number, id_string, value, states)

        except pyipmi.errors.CompletionCodeError as e:
            if s.type in (pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD,
                          pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD):
                print('0x{:04x} | {:3d} | {:18s} | ERR: CC=0x{:02x}'.format(
                      s.id,
                      s.number,
                      s.device_id_string,
                      e.cc))


def cmd_fru_print(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    inv = ipmi.get_fru_inventory(args.fru_id)

    # Chassis Info Area
    area = inv.chassis_info_area
    if area:
        print('''
Chassis Info Area:
  Type:               %(type)d
  Part Number:        %(part_number)s
  Serial Number:      %(serial_number)s
'''[1:-1] % area.__dict__)

        if len(area.custom_chassis_info) != 0:
            print('  Custom Chassis Info Records:')
            for field in area.custom_chassis_info:
                print('    %s' % field)

    # Board Info Area
    area = inv.board_info_area
    if area:
        print('''
Board Info Area:
  Mfg. Date / Time:   %(mfg_date)s
  Manufacturer:       %(manufacturer)s
  Product Name:       %(product_name)s
  Serial Number:      %(serial_number)s
  Part Number:        %(part_number)s
  FRU File ID:        %(fru_file_id)s
'''[1:-1] % area.__dict__)

        if len(area.custom_mfg_info) != 0:
            print('  Custom Board Info Records:')
            for field in area.custom_mfg_info:
                print('    %s' % field)

    # Product Info Area
    area = inv.product_info_area
    if area:
        print('''
Product Info Area:
  Manufacturer:       %(manufacturer)s
  Name:               %(name)s
  Part/Model Number:  %(part_number)s
  Version:            %(version)s
  Serial Number:      %(serial_number)s
  Asset:              %(asset_tag)s
  FRU File ID:        %(fru_file_id)s
'''[1:-1] % area.__dict__)

        if len(area.custom_mfg_info) != 0:
            print('  Custom Board Info Records:')
            for field in area.custom_mfg_info:
                print('    %s' % field)

    # Multirecords
    area = inv.multirecord_area
    if area:
        print('Multirecord Area:')
        if args.all == 'all':
            for record in area.records:
                print('  %s' % record)
        else:
            print('  Skipped. Use "print <fruid> all"')


def cmd_raw(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    raw_bytes = array('B', args.data)
    rsp = ipmi.raw_command(args.lun, args.netfn, py3_array_tobytes(raw_bytes))
    print(' '.join('%02x' % d for d in array('B', rsp)))


def cmd_hpm_capabilities(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    cap = ipmi.get_target_upgrade_capabilities()

    for c in cap.components:
        properties = ipmi.get_component_properties(c)
        print("Component ID: %d" % c)
        for prop in properties:
            print("  %s" % prop)


def cmd_hpm_check_file(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    cap = ipmi.open_upgrade_image(args.file)

    print(cap.header)
    for action in cap.actions:
        print(action)


def cmd_hpm_install(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.install_component_from_file(args.file, args.component_id)


def cmd_chassis_status(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    status = ipmi.get_chassis_status()

    if args.json:
        status = {
                  'power_on': status.power_on,
                  'overload': status.overload,
                  'interlock': status.interlock,
                  'fault': status.fault,
                  'ctrl_fault': status.control_fault,
                  'restore_policy': status.restore_policy
                 }
        print(json.dumps(status))
    else:

        print('''
Power ON:          %(power_on)s
Overload:          %(overload)s
Interlock:         %(interlock)s
Fault:             %(fault)s
Ctrl Fault:        %(control_fault)s
Restore Policy:    %(restore_policy)s
'''[1:-1] % status.__dict__)

        for event in status.last_event:
            print(event)
        for state in status.chassis_state:
            print(state)


CHASSIS_POWER_CONTROLS = {
    'off': 'chassis_control_power_down',
    'on': 'chassis_control_power_up',
    'cycle': 'chassis_control_power_cycle',
    'reset': 'chassis_control_hard_reset',
    'diag': 'chassis_control_power_diagnostic_interrupt',
    'soft': 'chassis_control_power_soft_shutdown',
}


def cmd_chassis_power(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    getattr(ipmi, CHASSIS_POWER_CONTROLS[args.action])()


def cmd_picmg_get_power(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    pwr = ipmi.get_power_level(0, 0)
    print(pwr)


def print_link_state(p: pyipmi.picmg.LinkDescriptor, s: int) -> None:
    intf_str = pyipmi.picmg.LinkDescriptor().get_interface_string(p.interface)
    link_str = pyipmi.picmg.LinkDescriptor().get_link_type_string(
            p.type, p.extension, p.sig_class)
    print('CH=%02d INTF=%d FLAGS=0x%x TYPE=%d SIG=%d EXT=%d STATE=%d (%s/%s)'
          % (p.channel, p.interface, p.link_flags, p.type, p.sig_class,
             p.extension, s, intf_str, link_str))


def cmd_picmg_get_portstate_all(ipmi: pyipmi.Ipmi,
                                args: argparse.Namespace) -> None:
    for interface in range(3):
        for channel in range(16):
            try:
                (p, s) = ipmi.get_port_state(channel, interface)
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
    ipmi.send_channel_power(args.channel)


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
    print('VSO Identifier    : 0x%02x' % rsp.vita_identifier)
    print('IPMC Identifier   : 0x%02x' % int(ipmc))
    print('    Tier  %d' % (ipmc.tier_functionality + 1))
    print('    Layer %d' % (ipmc.layer_functionality + 1))
    print('IPMB Capabilities : 0x%02x' % int(ipmb))
    frequency = {0: '100', 1: '400'}.get(ipmb.max_frequency, 'RESERVED')
    print('    Frequency  %skHz' % frequency)
    print('    %d IPMB interface%s supported'
          % (ipmb.number_ipmbs + 1, 's' if ipmb.number_ipmbs else ''))
    print('VSO Standard      : %s'
          % ('VITA 46.11' if rsp.vso_standard.standard == 0 else 'RESERVED'))
    print('VSO Spec Revision : %d.%d' % (rev & 0xf, rev >> 4))
    print('Max FRU Device ID : 0x%02x' % rsp.max_fru_id)
    print('FRU Device ID     : 0x%02x' % rsp.ipmc_fru_device_id)


def cmd_vita_frucontrol(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    name = (VITA_FRU_CONTROL_OPTIONS[args.option]
            if args.option < len(VITA_FRU_CONTROL_OPTIONS) else 'Unknown')
    print('FRU Device Id: %d FRU Control Option: %s' % (args.fru_id, name))
    ipmi.vita_fru_control(args.fru_id, args.option)
    print('FRU Control: ok')


def cmd_vita_addrinfo(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_fru_address_info(args.fru_id)
    print('Hardware Address : 0x%02x' % rsp.hardware_address)
    print('IPMB-0 Address   : 0x%02x' % rsp.ipmb_0_address)
    print('FRU ID           : 0x%02x' % rsp.fru_id)
    print('Site ID          : 0x%02x' % rsp.site_id)
    print('Site Type        : %s'
          % pyipmi.vita.VITA_SITE_TYPES.get(rsp.site_type, 'Unknown'))
    if rsp.address_on_channel_7 is not None:
        print('Channel 7 Address: 0x%02x' % rsp.address_on_channel_7)


def cmd_vita_activate(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_activation(args.fru_id)
    print('FRU has been successfully activated')


def cmd_vita_deactivate(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_deactivation(args.fru_id)
    print('FRU has been successfully deactivated')


def cmd_vita_policy_get(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    policy = ipmi.get_vita_fru_state_policy(args.fru_id).activation_policies
    print('FRU State Policy Bits:\t%xh' % int(policy))
    print('    Default-Activation-Locked Policy Bit is %d'
          % policy.default_activation_locked)
    print('    Commanded-Deactivation-Ignored Policy Bit is %d'
          % policy.commanded_deactivation_ignored)
    print('    Deactivation-Locked Policy Bit is %d'
          % policy.deactivation_lock)
    print('    Activation-Locked Policy Bit is %d' % policy.activation_lock)


def cmd_vita_policy_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_fru_state_policy(args.fru_id, args.mask, args.value)
    print('FRU state policy bits have been updated')


def cmd_vita_led_prop(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_led_properties(args.fru_id)
    print('LED Count:\t   %#x' % rsp.led_count)


def cmd_vita_led_cap(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    rsp = ipmi.get_vita_led_color_capabilities(args.fru_id, args.led_id)
    capabilities = int(rsp.color_capabilities)
    colors = [VITA_LED_COLORS[i] for i in range(8) if capabilities & (1 << i)]
    print('LED Color Capabilities: %s' % ', '.join(colors))
    print('Default LED Color in')
    print('      LOCAL control:  %s'
          % _vita_led_color(rsp.default_color_local_control.value))
    print('      OVERRIDE state: %s'
          % _vita_led_color(rsp.default_color_override_control.value))
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
    print('LED states:                   %x\t%s'
          % (int(state), ' '.join('[%s]' % flag for flag in flags)))

    if state.ipmc_control:
        print('  Local Control function:     %x\t[%s]'
              % (rsp.local_control_function,
                 _vita_led_function(rsp.local_control_function)))
        print('  Local Control On-Duration:  %x'
              % rsp.local_control_on_duration)
        print('  Local Control Color:        %x\t[%s]'
              % (rsp.local_control_color,
                 _vita_led_color(rsp.local_control_color & 7)))

    if (state.override or state.lamp_test) and rsp.override_state is not None:
        print('  Override function:     %x\t[%s]'
              % (rsp.override_state, _vita_led_function(rsp.override_state)))
        print('  Override On-Duration:  %x' % rsp.override_on_duration)
        print('  Override Color:        %x\t[%s]'
              % (rsp.override_color, _vita_led_color(rsp.override_color & 7)))
        if state.lamp_test and rsp.lamp_test_duration is not None:
            print('  Lamp test duration:    %x' % rsp.lamp_test_duration)


def cmd_vita_led_set(ipmi: pyipmi.Ipmi, args: argparse.Namespace) -> None:
    ipmi.set_vita_led_state(args.fru_id, args.led_id, args.function,
                            args.duration, args.color)
    print('LED state has been updated')


def parse_interface_options(interface_name: str, options: str | list) -> dict:
    if options:
        options = options.split(',')

    interface_options = {}

    for option in options:
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
                print('Warning: unknown option %s' % name)
        elif interface_name == 'ipmitool':
            if name == 'interface_type':
                interface_options['interface_type'] = value
            elif name == 'cipher':
                interface_options['cipher'] = value
            else:
                print('Warning: unknown option %s' % name)
        elif interface_name == 'ipmbdev':
            if name == 'port':
                interface_options['port'] = value
        elif interface_name == 'ipmidev':
            if name == 'port':
                interface_options['port'] = value
            elif name == 'timeout':
                interface_options['timeout'] = float(value)
            else:
                print('Warning: unknown option %s' % name)
        elif interface_name == 'openipmblink':
            if name == 'port':
                interface_options['port'] = value
            elif name == 'bus':
                interface_options['bus'] = int(value)
            elif name == 'address':
                interface_options['slave_address'] = int(value, 0)
            else:
                print('Warning: unknown option %s' % name)

    return interface_options


def create_ipmi_connection(interface_name: str, interface_options: str | list,
                           target_address: int,
                           target_routing: str | list | None,
                           rmcp_host: str | None, rmcp_port: int,
                           rmcp_user: str, rmcp_password: str,
                           rmcp_priv_level: str | None) -> pyipmi.Ipmi:
    interface_options = parse_interface_options(interface_name,
                                                interface_options)

    try:
        interface = pyipmi.interfaces.create_interface(interface_name,
                                                       **interface_options)
    except RuntimeError as e:
        print(e)
        return None

    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(target_address)

    if target_routing is not None:
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
'''


class _CommandGroups(object):
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='ipmitool.py',
        description='Pure python IPMI tool',
        epilog=INTERFACE_OPTIONS_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.set_defaults(func=None, help_parser=parser)

    parser.add_argument('-V', '--version', action='version',
                        version='ipmitool v%s' % pyipmi.__version__)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='be verbose')
    parser.add_argument('-J', '--json', action='store_true',
                        help='print the output as JSON (if supported)')
    parser.add_argument('-I', dest='interface', metavar='<interface>',
                        help='interface (rmcp, aardvark, ipmitool, ipmbdev, '
                             'ipmidev, openipmblink)')
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
                        help='RMCP privilege level')

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

    group = commands.group('fru', 'Print built-in FRU')
    p = group.command('print', cmd_fru_print, 'Print FRU inventory')
    p.add_argument('fru_id', type=auto_int, nargs='?', default=0)
    p.add_argument('all', nargs='?', choices=('all',),
                   help='also print the multirecord area')

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
    sub = group.group('send', 'Send')
    sub.command('heartbeat', cmd_picmg_send_pm_heartbeat,
                'Send PM heartbeat')

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
                   help='policy bits to change (%s)' % policy_bits)
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


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.func is None:
        args.help_parser.print_help()
        sys.exit(1)

    handler = logging.StreamHandler()
    if args.verbose:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
    pyipmi.logger.add_log_handler(handler)
    pyipmi.logger.set_log_level(logging.DEBUG)

    routing = args.routing
    if args.channel is not None:
        routing = [(0x20, args.channel, 0)]

    ipmi = None
    if args.needs_connection:
        ipmi = create_ipmi_connection(args.interface, args.options,
                                      args.target, routing,
                                      args.host, args.port, args.user,
                                      args.password, args.priv_level)
        if ipmi is None:
            sys.exit(1)  # interface could not be created, error is printed

    try:
        if args.needs_connection:
            ipmi.open()  # this will open interface and session
        args.func(ipmi, args)
    except pyipmi.errors.CompletionCodeError as e:
        print('Command returned with completion code 0x%02x' % e.cc)
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except pyipmi.errors.IpmiTimeoutError:
        print('Command timed out')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    finally:
        if args.needs_connection:
            ipmi.close()  # this will close interface and session


if __name__ == '__main__':
    main()
