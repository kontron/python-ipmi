#!/usr/bin/env python

import sys

import pyipmi
import pyipmi.interfaces

host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]

intf = pyipmi.interfaces.create_interface('rmcp+')

sess = pyipmi.Session()
sess.set_session_type_rmcp(host, 623)
sess.set_auth_type_user(user, password)
target = pyipmi.Target(ipmb_address=0x20)

# (1) The device connection can either be opened and closed
ipmi = pyipmi.Ipmi(interface=intf, session=sess, target=target)
ipmi.open()
device_id = ipmi.get_device_id()
ipmi.close()

# (2) or the 'with' statement can be used
with pyipmi.Ipmi(interface=intf, session=sess, target=target) as ipmi:
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
    print('Aux Firmware Rev Info:  [%s]' % (
            ' '.join('0x%02x' % d for d in device_id.aux)))
