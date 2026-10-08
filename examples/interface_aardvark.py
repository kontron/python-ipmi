#!/usr/bin/env python

import pyipmi
import pyipmi.interfaces


interface = pyipmi.interfaces.create_interface('aardvark',
                                               slave_address=0x20,
                                               serial_number='2237-523145')
target = pyipmi.Target(ipmb_address=0xb4)

# (1) The device connection can either be opened and closed
ipmi = pyipmi.Ipmi(interface=interface, target=target)
ipmi.open()
device_id = ipmi.get_device_id()
ipmi.close()

# (2) or the 'with' statement can be used
with pyipmi.Ipmi(interface=interface, target=target) as ipmi:
    device_id = ipmi.get_device_id()

print(f'''
Device ID:          {device_id.device_id}
Device Revision:    {device_id.revision}
Firmware Revision:  {device_id.fw_revision}
IPMI Version:       {device_id.ipmi_version}
Manufacturer ID:    {device_id.manufacturer_id:d} (0x{device_id.manufacturer_id:04x})
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
          f"[{' '.join(f'0x{d:02x}' for d in device_id.aux)}]")
