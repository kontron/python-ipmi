#!/usr/bin/env python3

import pyipmi
import pyipmi.interfaces

# Test with ipmi_sim, a tool that ships with openipmi
# This should work with the default config file /etc/ipmi/ipmi.conf;
# just run ipmi_sim -p in another window to start the server
intf = pyipmi.interfaces.create_interface('rmcp',
                                          slave_address=0x81,
                                          host_target_address=0x20,
                                          keep_alive_interval=0)
sess = pyipmi.Session()
sess.set_session_type_rmcp('localhost', 9001)
sess.set_auth_type_user('ipmiusr', 'test')
sess.set_priv_level("ADMINISTRATOR")
target = pyipmi.Target(ipmb_address=0x20)

# (1) The device connection can either be opened and closed
ipmi = pyipmi.Ipmi(interface=intf, session=sess, target=target)
ipmi.open()
device_id = ipmi.get_device_id()
ipmi.close()

# (2) or the 'with' statement can be used
with pyipmi.Ipmi(interface=intf, session=sess, target=target) as ipmi:
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
