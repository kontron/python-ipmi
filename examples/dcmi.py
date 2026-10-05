#!/usr/bin/env python

import sys

import pyipmi
import pyipmi.interfaces


def main():

    if len(sys.argv) < 4:
        print('<HOST> <USER> <PASSWORD>')
        sys.exit(1)

    host = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]

    interface = pyipmi.interfaces.create_interface('ipmitool',
                                                   interface_type='lanplus')
    ipmi = pyipmi.create_connection(interface)
    ipmi.session.set_session_type_rmcp(host, 623)
    ipmi.session.set_auth_type_user(user, password)
    ipmi.target = pyipmi.Target(ipmb_address=0x20)
    ipmi.open()

    for selector in range(1, 6):
        caps = ipmi.get_dcmi_capabilities(selector)
        print(f'Selector: {selector} ')
        print(f'  version:  {caps.specification_conformence} ')
        print(f'  revision: {caps.parameter_revision}')
        print(f'  data:     {caps.parameter_data}')

    rsp = ipmi.get_power_reading(1)

    print('Power Reading')
    print(f'  current:   {rsp.current_power}')
    print(f'  minimum:   {rsp.minimum_power}')
    print(f'  maximum:   {rsp.maximum_power}')
    print(f'  average:   {rsp.average_power}')
    print(f'  timestamp: {rsp.timestamp}')
    print(f'  period:    {rsp.period}')
    print(f'  state:     {rsp.reading_state}')

    ipmi.close()


if __name__ == '__main__':
    main()
