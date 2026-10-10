#!/usr/bin/env python3

import pyipmi
import pyipmi.interfaces

# Read all sensor values of a BMC, similar to 'ipmitool sensor'.
#
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

with pyipmi.Ipmi(interface=intf, session=sess, target=target) as ipmi:
    # The records are read from the SDR repository of a BMC, or from the
    # device SDR repository of a satellite controller. Search them once,
    # e.g. with name='CPU*' or sensor_type='temperature', and keep them to
    # read the sensors repeatedly.
    for record in ipmi.find_sensors():
        reading = ipmi.read_sensor(record)
        # compact records describe discrete sensors, which have no value
        # in a physical unit but only states
        print(f'{reading.name:<18} | {reading.value!s:>10} '
              f'{reading.unit:<10} | {", ".join(reading.state_names())}')
