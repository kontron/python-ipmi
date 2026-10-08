#!/usr/bin/env python

import pyipmi
import pyipmi.interfaces
import pyipmi.sdr

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
    # A BMC normally holds its sensor records in the SDR repository. The
    # device SDR commands (device_sdr_entries) are mostly used by satellite
    # controllers and are rejected by many BMCs with cc=0xc1.
    device_id = ipmi.get_device_id()
    if device_id.supports_function('sdr_repository'):
        entries = ipmi.sdr_repository_entries()
    elif device_id.supports_function('sensor'):
        entries = ipmi.device_sdr_entries()
    else:
        raise SystemExit('Device provides no SDRs')

    for sdr in entries:
        if sdr.type == pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD:
            (raw, states) = ipmi.get_sensor_reading(sdr.number,
                                                    sdr.owner_lun)
            value = sdr.convert_sensor_raw_to_value(raw)
            print(f'{sdr.device_id_string!s:<18} | {value!s:>10}')
        elif sdr.type == pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD:
            # compact records describe discrete sensors, there is no
            # conversion to a physical value
            (raw, states) = ipmi.get_sensor_reading(sdr.number,
                                                    sdr.owner_lun)
            print(f'{sdr.device_id_string!s:<18} | {raw!s:>10} | '
                  f'states=0x{states or 0:04x}')
