#!/usr/bin/env python

import pytest

from pyipmi import ipmitool
from pyipmi.ipmitool import build_parser, parse_interface_options
from pyipmi.sdr import SdrCommon


class TestParseInterfaceOptions:
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
        options = parse_interface_options('ipmitool', 'interface_type=abcd,cipher=55')
        assert options['interface_type'] == 'abcd'
        assert options['cipher'] == '55'

    def test_options_ipmbdev(self):
        options = parse_interface_options('ipmbdev', 'port=/dev/ipmb0')
        assert options['port'] == '/dev/ipmb0'

    def test_options_ipmidev(self):
        options = parse_interface_options('ipmidev', 'port=/dev/ipmi1,timeout=2')
        assert options['port'] == '/dev/ipmi1'
        assert options['timeout'] == 2.0

    def test_options_openipmblink(self):
        options = parse_interface_options(
            'openipmblink', 'port=socket://localhost:5555,bus=1,address=0x24')
        assert options['port'] == 'socket://localhost:5555'
        assert options['bus'] == 1
        assert options['slave_address'] == 0x24


class TestParser:
    def parse(self, command):
        return build_parser().parse_args(command.split())

    def test_global_options(self):
        args = self.parse('-I openipmblink -o port=/dev/x,bus=1 -t 0x82 '
                          '-b 7 -H host -p 0x26f -U user -P pass -L ADMIN '
                          '-v -J bmc info')
        assert args.interface == 'openipmblink'
        assert args.options == 'port=/dev/x,bus=1'
        assert args.target == 0x82
        assert args.channel == 7
        assert args.host == 'host'
        assert args.port == 623
        assert args.user == 'user'
        assert args.password == 'pass'
        assert args.priv_level == 'ADMIN'
        assert args.verbose
        assert args.json

    def test_defaults(self):
        args = self.parse('bmc info')
        assert args.target == 0x20
        assert args.port == 623
        assert args.options == ''
        assert args.func is ipmitool.cmd_bmc_info
        assert args.needs_connection

    @pytest.mark.parametrize('command, func', [
        ('bmc info', 'cmd_bmc_info'),
        ('bmc reset cold', 'cmd_bmc_reset'),
        ('chassis status', 'cmd_chassis_status'),
        ('chassis power cycle', 'cmd_chassis_power'),
        ('fru print', 'cmd_fru_print'),
        ('sdr list', 'cmd_sdr_list'),
        ('sdr raw 1', 'cmd_sdr_show_raw'),
        ('sdr show 1', 'cmd_sdr_show'),
        ('sdr showall', 'cmd_sdr_show_all'),
        ('sel list', 'cmd_sel_list'),
        ('sel clear', 'cmd_sel_clear'),
        ('sensor rearm 3', 'cmd_sensor_rearm'),
        ('hpm capabilities', 'cmd_hpm_capabilities'),
        ('hpm install file.img 2', 'cmd_hpm_install'),
        ('picmg frucontrol cr', 'cmd_picmg_frucontrol_cold_reset'),
        ('picmg power get', 'cmd_picmg_get_power'),
        ('picmg portstate get 1 0', 'cmd_picmg_get_portstate'),
        ('picmg portstate getall', 'cmd_picmg_get_portstate_all'),
        ('picmg channel status 1', 'cmd_picmg_getpower_channel_status'),
        ('picmg channel power 1', 'cmd_picmg_send_channel_power'),
        ('picmg send heartbeat', 'cmd_picmg_send_pm_heartbeat'),
        ('vita properties', 'cmd_vita_properties'),
        ('vita led set 0 1 255 0 3', 'cmd_vita_led_set'),
    ])
    def test_commands(self, command, func):
        assert self.parse(command).func is getattr(ipmitool, func)

    def test_raw(self):
        args = self.parse('raw 0x06 0x01')
        assert (args.lun, args.netfn, args.data) == (0, 6, [1])
        args = self.parse('raw -l 1 6 0x01 0x02')
        assert (args.lun, args.netfn, args.data) == (1, 6, [1, 2])

    def test_fru_print(self):
        args = self.parse('fru print')
        assert (args.fru_id, args.all) == (0, None)
        args = self.parse('fru print 2 all')
        assert (args.fru_id, args.all) == (2, 'all')

    def test_hpm_check_needs_no_connection(self):
        assert not self.parse('hpm check file.img').needs_connection

    def test_invalid_choice(self, capsys):
        with pytest.raises(SystemExit):
            self.parse('chassis power sideways')
        assert 'invalid choice' in capsys.readouterr().err

    def test_group_without_command_prints_help(self, capsys):
        with pytest.raises(SystemExit) as e:
            ipmitool.main(['vita', 'led'])
        assert e.value.code == 1
        out = capsys.readouterr().out
        assert 'usage: ipmitool.py vita led' in out
        assert 'prop' in out and 'set' in out

    def test_no_command_prints_help(self, capsys):
        with pytest.raises(SystemExit):
            ipmitool.main([])
        assert 'interface options' in capsys.readouterr().out

    def test_main_runs_command(self, monkeypatch):
        calls = []

        class FakeIpmi:
            def open(self):
                calls.append('open')

            def close(self):
                calls.append('close')

        def fake_connection(*args):
            calls.append(('connect',) + args)
            return FakeIpmi()

        monkeypatch.setattr(ipmitool, 'create_ipmi_connection',
                            fake_connection)
        monkeypatch.setattr(ipmitool, 'cmd_sel_clear',
                            lambda ipmi, args: calls.append('sel clear'))
        ipmitool.main(['-I', 'ipmbdev', '-o', 'port=/dev/ipmb-1',
                       '-t', '0x72', '-b', '7', 'sel', 'clear'])

        assert calls == [
            ('connect', 'ipmbdev', 'port=/dev/ipmb-1', 0x72, [(0x20, 7, 0)],
             None, 623, '', '', None),
            'open', 'sel clear', 'close']


class TestSdrShow:
    def test_mc_confirmation_record(self, capsys):
        data = [0x45, 0x00, 0x51, 0x13, 0x1b, 0x20, 0x00, 0x01,
                0x02, 0x01, 0x51, 0x4a, 0xc1, 0x62, 0x06, 0x80,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        ipmitool.sdr_show(None, SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert 'SDR record ID:    0x0045' in out
        assert 'SDR type:         0x13' in out
        assert 'Device Id string' not in out
        assert 'Entity' not in out
        assert 'Slave address:    0x20' in out
        assert 'Device revision:  1' in out
        assert 'Channel:          0' in out
        assert 'Firmware:         2.01' in out
        assert 'IPMI version:     1.5' in out
        assert 'Manufacturer ID:  0x2c14a' in out
        assert 'Product ID:       0x8006' in out

    @pytest.mark.parametrize('data', [
        # OEM record
        [0x05, 0x00, 0x51, 0xc0, 0x05, 0x57, 0x01, 0x00, 0xaa, 0xbb],
        # unknown record type
        [0x01, 0x00, 0x51, 0x0a, 0x00],
    ])
    def test_record_without_id_string(self, capsys, data):
        ipmitool.sdr_show(None, SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert 'SDR type:         0x%02x' % data[3] in out
        assert 'Device Id string' not in out

    def test_fru_device_locator_record(self, capsys):
        data = [0x02, 0x00, 0x51, 0x11, 0x10, 0x20, 0x00, 0x00,
                0x00, 0x00, 0x10, 0x00, 0x0a, 0x01, 0x00, 0xc4,
                0x46, 0x52, 0x55, 0x31]
        ipmitool.sdr_show(None, SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert 'Device Id string: FRU1' in out
        assert 'Entity:           10.1' in out
