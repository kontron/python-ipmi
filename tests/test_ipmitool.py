#!/usr/bin/env python

from pyipmi.ipmitool import parse_interface_options


class TestParseInterfaceOptions(object):
    def test_options_aardvark(self):
        options = parse_interface_options('aardvark', 'serial=1234')
        assert options['serial_number'] == '1234'

        options = parse_interface_options('aardvark', 'pullups=on')
        assert options['enable_i2c_pullups'] is True

        options = parse_interface_options('aardvark', 'pullups=off')
        assert options['enable_i2c_pullups'] is False

        options = parse_interface_options('aardvark', 'power=on')
        assert options['enable_target_power'] is True

        options = parse_interface_options('aardvark', 'power=off')
        assert options['enable_target_power'] is False

        options = parse_interface_options('aardvark', 'fastmode=on')
        assert options['enable_fastmode'] is True

        options = parse_interface_options('aardvark', 'fastmode=off')
        assert options['enable_fastmode'] is False

    def test_options_ipmitool(self):
        options = parse_interface_options('ipmitool', 'interface_type=abcd')
        assert options['interface_type'] == 'abcd'

    def test_options_ipmbdev(self):
        options = parse_interface_options('ipmbdev', 'port=/dev/ipmb0')
        assert options['port'] == '/dev/ipmb0'
