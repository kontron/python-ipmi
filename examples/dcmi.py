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
        print('Selector: {} '.format(selector))
        print('  version:  {} '.format(caps.specification_conformence))
        print('  revision: {}'.format(caps.parameter_revision))
        print('  data:     {}'.format(caps.parameter_data))

    rsp = ipmi.get_power_reading(1)

    print('Power Reading')
    print('  current:   {}'.format(rsp.current_power))
    print('  minimum:   {}'.format(rsp.minimum_power))
    print('  maximum:   {}'.format(rsp.maximum_power))
    print('  average:   {}'.format(rsp.average_power))
    print('  timestamp: {}'.format(rsp.timestamp))
    print('  period:    {}'.format(rsp.period))
    print('  state:     {}'.format(rsp.reading_state))

    ipmi.close()


if __name__ == '__main__':
    main()
