#!/usr/bin/env python

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

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
#from builtins import hex
#from builtins import str
#from builtins import map
#from builtins import range

from collections import namedtuple
import sys
import getopt
import logging
import traceback
import array

import pyipmi
import pyipmi.interfaces

Command = namedtuple('Command', 'name fn')
CommandHelp = namedtuple('CommandHelp', 'name arguments help')

# print helper
def _print(s):
    print(s)

def _get_command_function(name):
    for cmd in COMMANDS:
        if cmd.name == name:
            return cmd.fn
    else:
        return None

def cmd_bmc_info(ipmi, args):
    id = ipmi.get_device_id()
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
'''[1:-1] % id.__dict__)

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
        if id.supports_function(n):
            print('  %s' % s)

    if id.aux is not None:
        print('Aux Firmware Rev Info:  [%02x %02x %02x %02x]' % (
                id.aux[0], id.aux[1], id.aux[2], id.aux[3]))

def cmd_sel_clear(ipmi, args):
    ipmi.clear_sel()

def cmd_sensor_rearm(ipmi, args):
    if len(args) < 1:
        return
    number = int(args[0], 0)
    rsp = ipmi.rearm_sensor_events(number)

def sdr_show(ipmi, s):
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
        print("SDR record ID:    0x%04x" % s.id)
        print("Device Id string: %s" % s.device_id_string)
        print("Entity:           %s.%s" % (s.entity_id, s.entity_instance))
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
        print("SDR record ID:    0x%04x" % s.id)
        print("Device Id string: %s" % s.device_id_string)
        print("Entity:           %s.%s" % (s.entity_id, s.entity_instance))
        print("Reading:          %s" % raw)
        print("Reading state:    0x%x" % states)
    else:
        print("SDR record ID:    0x%04x" % s.id)
        print("Device Id string: %s" % s.device_id_string)
        print("Entity:           %s.%s" % (s.entity_id, s.entity_instance))

def cmd_sdr_show(ipmi, args):
    if len(args) != 1:
        usage()
        return

    try:
        s = ipmi.get_device_sdr(int(args[0], 0))
        sdr_show(ipmi, s)
    except ValueError:
        print('')

def cmd_sdr_show_all(ipmi, args):
    for s in ipmi.device_sdr_entries():
        try:
            sdr_show(ipmi, s)
        except ValueError:
            print('')
        print("\n")

def print_sdr_list_entry(record_id, number, id_string, value, states):
    if number:
        number = str(number)
    else:
        number = 'na'

    if states:
        states = hex(states)
    else:
        states = 'na'

    print("0x%04x | %3s | %-16s | %9s | %s" % (record_id, number,
                        id_string, value, states))

def cmd_sdr_list(ipmi, args):
    print("SDR-ID |     | Device String    |")
    print("=======|=====|==================|====================")

    for s in ipmi.device_sdr_entries():
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

            print_sdr_list_entry(s.id, number, s.device_id_string,
                        value, states)

        except pyipmi.errors.CompletionCodeError as e:
            if s.type in (pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD,
                    pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD):
                print("0x%04x | %3d | %-16s | ERR: CC=0x%02x " % (s.id,
                        s.number, s.device_id_string, e.cc))

def cmd_fru_print(ipmi, args):
    fru_id = 0
    print_all = False
    if len(args) > 0:
        fru_id = int(args[0])
    if len(args) > 1 and args[1] == 'all':
        print_all = True

    inv = ipmi.get_fru_inventory(fru_id)

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
        if print_all:
            for record in area.records:
                print('  %s' % record)
        else:
            print('  Skipped. Use "print <fruid> all"')

def cmd_raw(ipmi, args):
    lun = 0
    if len(args) > 1 and args[0] == 'lun':
        lun = int(args[1], 0)
        args = args[2:]

    if len(args) < 2:
        usage()
        return

    netfn = int(args[0], 0)
    raw_bytes = array.array('B', [int(d, 0) for d in args[1:]])
    rsp = ipmi.raw_command(lun, netfn, raw_bytes.tostring())
    print(' '.join('%02x' % ord(d) for d in rsp))

def cmd_hpm_capabilities(ipmi, args):
    cap = ipmi.get_target_upgrade_capabilities()

    for c in cap.components:
        prop = ipmi.get_component_properties(c)
        print("Component ID: %d" % c)
        for p in  prop:
            print("  %s" % p)

def cmd_hpm_check_file(ipmi, args):
    if len(args) < 1:
        return
    cap = ipmi.open_upgrade_image(args[0])

    print(cap.header)
    for action in cap.actions:
        print(action)

def cmd_hpm_install(ipmi, args):
    if len(args) < 2:
        return
    ipmi.install_component_from_file(args[0], int(args[1]))

def cmd_chassis_status(ipmi, args):
    status = ipmi.get_chassis_status()
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

def cmd_picmg_get_power(ipmi, args):
    pwr = ipmi.get_power_level(0, 0)
    print(pwr)

def print_link_state(p, s):
    intf_str = pyipmi.picmg.LinkDescriptor().get_interface_string(p.interface)
    link_str = pyipmi.picmg.LinkDescriptor().get_link_type_string(
            p.type, p.extension, p.sig_class)
    print('CH=%02d INTF=%d FLAGS=0x%x TYPE=%d SIG=%d EXT=%d STATE=%d (%s/%s)'\
            % (p.channel, p.interface, p.link_flags, p.type, p.sig_class,
            p.extension, s, intf_str, link_str))

def cmd_picmg_get_portstate_all(ipmi, args):
    for interface in range(3):
        for channel in range(16):
           try:
               (p, s) = ipmi.get_port_state(channel, interface)
               print_link_state(p, s)
           except pyipmi.errors.CompletionCodeError as e:
               if e.cc is 0xcc:
                   continue

def cmd_picmg_get_portstate(ipmi, args):
    if len(args) < 2:
        return
    channel = int(args[0])
    interface = int(args[1])
    (p, s) = ipmi.get_port_state(channel, interface)
    print_link_state(p, s)

def cmd_picmg_frucontrol_cold_reset(ipmi, args):
    ipmi.fru_control_cold_reset(0)

def usage(toplevel=False):
    commands = []
    maxlen = 0

    if toplevel:
        argv = []
    else:
        argv = sys.argv[1:]

    # (1) try to find help for commands on exactly one level above
    for cmd in COMMAND_HELP:
        subcommands = cmd.name.split(' ')
        if (len(subcommands) == len(argv) + 1
                and subcommands[:len(argv)] == argv):
            commands.append(cmd)
            if cmd.arguments:
                maxlen = max(maxlen, len(cmd.name)+len(cmd.arguments)+1)
            else:
                maxlen = max(maxlen, len(cmd.name))

    # (2) if nothing found, try to find help on any level above
    if maxlen == 0:
        for cmd in COMMAND_HELP:
            subcommands = cmd.name.split(' ')
            if (len(subcommands) > len(argv) + 1
                    and subcommands[:len(argv)] == argv):
                commands.append(cmd)
                if cmd.arguments:
                    maxlen = max(maxlen, len(cmd.name)+len(cmd.arguments)+1)
                else:
                    maxlen = max(maxlen, len(cmd.name))

    # (3) find help on same level
    if maxlen == 0:
        for cmd in COMMAND_HELP:
            subcommands = cmd.name.split(' ')
            if (len(subcommands) == len(argv)
                    and subcommands[:len(argv)] == argv):
                commands.append(cmd)
                if cmd.arguments:
                    maxlen = max(maxlen, len(cmd.name)+len(cmd.arguments)+1)
                else:
                    maxlen = max(maxlen, len(cmd.name))

    # if still nothing found, print toplevel usage
    if maxlen == 0:
        usage(toplevel=True)
        return

    if len(argv) == 0:
        version()
        print('usage: ipmitool [options...] <command>')
        print('''
Options:
  -t <addr>        Set target IPMB address
  -b <channel>     Set target channel
  -r <rtr>         Set target routing (not supported atm)
  -h               Show this help
  -v               Be verbose
  -V               Print version
  -I <interface>   Set interface (available: aardvark ipmitool)
  -H <host>        Set RMCP host
  -U <user>        Set RMCP user
  -P <password>    Set RMCP password
  -o <options>     Set interface specific options (name=value, separated
                   by commas, see below for available options).
'''[1:])
        print('''
Aardvark options:
  serial=<SN>       Serial number of the device
  pullups=<on|off>  Enable/disable pullups
  power=<on|off>    Enable/disable target power
'''[1:])
        print('Commands:')

    for cmd in commands:
        name = cmd.name
        if cmd.arguments:
            name = '%s %s' % (name, cmd.arguments)
        print('  %-*s   %s' % (maxlen, name, cmd.help))

def version():
    print('ipmitool v%s' % pyipmi.__version__)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 't:hvVI:H:U:P:o:b:')
    except getopt.GetoptError as err:
        print(str(err))
        usage()
        sys.exit(2)
    verbose = False
    interface_name = 'aardvark'
    target_address = 0x20
    target_routing = [(0x20,0)]
    rmcp_host = None
    rmcp_user = ''
    rmcp_password = ''
    interface_options = list()
    for o, a in opts:
        if o == '-v':
            verbose = True
        elif o == '-h':
            usage()
            sys.exit()
        elif o == '-V':
            version()
            sys.exit()
        elif o == '-t':
            target_address = int(a, 0)
        elif o == '-b':
            target_routing = [(0x20,int(a))]
        elif o == '-H':
            rmcp_host = a
        elif o == '-U':
            rmcp_user = a
        elif o == '-P':
            rmcp_password = a
        elif o == '-I':
            interface_name = a
        elif o == '-o':
            interface_options = a.split(',')
        else:
            assert False, 'unhandled option'

    # fake sys.argv
    sys.argv = [sys.argv[0]] + args

    if len(args) == 0:
        usage()
        sys.exit(1)

    handler = logging.StreamHandler()
    if verbose:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
    pyipmi.logger.add_log_handler(handler)
    pyipmi.logger.set_log_level(logging.DEBUG)

    for i in range(len(args)):
        cmd = _get_command_function(' '.join(args[0:i+1]))
        if cmd is not None:
            args = args[i+1:]
            break
    else:
        usage()
        sys.exit(1)


    aardvark_serial = None
    aardvark_pullups = None
    aardvark_target_power = None

    for option in interface_options:
        (name, value) = option.split('=', 1)
        if (interface_name, name) == ('aardvark', 'serial'):
            aardvark_serial = value
        elif (interface_name, name, value) == ('aardvark', 'pullups', 'on'):
            aardvark_pullups = True
        elif (interface_name, name, value) == ('aardvark', 'pullups', 'off'):
            aardvark_pullups = False
        elif (interface_name, name, value) == ('aardvark', 'power', 'on'):
            aardvark_target_power = True
        elif (interface_name, name, value) == ('aardvark', 'power', 'off'):
            aardvark_target_power = False
        else:
            print('Warning: unknown option %s' % name)

    try:
        if interface_name == 'aardvark':
            interface = pyipmi.interfaces.create_interface(interface_name,
                            serial_number=aardvark_serial)
        else:
            interface = pyipmi.interfaces.create_interface(interface_name)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    if aardvark_pullups:
        interface.enable_pullups(aardvark_pullups)
    if aardvark_target_power:
        interface.enable_target_power(aardvark_target_power)

    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(target_address)
    ipmi.target.set_routing_information(target_routing)

    if rmcp_host is not None:
        ipmi.session.set_session_type_rmcp(rmcp_host)
        ipmi.session.set_auth_type_user(rmcp_user, rmcp_password)
        ipmi.session.establish()

    try:
        cmd(ipmi, args)
    except pyipmi.errors.CompletionCodeError as e:
        print('Command returned with completion code 0x%02x' % e.cc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)
    except pyipmi.errors.TimeoutError as e:
        print('Command timed out')
        if verbose:
            traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt as e:
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    if rmcp_host is not None:
        ipmi.session.close()

COMMANDS = (
        Command('bmc info', cmd_bmc_info),
        Command('bmc reset cold', lambda i, a: i.cold_reset()),
        Command('bmc reset warm', lambda i, a: i.warm_reset()),
        Command('sel list', lambda i, a: list(map(_print, i.sel_entries()))),
        Command('sel clear', cmd_sel_clear),
        Command('sensor rearm', cmd_sensor_rearm),
        Command('sdr list', cmd_sdr_list),
        Command('sdr show', cmd_sdr_show),
        Command('sdr showall', cmd_sdr_show_all),
        Command('fru print', cmd_fru_print),
        Command('picmg frucontrol cr', cmd_picmg_frucontrol_cold_reset),
        Command('picmg power get', cmd_picmg_get_power),
        Command('picmg portstate get', cmd_picmg_get_portstate),
        Command('picmg portstate getall', cmd_picmg_get_portstate_all),
        Command('raw', cmd_raw),
        Command('hpm capabilities', cmd_hpm_capabilities),
        Command('hpm check', cmd_hpm_check_file),
        Command('hpm install', cmd_hpm_install),
        Command('chassis status', cmd_chassis_status),
        Command('chassis power off',
            lambda i, a: i.chassis_control_power_down()),
        Command('chassis power on',
            lambda i, a: i.chassis_control_power_up()),
        Command('chassis power cycle',
            lambda i, a: i.chassis_control_power_cycle()),
        Command('chassis power reset',
            lambda i, a: i.chassis_control_hard_reset()),
        Command('chassis power diag',
            lambda i, a: i.chassis_control_power_diagnostic_interrupt()),
        Command('chassis power soft',
            lambda i, a: i.chassis_control_power_soft_shutdown()),
)

COMMAND_HELP = (
        CommandHelp('raw', None, 'Send a RAW IPMI request and print response'),

        CommandHelp('fru', None,
                'Print built-in FRU and scan SDR for FRU locators'),

        CommandHelp('sensor', None, None),
        CommandHelp('sensor rearm', '<sensor-numer>', 'Rearm Sensor Events'),

        CommandHelp('sel', None, 'Print System Event Log (SEL)'),
        CommandHelp('sel list', None, 'List all SEL entries'),
        CommandHelp('sel clear', None, 'Clear SEL'),

        CommandHelp('sdr', None,
                'Print Sensor Data Repository entries and readings'),
        CommandHelp('sdr list', None, 'List all SDRs'),
        CommandHelp('sdr show', '<sdr-id>', 'Show detail for one SDR'),
        CommandHelp('sdr showall', None, 'Show detail for all SDRs'),

        CommandHelp('bmc', None,
                'Management Controller status and global enables'),
        CommandHelp('bmc info', None, 'BMC Device ID inforamtion'),
        CommandHelp('bmc reset', '<cold|warm>', 'BMC reset control'),

        CommandHelp('picmg', None, 'PICMG commands'),
        CommandHelp('picmg frucontrol', '<cr>', 'Issue frucontrol'),
        CommandHelp('picmg power get', 'get PICMG power level',
                'Request the power level'),
        CommandHelp('picmg portstate getall', '',
                'Request all portstates for all interfaces'),
        CommandHelp('picmg portstate get', '<channel> <interface>',
                'Request the portstate for an interface'),

        CommandHelp('hpm', None, 'HPM.1 commands'),
        CommandHelp('hpm capabilities', 'HPM.1 target upgrade capabilities',
                'Request the target upgrade capabilities'),
        CommandHelp('hpm check', 'HPM.1 file check',
                'Check the specified HPM.1 file'),
        CommandHelp('hpm install', '<file> <component id>',
                'Install the specified HPM.1 file to the controller'),

        CommandHelp('chassis', None, 'Get chassis status and set power state'),
        CommandHelp('chassis status', '', 'Get chassis status'),
        CommandHelp('chassis power', '<on|off|cycle|reset|diag|soft>',
            'Set power state')
)

if __name__ == '__main__':
    main()

