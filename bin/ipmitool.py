#!/usr/bin/env python

from collections import namedtuple
import sys
import getopt

import pyipmi
import pyipmi.interfaces

IPMITOOL_VERSION = 0.1

Command = namedtuple('Command', ['name','fn','help'])

def cmd_bmc_info(ipmi, args):
    id = ipmi.get_device_id()
    print '''
Device ID:          %(id)s
Device Revision:    %(revision)s
Firmware Revision:  %(major_fw_revision)d.%(minor_fw_revision)d
IPMI Version:       %(major_ipmi_version)d.%(minor_ipmi_version)d
Manufacturer ID:    %(manufacturer_id)d (0x%(manufacturer_id)04x)
Product ID:         %(product_id)d (0x%(product_id)04x)
Device Available:   %(available)d
Provides SDRs:      %(provides_sdrs)d
Additional Device Support:
'''[1:-1] % id.__dict__

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
            print '  %s' % s

    if id.aux is not None:
        print 'Aux Firmware Rev Info:  [%02x %02x %02x %02x]' % (
                id.aux[0], id.aux[1], id.aux[2], id.aux[3])

def bmc_usage():
    print 'BMC Commands:'
    print '  reset [warm|cold]'
    print '  info'

def cmd_bmc(ipmi, args):
    if len(args) == 0:
        bmc_usage()
        sys.exit(1)

    if args[0] == 'reset':
        if len(args) == 2 and args[1] == 'warm':
            ipmi.warm_reset()
        elif len(args) == 2 and args[1] == 'cold':
            ipmi.cold_reset()
        else:
            bmc_usage()
            sys.exit(1)
    elif args[0] == 'info':
        cmd_bmc_info(ipmi, args[1:])
    else:
        bmc_usage()
        sys.exit(1)

def cmd_raw(ipmi, args):
    pass

def usage():
    print 'usage: ipmitool [options...] <command>'
    print 'Commands:'
    for cmd in GLOBAL_COMMANDS:
        print '    %-8s %s' % (cmd.name, cmd.help)

def version():
    print 'ipmitool v%s' % IPMITOOL_VERSION
    
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 't:hvVI:')
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    verbose = False
    interface = 'aardvark'
    target_address = 0x20
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
        elif o == '-I':
            interface = o
        else:
            assert False, 'unhandled option'

    if len(args) == 0:
        usage()
        sys.exit(1)

    (cmd_name, args) = (args[0], args[1:])

    for cmd in GLOBAL_COMMANDS:
        if cmd_name == cmd.name:
            fn = cmd.fn
            break
    else:
        usage()
        sys.exit(1)

    interface = pyipmi.interfaces.create_interface(interface)
    ipmi = pyipmi.create_connection(interface)
    #ipmi.session.set_session_type_rmcp(host)
    #ipmi.session.set_auth_type_user(user, password)
    ipmi.target = pyipmi.Target(target_address)
    #ipmi.session.establish()

    try:
        fn(ipmi, args)
    except pyipmi.errors.CompletionCodeError, e:
        print 'Command returned with completion code 0x%02x' % e.cc
    except pyipmi.errors.TimeoutError, e:
        print 'Command timed out'

    #ipmi.session.close()


GLOBAL_COMMANDS = (
        Command('bmc', cmd_bmc, 
            'Management Controller status and global enables'),
        Command('raw', cmd_raw,
            'Send a RAW IPMI request and print response'),
)

if __name__ == '__main__':
    main()

