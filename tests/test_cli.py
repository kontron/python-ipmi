#!/usr/bin/env python

import argparse
import json
import logging
import os

import pytest

from unittest.mock import MagicMock

from pyipmi import cli
from pyipmi.errors import CompletionCodeError, NotSupportedError
from pyipmi.msgs import create_response_by_name, decode_message
from pyipmi.cli import build_parser, log_level, parse_interface_options
from pyipmi.sdr import SdrCommon, SdrCompactSensorRecord, SdrFullSensorRecord
from pyipmi.sel import SelEntry
from pyipmi.sensor import SensorReading

from .ipmi_helper import create_ipmi


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

    def test_options_ipmitool_retries_timeout(self):
        options = parse_interface_options('ipmitool', 'retries=1,timeout=2')
        assert options['retries'] == 1
        assert options['timeout'] == 2

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


class TestLogLevel:
    @pytest.mark.parametrize('value, expected', [
        ('DEBUG', ('pyipmi', logging.DEBUG)),
        ('warning', ('pyipmi', logging.WARNING)),
        ('15', ('pyipmi', 15)),
        ('pyipmi=ERROR', ('pyipmi', logging.ERROR)),
        ('interfaces.aardvark=DEBUG',
         ('pyipmi.interfaces.aardvark', logging.DEBUG)),
        ('pyipmi.interfaces.router=info',
         ('pyipmi.interfaces.router', logging.INFO)),
    ])
    def test_valid(self, value, expected):
        assert log_level(value) == expected

    @pytest.mark.parametrize('value', ['', 'LOUD', 'interfaces.rmcp='])
    def test_invalid(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            log_level(value)

    def test_logger_names(self):
        names = cli.logger_names()
        assert 'interfaces.aardvark' in names
        assert 'interfaces.router' in names
        assert 'pyipmi' not in names

    def test_help_lists_loggers(self):
        assert 'interfaces.aardvark' in build_parser().format_help()

    def test_setup_logging(self):
        loggers = [logging.getLogger(n) for n in
                   ('pyipmi', 'pyipmi.interfaces.aardvark',
                    'pyipmi.interfaces.router')]
        saved = [(lg, lg.level, list(lg.handlers)) for lg in loggers]
        try:
            cli.setup_logging(False, [
                ('pyipmi.interfaces.aardvark', logging.DEBUG),
                ('pyipmi.interfaces.router', logging.ERROR)])
            assert not loggers[0].isEnabledFor(logging.DEBUG)
            assert loggers[1].isEnabledFor(logging.DEBUG)
            assert not loggers[2].isEnabledFor(logging.WARNING)
        finally:
            for lg, level, handlers in saved:
                lg.setLevel(level)
                lg.handlers[:] = handlers


class TestParser:
    def parse(self, command):
        return build_parser().parse_args(command.split())

    def test_global_options(self):
        args = self.parse('-I openipmblink -o port=/dev/x,bus=1 -t 0x82 '
                          '-b 7 -H host -p 0x26f -U user -P pass -L ADMINISTRATOR '
                          '-v -J bmc info')
        assert args.interface == 'openipmblink'
        assert args.options == 'port=/dev/x,bus=1'
        assert args.target == 0x82
        assert args.channel == 7
        assert args.host == 'host'
        assert args.port == 623
        assert args.user == 'user'
        assert args.password == 'pass'
        assert args.priv_level == 'administrator'
        assert args.verbose
        assert args.json

    def test_log_level(self):
        args = self.parse('--log-level INFO --log-level '
                          'interfaces.aardvark=DEBUG bmc info')
        assert args.log_levels == [
            ('pyipmi', logging.INFO),
            ('pyipmi.interfaces.aardvark', logging.DEBUG)]

    def test_defaults(self):
        args = self.parse('bmc info')
        assert args.target == 0x20
        assert args.port == 623
        assert args.options == ''
        assert args.func is cli.cmd_bmc_info
        assert args.needs_connection

    @pytest.mark.parametrize('command, func', [
        ('bmc info', 'cmd_bmc_info'),
        ('bmc reset cold', 'cmd_bmc_reset'),
        ('chassis status', 'cmd_chassis_status'),
        ('chassis power cycle', 'cmd_chassis_power'),
        ('chassis reset', 'cmd_chassis_reset'),
        ('chassis identify', 'cmd_chassis_identify'),
        ('chassis policy list', 'cmd_chassis_policy'),
        ('chassis restart-cause', 'cmd_chassis_restart_cause'),
        ('chassis poh', 'cmd_chassis_poh'),
        ('chassis capabilities', 'cmd_chassis_capabilities'),
        ('chassis buttons', 'cmd_chassis_buttons'),
        ('chassis cycle-interval 10', 'cmd_chassis_cycle_interval'),
        ('fru print', 'cmd_fru_print'),
        ('fru read 0 fru.bin', 'cmd_fru_read'),
        ('fru print-file fru.bin', 'cmd_fru_print_file'),
        ('lan print', 'cmd_lan_print'),
        ('lan set ipaddr 10.0.1.224', 'cmd_lan_set_ipaddr'),
        ('lan set ipsrc dhcp', 'cmd_lan_set_ipsrc'),
        ('lan set vlan off', 'cmd_lan_set_vlan'),
        ('sdr list', 'cmd_sdr_list'),
        ('sdr raw 1', 'cmd_sdr_show_raw'),
        ('sdr show 1', 'cmd_sdr_show'),
        ('sdr showall', 'cmd_sdr_show_all'),
        ('sdr info', 'cmd_sdr_info'),
        ('sdr device-info', 'cmd_sdr_device_info'),
        ('sdr time get', 'cmd_sdr_time_get'),
        ('sdr time set now', 'cmd_sdr_time_set'),
        ('sdr add 0 0 0x51 1 0', 'cmd_sdr_add'),
        ('sdr delete 1', 'cmd_sdr_delete'),
        ('sdr update-mode enter', 'cmd_sdr_update_mode'),
        ('sensor type 1', 'cmd_sensor_type'),
        ('sensor hysteresis 1', 'cmd_sensor_hysteresis'),
        ('sensor events 1', 'cmd_sensor_events'),
        ('sensor factors 1 0x80', 'cmd_sensor_factors'),
        ('sensor set-reading 1 0x42', 'cmd_sensor_set_reading'),
        ('sel list', 'cmd_sel_list'),
        ('sel clear', 'cmd_sel_clear'),
        ('sel info', 'cmd_sel_info'),
        ('sel time get', 'cmd_sel_time_get'),
        ('sel time set now', 'cmd_sel_time_set'),
        ('sel utc-offset', 'cmd_sel_utc_offset'),
        ('sel get 1', 'cmd_sel_get'),
        ('sel add' + ' 0' * 16, 'cmd_sel_add'),
        ('sel delete 1', 'cmd_sel_delete'),
        ('sel aux-status mca', 'cmd_sel_aux_status'),
        ('sensor rearm 3', 'cmd_sensor_rearm'),
        ('hpm capabilities', 'cmd_hpm_capabilities'),
        ('hpm install file.img 2', 'cmd_hpm_install'),
        ('picmg frucontrol cr', 'cmd_picmg_frucontrol_cold_reset'),
        ('picmg power get', 'cmd_picmg_get_power'),
        ('picmg portstate get 1 0', 'cmd_picmg_get_portstate'),
        ('picmg portstate getall', 'cmd_picmg_get_portstate_all'),
        ('picmg channel status 1', 'cmd_picmg_getpower_channel_status'),
        ('picmg channel power 1 on 2.5', 'cmd_picmg_send_channel_power'),
        ('picmg send heartbeat', 'cmd_picmg_send_pm_heartbeat'),
        ('vita properties', 'cmd_vita_properties'),
        ('vita led set 0 1 255 0 3', 'cmd_vita_led_set'),
        ('dcmi discover', 'cmd_dcmi_discover'),
        ('dcmi sensors', 'cmd_dcmi_sensors'),
        ('dcmi get_temp_reading', 'cmd_dcmi_get_temp_reading'),
        ('dcmi power reading', 'cmd_dcmi_power_reading'),
        ('dcmi power get_limit', 'cmd_dcmi_power_get_limit'),
        ('dcmi power set_limit 300 1000 5', 'cmd_dcmi_power_set_limit'),
        ('dcmi power activate', 'cmd_dcmi_power_activate'),
        ('dcmi power deactivate', 'cmd_dcmi_power_deactivate'),
        ('dcmi thermalpolicy get inlet 1', 'cmd_dcmi_thermalpolicy_get'),
        ('dcmi thermalpolicy set inlet 1 45 10',
         'cmd_dcmi_thermalpolicy_set'),
        ('dcmi asset_tag', 'cmd_dcmi_asset_tag'),
        ('dcmi set_asset_tag tag', 'cmd_dcmi_set_asset_tag'),
        ('dcmi get_mc_id_string', 'cmd_dcmi_get_mc_id_string'),
        ('dcmi set_mc_id_string bmc', 'cmd_dcmi_set_mc_id_string'),
        ('dcmi get_conf_param', 'cmd_dcmi_get_conf_param'),
        ('dcmi set_conf_param 3 64', 'cmd_dcmi_set_conf_param'),
    ])
    def test_commands(self, command, func):
        assert self.parse(command).func is getattr(cli, func)

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

    def test_fru_print_file(self):
        args = self.parse('fru print-file fru.bin')
        assert (args.filename, args.all) == ('fru.bin', None)
        assert not args.needs_connection
        args = self.parse('fru print-file fru.bin all')
        assert args.all == 'all'
        with pytest.raises(SystemExit):
            self.parse('fru print-file')

    @pytest.mark.parametrize('extra, expected, not_expected', [
        (['all'], 'd0 (OEM, manufacturer ID 11 = Hewlett-Packard)', 'Skipped'),
        ([], 'Skipped. Use "print-file <filename> all"', 'OEM'),
    ])
    def test_fru_print_file_runs_without_connection(self, capsys, extra,
                                                    expected, not_expected):
        path = os.path.join(os.path.dirname(__file__), 'fru_bin',
                            'HP_ProLiant_BL460c_Gen8.bin')
        cli.main(['fru', 'print-file', path] + extra)
        out = capsys.readouterr().out
        assert 'Product Name:       HP ProLiant BL460c Gen8' in out
        assert expected in out
        assert not_expected not in out

    @pytest.mark.parametrize('extra, data_printed', [(['all'], True),
                                                     ([], False)])
    def test_fru_print_file_internal_use_area(self, capsys, extra,
                                              data_printed):
        path = os.path.join(os.path.dirname(__file__), 'fru_bin',
                            'HP_ProLiant_BL460c_Gen8.bin')
        cli.main(['fru', 'print-file', path] + extra)
        out = capsys.readouterr().out
        assert ('Internal Use Area:\n'
                '  Format Version:     1\n'
                '  Data Length:        15\n') in out
        assert ('  Data:               02 01 00 85' in out) == data_printed

    @pytest.mark.parametrize('content, error', [
        (None, 'No such file'),
        (b'\x01\x00\x00\x00\x00\x00\x00\x00', 'checksum'),
    ])
    def test_fru_print_file_error(self, tmp_path, capsys, content, error):
        path = tmp_path / 'fru.bin'
        if content is not None:
            path.write_bytes(content)
        with pytest.raises(SystemExit) as e:
            cli.main(['fru', 'print-file', str(path)])
        assert e.value.code == 1
        assert error in capsys.readouterr().err

    def test_lan(self):
        args = self.parse('lan print')
        assert args.lan_channel is None
        # the bridge channel option -b is not the LAN channel
        args = self.parse('-b 7 lan print 2')
        assert (args.channel, args.lan_channel) == (7, 2)
        args = self.parse('lan set ipaddr 10.0.1.224 3')
        assert (args.address, args.lan_channel) == ('10.0.1.224', 3)
        assert self.parse('lan set ipsrc static').source == 'static'
        assert self.parse('lan set vlan off').vlan == 0
        assert self.parse('lan set vlan 394').vlan == 394

    @pytest.mark.parametrize('command', [
        'lan set ipaddr 10.0.1',
        'lan set ipaddr 10.0.1.256',
        'lan set ipsrc bios',
        'lan set vlan 4096',
        'lan set vlan on',
    ])
    def test_lan_invalid(self, command):
        with pytest.raises(SystemExit):
            self.parse(command)

    def test_fru_read(self):
        args = self.parse('fru read 0x02 fru.bin')
        assert (args.fru_id, args.filename) == (2, 'fru.bin')
        with pytest.raises(SystemExit):
            self.parse('fru read 0')

    def test_dcmi_entity(self):
        assert self.parse('dcmi get_temp_reading').entity is None
        assert self.parse('dcmi get_temp_reading cpu').entity == 0x41
        assert self.parse('dcmi get_temp_reading 0x37').entity == 0x37
        args = self.parse('dcmi thermalpolicy get baseboard 2')
        assert (args.entity, args.instance) == (0x42, 2)

    def test_dcmi_invalid_entity(self, capsys):
        with pytest.raises(SystemExit):
            self.parse('dcmi get_temp_reading gpu')
        assert 'invalid entity' in capsys.readouterr().err

    def test_dcmi_power_set_limit(self):
        args = self.parse('dcmi power set_limit 300 1000 5')
        assert (args.limit, args.correction_time, args.sampling_period,
                args.action) == (300, 1000, 5, 'no_action')
        args = self.parse('dcmi power set_limit 300 1000 5 '
                          '--action power_off')
        assert args.action == 'power_off'

    def test_dcmi_thermalpolicy_set(self):
        args = self.parse('dcmi thermalpolicy set cpu 1 80 30 --power-off')
        assert (args.entity, args.instance, args.limit,
                args.exception_time) == (0x41, 1, 80, 30)
        assert args.power_off and not args.log_sel and not args.disable

    def test_dcmi_set_conf_param_invalid_selector(self, capsys):
        with pytest.raises(SystemExit):
            self.parse('dcmi set_conf_param 6 1')
        assert 'invalid choice' in capsys.readouterr().err

    def test_hpm_check_needs_no_connection(self):
        assert not self.parse('hpm check file.img').needs_connection

    def test_hpm_check_runs_without_connection(self, capsys):
        path = os.path.join(os.path.dirname(__file__), 'hpm_bin',
                            'firmware.hpm')
        cli.main(['hpm', 'check', path])
        out = capsys.readouterr().out
        assert 'HPM Upgrade Image header' in out
        assert 'Upload Firmware Image' in out
        assert 'Manufacturer:     15000 = Kontron' in out

    def test_invalid_choice(self, capsys):
        with pytest.raises(SystemExit):
            self.parse('chassis power sideways')
        assert 'invalid choice' in capsys.readouterr().err

    def test_group_without_command_prints_help(self, capsys):
        with pytest.raises(SystemExit) as e:
            cli.main(['vita', 'led'])
        assert e.value.code == 1
        out = capsys.readouterr().out
        assert 'usage: pyipmi vita led' in out
        assert 'prop' in out and 'set' in out

    def test_no_command_prints_help(self, capsys):
        with pytest.raises(SystemExit):
            cli.main([])
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

        monkeypatch.setattr(cli, 'create_ipmi_connection',
                            fake_connection)
        monkeypatch.setattr(cli, 'cmd_sel_clear',
                            lambda ipmi, args: calls.append('sel clear'))
        cli.main(['-I', 'ipmbdev', '-o', 'port=/dev/ipmb-1',
                       '-t', '0x72', '-b', '7', 'sel', 'clear'])

        assert calls == [
            ('connect', 'ipmbdev', 'port=/dev/ipmb-1', 0x72, None,
             None, 623, '', '', None, 7),
            'open', 'sel clear', 'close']


class TestChassisPower:
    # the control values of the Chassis Control command
    @pytest.mark.parametrize('action, control', [
        ('off', 0),
        ('on', 1),
        ('cycle', 2),
        ('reset', 3),
        ('diag', 4),
        ('soft', 5),
    ])
    def test_chassis_power(self, action, control):
        ipmi = create_ipmi(b'\x00')
        args = build_parser().parse_args(['chassis', 'power', action])
        cli.cmd_chassis_power(ipmi, args)
        assert ipmi.requests == [('ChassisControlReq', bytes([control]))]


class TestChassisCommands:
    @staticmethod
    def run(command, rsp_data):
        ipmi = create_ipmi(rsp_data)
        args = build_parser().parse_args(['chassis'] + command.split())
        args.func(ipmi, args)
        return ipmi

    def test_reset(self):
        ipmi = self.run('reset', b'\x00')
        assert ipmi.requests == [('ChassisResetReq', b'')]

    @pytest.mark.parametrize('command, data, output', [
        ('identify', b'', 'default (15 seconds)'),
        ('identify 30', b'\x1e', '30 seconds'),
        ('identify 0', b'\x00', 'off'),
        ('identify force', b'\x00\x01', 'indefinite'),
    ])
    def test_identify(self, capsys, command, data, output):
        ipmi = self.run(command, b'\x00')
        assert ipmi.requests == [('ChassisIdentifyReq', data)]
        assert capsys.readouterr().out == \
            f'Chassis identify interval: {output}\n'

    @pytest.mark.parametrize('interval', ['256', '-1', 'on'])
    def test_identify_invalid_interval(self, capsys, interval):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['chassis', 'identify', interval])
        assert 'invalid interval' in capsys.readouterr().err

    def test_policy_list(self, capsys):
        ipmi = self.run('policy list', b'\x00\x05')
        # the policy is not changed
        assert ipmi.requests == [('SetPowerRestorePolicyReq', b'\x03')]
        assert capsys.readouterr().out == (
            'Supported chassis power restore policies: always-off '
            'always-on\n')

    @pytest.mark.parametrize('policy, data', [
        ('always-off', b'\x00'),
        ('previous', b'\x01'),
        ('always-on', b'\x02'),
    ])
    def test_policy_set(self, capsys, policy, data):
        ipmi = self.run(f'policy {policy}', b'\x00\x07')
        assert ipmi.requests == [('SetPowerRestorePolicyReq', data)]
        out = capsys.readouterr().out
        assert out.startswith(f'Set chassis power restore policy to '
                              f'{policy}\n')

    @pytest.mark.parametrize('rsp, output', [
        (b'\x00\x04\x01', 'System restart cause: watchdog expiration\n'
                           'Channel:              1\n'),
        (b'\x00\x02', 'System restart cause: reset via pushbutton\n'),
    ])
    def test_restart_cause(self, capsys, rsp, output):
        ipmi = self.run('restart-cause', rsp)
        assert ipmi.requests == [('GetSystemRestartCauseReq', b'')]
        assert capsys.readouterr().out == output

    def test_poh(self, capsys):
        # 60 minutes per count, 51 counts: 2 days and 3 hours
        self.run('poh', b'\x00\x3c\x33\x00\x00\x00')
        assert capsys.readouterr().out == 'POH Counter: 2 days, 3 hours\n'

    @pytest.mark.parametrize('rsp, bridge', [
        (b'\x00\x09\x20\x22\x24\x26\x28', '0x28'),
        (b'\x00\x09\x20\x22\x24\x26', 'na'),
    ])
    def test_capabilities(self, capsys, rsp, bridge):
        self.run('capabilities', rsp)
        out = capsys.readouterr().out
        assert 'Intrusion Sensor:         True\n' in out
        assert 'Front Panel Lockout:      False\n' in out
        assert 'Power Interlock:          True\n' in out
        assert 'SEL Device:               0x24\n' in out
        assert out.endswith(f'Bridge Device:            {bridge}\n')

    # front panel buttons: all can be disabled except standby, reset is
    # disabled
    STATUS_RSP = b'\x00\x01\x00\x00\x72'

    def test_buttons_print(self, capsys):
        ipmi = self.run('buttons', self.STATUS_RSP)
        assert ipmi.requests == [('GetChassisStatusReq', b'')]
        assert capsys.readouterr().out == (
            'Power Off Button:            enabled\n'
            'Reset Button:                disabled\n'
            'Diagnostic Interrupt Button: enabled\n'
            'Standby Button:              enabled (cannot be disabled)\n')

    @pytest.mark.parametrize('command, data', [
        # the state of the other buttons is kept
        ('buttons disable power-off', b'\x03'),
        ('buttons enable reset', b'\x00'),
        ('buttons disable diag standby', b'\x0e'),
    ])
    def test_buttons_set(self, command, data):
        ipmi = self.run(command, {'GetChassisStatus': self.STATUS_RSP,
                                  'SetFrontPanelButtonEnables': b'\x00'})
        assert ipmi.requests[1] == ('SetFrontPanelButtonEnablesReq', data)

    def test_buttons_without_button(self, capsys):
        with pytest.raises(SystemExit) as e:
            self.run('buttons enable', self.STATUS_RSP)
        assert e.value.code == 1
        assert 'No button to enable given' in capsys.readouterr().err

    def test_buttons_not_reported(self, capsys):
        with pytest.raises(SystemExit) as e:
            self.run('buttons', b'\x00\x01\x00\x00')
        assert e.value.code == 1
        assert 'does not report the front panel buttons' in \
            capsys.readouterr().err

    def test_buttons_invalid(self, capsys):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['chassis', 'buttons', 'enable',
                                       'eject'])
        assert 'invalid button: eject' in capsys.readouterr().err

    def test_cycle_interval(self):
        ipmi = self.run('cycle-interval 10', b'\x00')
        assert ipmi.requests == [('SetPowerCycleIntervalReq', b'\x0a')]

    def test_cycle_interval_invalid(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['chassis', 'cycle-interval', '256'])


class TestCreateIpmiConnection:
    @staticmethod
    def routing(ipmi):
        return [(r.rq_sa, r.rs_sa, r.channel) for r in ipmi.target.routing]

    def test_channel_rmcp(self):
        # like ipmitool -t 0x82 -b 0: bridged by the BMC on channel 0
        ipmi = cli.create_ipmi_connection('rmcp', None, 0x82, None,
                                               '10.0.0.1', 623, 'admin',
                                               'admin', None, 0)
        assert ipmi.target.ipmb_address == 0x82
        assert self.routing(ipmi) == [(0x81, 0x20, 0), (0x20, 0x82, None)]

    def test_channel_ipmitool(self):
        ipmi = cli.create_ipmi_connection('ipmitool', None, 0x72, None,
                                               '10.0.0.1', 623, 'admin',
                                               'admin', None, 7)
        ipmi.interface.establish_session(ipmi.session)
        assert ipmi.interface._build_ipmitool_target(ipmi.target) \
            == ' -t 0x72 -b 7'

    def test_channel_uses_own_address(self, monkeypatch):
        # the requester of the first hop is the own address of the interface
        interface = MagicMock(slave_address=0x24)
        monkeypatch.setattr(cli.pyipmi.interfaces, 'create_interface',
                            lambda name, **kwargs: interface)
        ipmi = cli.create_ipmi_connection('openipmblink', None, 0x72,
                                               None, None, 623, '', '', None,
                                               7)
        assert self.routing(ipmi) == [(0x24, 0x20, 7), (0x20, 0x72, None)]

    def test_routing(self):
        ipmi = cli.create_ipmi_connection('rmcp', None, 0x72,
                                               '[(0x81,0x20,0),(0x20,0x72,None)]',
                                               '10.0.0.1', 623, 'admin',
                                               'admin', None)
        assert self.routing(ipmi) == [(0x81, 0x20, 0), (0x20, 0x72, None)]


class TestSdrShow:
    def test_mc_confirmation_record(self, capsys):
        data = [0x45, 0x00, 0x51, 0x13, 0x1b, 0x20, 0x00, 0x01,
                0x02, 0x01, 0x51, 0x4a, 0xc1, 0x62, 0x06, 0x80,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        cli.sdr_show(SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert out == (
            'Record ID:              0x0045\n'
            'Record Type:            [0x13] Management Controller '
            'Confirmation Record\n'
            'Slave Address:          0x20\n'
            'Device ID:              0x00\n'
            'Device Revision:        [0x01] 1\n'
            'Channel:                [0x00] 0\n'
            'Firmware Revision:      [0x02 0x01] 2.01\n'
            'IPMI Version:           [0x51] 1.5\n'
            'Manufacturer:           [0x2c14a] Unknown\n'
            'Product ID:             0x8006\n')

    def test_mc_confirmation_record_manufacturer_name(self, capsys):
        # manufacturer ID 15000
        data = [0x45, 0x00, 0x51, 0x13, 0x1b, 0x20, 0x00, 0x01,
                0x02, 0x01, 0x51, 0x98, 0x3a, 0x00, 0x06, 0x80,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        record = SdrCommon.from_data(data)
        assert record.manufacturer_name == 'Kontron'
        cli.sdr_show(record)

        out = capsys.readouterr().out
        assert 'Manufacturer:           [0x03a98] Kontron' in out

    @pytest.mark.parametrize('data, lines', [
        # OEM record
        ([0x05, 0x00, 0x51, 0xc0, 0x05, 0x57, 0x01, 0x00, 0xaa, 0xbb],
         ['Record Type:            [0xc0] OEM Record',
          'Manufacturer:           [0x00157] Intel',
          'OEM Data:               aa bb']),
        # unknown record type
        ([0x01, 0x00, 0x51, 0x0a, 0x00],
         ['Record Type:            [0x0a] Unknown Record',
          'Raw Data:               01 00 51 0a 00']),
    ])
    def test_record_without_id_string(self, capsys, data, lines):
        cli.sdr_show(SdrCommon.from_data(data))

        out = capsys.readouterr().out
        for line in lines:
            assert line in out
        assert 'Name:' not in out

    def test_fru_device_locator_record(self, capsys):
        data = [0x02, 0x00, 0x51, 0x11, 0x10, 0x20, 0x00, 0x00,
                0x00, 0x00, 0x10, 0x00, 0x0a, 0x01, 0x00, 0xc4,
                0x46, 0x52, 0x55, 0x31]
        cli.sdr_show(SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert out == (
            'Record ID:              0x0002\n'
            'Record Type:            [0x11] FRU Device Locator Record\n'
            'Name:                   FRU1\n'
            'Entity:                 [0x0a 0x01] Power Supply\n'
            'Device Access Address:  0x20\n'
            'FRU Device Address:     0x00\n'
            'Private Bus:            [0x00] 0\n'
            'Access LUN:             [0x00] 0\n'
            'Channel:                [0x00] 0\n'
            'Device Type:            0x10 modifier 0x00\n')

    # temperature sensor 4 of the BMC with the readable upper thresholds
    FULL_RECORD = bytes([
        0x01, 0x00, 0x51, 0x01, 0x00, 0x20, 0x00, 0x04, 0x03, 0x01,
        0x7f, 0x68, 0x01, 0x01, 0x80, 0x0a, 0x80, 0x7a, 0x38, 0x38,
        0x00, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x01, 40, 80, 10, 127, 0, 100, 90, 80, 0, 0, 0, 2, 2, 0, 0, 0,
        0xc8]) + b'CPU Temp'

    # sensor-specific slot/connector sensor of the controller 0x82
    COMPACT_RECORD = bytes([
        0xd3, 0x00, 0x51, 0x02, 0x28, 0x82, 0x00, 0xd3, 0xc1, 0x64,
        0x03, 0x40, 0x21, 0x6f, 0x05, 0x00, 0x01, 0x00, 0x03, 0x00,
        0xc0, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0xcd]) + b'A4:Pres SFP-1'

    def test_full_sensor_record(self, capsys):
        cli.sdr_show(SdrCommon.from_data(self.FULL_RECORD))

        # the bits 14:12 of the deassertion mask are no events
        assert capsys.readouterr().out == (
            'Record ID:              0x0001\n'
            'Record Type:            [0x01] Full Sensor Record\n'
            'Name:                   CPU Temp\n'
            'Entity:                 [0x03 0x01] Processor\n'
            'Sensor Owner:           [0x20 0x00] IPMB 0x20 LUN 0\n'
            'Sensor Number:          0x04\n'
            'Sensor Type:            [0x01] Temperature\n'
            'Event/Reading Type:     [0x01] Threshold\n'
            'Upper Non-recoverable:  [0x64] 100.000 degrees C\n'
            'Upper Critical:         [0x5a] 90.000 degrees C\n'
            'Upper Non-critical:     [0x50] 80.000 degrees C\n'
            'Nominal Reading:        [0x28] 40.000 degrees C\n'
            'Sensor Minimum:         [0x00] 0.000 degrees C\n'
            'Sensor Maximum:         [0x7f] 127.000 degrees C\n'
            'Assertion Events:       [0x0a80]\n'
            '                        Upper Non-critical going high\n'
            '                        Upper Critical going high\n'
            '                        Upper Non-recoverable going high\n'
            'Deassertion Events:     [0x7a80]\n'
            '                        Upper Non-critical going high\n'
            '                        Upper Critical going high\n'
            '                        Upper Non-recoverable going high\n')

    def test_compact_sensor_record(self, capsys):
        cli.sdr_show(SdrCommon.from_data(self.COMPACT_RECORD))

        assert capsys.readouterr().out == (
            'Record ID:              0x00d3\n'
            'Record Type:            [0x02] Compact Sensor Record\n'
            'Name:                   A4:Pres SFP-1\n'
            'Entity:                 [0xc1 0x64] PICMG AdvancedMC '
            'Module\n'
            'Sensor Owner:           [0x82 0x00] IPMB 0x82 LUN 0\n'
            'Sensor Number:          0xd3\n'
            'Sensor Type:            [0x21] Slot / Connector\n'
            'Event/Reading Type:     [0x6f] Sensor-specific\n'
            'Assertion Events:       [0x0005]\n'
            '                        Fault Status Asserted\n'
            '                        Slot / Connector Device '
            'Installed/Attached\n'
            'Deassertion Events:     [0x0001]\n'
            '                        Fault Status Asserted\n')

    def test_compact_threshold_sensor_record(self, capsys):
        # a compact record has no conversion, only the unit is printed
        data = bytearray(self.COMPACT_RECORD)
        data[13] = 0x01
        data[21] = 0x04
        cli.sdr_show(SdrCommon.from_data(bytes(data)))

        out = capsys.readouterr().out
        assert ('Event/Reading Type:     [0x01] Threshold\n'
                'Unit:                   [0xc0 0x04 0x00] Volts\n') in out

    def test_mc_device_locator_record(self, capsys):
        data = [0x00, 0x01, 0x51, 0x12, 0x0f, 0x20, 0x00, 0x00,
                0x29, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0xc4,
                0x42, 0x4d, 0x43, 0x30]
        cli.sdr_show(SdrCommon.from_data(data))

        assert capsys.readouterr().out.endswith(
            'Slave Address:          0x20\n'
            'Channel:                [0x00] 0\n'
            'Device Capabilities:    [0x29]\n'
            '                        Sensor Device\n'
            '                        FRU Inventory Device\n'
            '                        IPMB Event Generator\n')


class TestDcmiCommands:
    def setup_method(self):
        self.ipmi = MagicMock()

    def run(self, command):
        args = build_parser().parse_args(command.split())
        args.func(self.ipmi, args)
        return args

    def test_discover(self, capsys):
        rsp = create_response_by_name('GetDcmiCapabilities')
        decode_message(rsp, b'\x00\xdc\x01\x05\x02\x00\x01\x05')
        self.ipmi.get_dcmi_capabilities.side_effect = [
            rsp, rsp, rsp, CompletionCodeError(0xcc), rsp]

        self.run('dcmi discover')

        out = capsys.readouterr().out.splitlines()
        assert len(out) == 5
        assert out[0] == ('Supported DCMI capabilities                  : '
                          '00 01 05 (DCMI 1.5, revision 2)')
        assert out[3].endswith('ERR: CC=0xcc (Invalid data field in Request)')

    def test_power_reading(self, capsys):
        rsp = create_response_by_name('GetPowerReading')
        decode_message(rsp, b'\x00\xdc\x64\x00\x32\x00\xc8\x00\x78\x00'
                            b'\x10\x20\x30\x40\xe8\x03\x00\x00\x40')
        self.ipmi.get_power_reading.return_value = rsp

        self.run('dcmi power reading')

        self.ipmi.get_power_reading.assert_called_once_with(1)
        out = capsys.readouterr().out
        assert 'Instantaneous power reading :   100 Watts' in out
        assert 'Average power               :   120 Watts' in out
        assert 'Power reading state         : activated' in out

    def test_power_get_limit(self, capsys):
        rsp = create_response_by_name('GetPowerLimit')
        decode_message(rsp, b'\x00\xdc\x00\x00\x01\x2c\x01'
                            b'\xe8\x03\x00\x00\x00\x00\x05\x00')
        self.ipmi.get_power_limit.return_value = rsp

        self.run('dcmi power get_limit')

        out = capsys.readouterr().out
        assert 'Exception actions      : power_off' in out
        assert 'Power limit            : 300 Watts' in out
        assert 'Correction time        : 1000 ms' in out
        assert 'Sampling period        : 5 s' in out

    def test_power_set_limit(self):
        self.run('dcmi power set_limit 300 1000 5 --action sel_logging')
        self.ipmi.set_power_limit.assert_called_once_with(300, 1000, 5, 0x11)

    def test_power_activate_deactivate(self):
        self.run('dcmi power activate')
        self.ipmi.activate_power_limit.assert_called_once_with()
        self.run('dcmi power deactivate')
        self.ipmi.deactivate_power_limit.assert_called_once_with()

    def test_sensors(self, capsys):
        self.ipmi.get_dcmi_sensor_record_ids.return_value = [0x10, 0x20]
        sdr = MagicMock(device_id_string='Inlet Temp')
        self.ipmi.get_repository_sdr.side_effect = [
            sdr, CompletionCodeError(0xcb)]

        self.run('dcmi sensors')

        assert capsys.readouterr().out.splitlines() == [
            '0x0010 | Inlet Temp', '0x0020 | ']

    def test_get_temp_reading_all(self, capsys):
        self.ipmi.get_temperature_readings.side_effect = [
            [(1, 25)], [(1, 45), (2, -5)], CompletionCodeError(0xcb)]

        self.run('dcmi get_temp_reading')

        assert capsys.readouterr().out.splitlines() == [
            'inlet      |   1 |  +25 C',
            'cpu        |   1 |  +45 C',
            'cpu        |   2 |   -5 C',
            'baseboard  | ERR: CC=0xcb (Requested data not present)']

    def test_get_temp_reading_entity(self):
        self.ipmi.get_temperature_readings.return_value = []
        self.run('dcmi get_temp_reading 0x37')
        self.ipmi.get_temperature_readings.assert_called_once_with(0x37)

    def test_thermalpolicy_get(self, capsys):
        rsp = create_response_by_name('GetThermalLimit')
        decode_message(rsp, b'\x00\xdc\xa0\x2d\x2c\x01')
        self.ipmi.get_thermal_limit.return_value = rsp

        self.run('dcmi thermalpolicy get inlet 1')

        self.ipmi.get_thermal_limit.assert_called_once_with(0x40, 1)
        out = capsys.readouterr().out
        assert 'Exception actions    : enabled' in out
        assert '  Hard power off     : inactive' in out
        assert '  Log event to SEL   : active' in out
        assert 'Temperature limit    : 45 C' in out
        assert 'Exception time       : 300 s' in out

    def test_thermalpolicy_set(self):
        self.run('dcmi thermalpolicy set cpu 2 80 30 --log-sel')
        self.ipmi.set_thermal_limit.assert_called_once_with(
            0x41, 2, 80, 30, enable=True, hard_power_off=False,
            log_event_to_sel=True)

    def test_asset_tag(self, capsys):
        self.ipmi.get_asset_tag.return_value = 'my tag'
        self.run('dcmi asset_tag')
        assert capsys.readouterr().out == 'Asset tag: my tag\n'

        self.run('dcmi set_asset_tag new')
        self.ipmi.set_asset_tag.assert_called_once_with('new')

    def test_mc_id_string(self, capsys):
        self.ipmi.get_management_controller_id_string.return_value = 'bmc'
        self.run('dcmi get_mc_id_string')
        assert capsys.readouterr().out == \
            'Management controller ID string: bmc\n'

        self.run('dcmi set_mc_id_string new')
        self.ipmi.set_management_controller_id_string.assert_called_once_with(
            'new')

    def test_get_conf_param(self, capsys):
        rsp = create_response_by_name('GetDcmiConfigurationParameters')
        decode_message(rsp, b'\x00\xdc\x01\x05\x01\x3c\x00')
        self.ipmi.get_dcmi_configuration_parameters.return_value = rsp

        self.run('dcmi get_conf_param 5')

        self.ipmi.get_dcmi_configuration_parameters.assert_called_once_with(5)
        assert capsys.readouterr().out == 'DHCP timing 3           : 3c 00\n'

    @pytest.mark.parametrize('command, selector, data', [
        ('dcmi set_conf_param 3 64', 3, b'\x40'),
        ('dcmi set_conf_param 5 0x3c', 5, b'\x3c\x00'),
    ])
    def test_set_conf_param(self, command, selector, data):
        self.run(command)
        self.ipmi.set_dcmi_configuration_parameters.assert_called_once_with(
            selector, data)


def test_cmd_fru_read(tmp_path, capsys):
    ipmi = MagicMock()
    ipmi.read_fru_data_full.return_value = bytes(range(256))
    filename = tmp_path / 'fru.bin'
    args = build_parser().parse_args(['fru', 'read', '1', str(filename)])
    args.func(ipmi, args)

    ipmi.read_fru_data_full.assert_called_once_with(1)
    assert filename.read_bytes() == bytes(range(256))
    assert capsys.readouterr().out == (
        f'Read 256 bytes from FRU 1 to {filename}\n')


@pytest.mark.parametrize('manufacturer, name', [
    (b'\x98\x3a\x00', 'Kontron'),
    (b'\x39\x30\x00', 'Unknown'),
])
def test_bmc_info_manufacturer_name(capsys, manufacturer, name):
    ipmi = create_ipmi(b'\x00\x04\x00\x01\x00\x02\x00' + manufacturer
                       + b'\xa5\x06')
    cli.cmd_bmc_info(ipmi, None)
    out = capsys.readouterr().out
    assert f'Manufacturer Name:  {name}\n' in out
    # the IDs are shown in decimal and hex
    assert 'Device ID:          4 (0x04)\n' in out
    assert 'Product ID:         1701 (0x06a5)\n' in out


def lan_rsp(data):
    """Return a Get LAN Configuration Parameters response."""
    # completion code, parameter revision, data
    return b'\x00\x11' + bytes(data)


# Get Channel Info response: channel 1 is an 802.3 LAN channel
LAN_CHANNEL_INFO_RSP = b'\x00\x01\x04\x01\x80\xf2\x1b\x00\x00\x00'


def run_command(ipmi, command):
    args = build_parser().parse_args(command.split())
    args.func(ipmi, args)


def test_lan_print(capsys):
    ipmi = create_ipmi({
        'GetChannelInfo': LAN_CHANNEL_INFO_RSP,
        'GetLanConfigurationParameters': [
            lan_rsp([2]),                       # IP address source
            lan_rsp([10, 0, 1, 224]),           # IP address
            lan_rsp([255, 255, 255, 0]),        # subnet mask
            lan_rsp([0, 0x11, 0x22, 0x33, 0x44, 0x55]),   # MAC address
            lan_rsp([10, 0, 1, 1]),             # default gateway
            lan_rsp([0, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e]),   # gateway MAC
            lan_rsp([0x8a, 0x81]),              # VLAN 394
        ],
    })
    run_command(ipmi, 'lan print')
    assert capsys.readouterr().out == (
        'Channel:             1\n'
        'IP Address Source:   dhcp\n'
        'IP Address:          10.0.1.224\n'
        'Subnet Mask:         255.255.255.0\n'
        'MAC Address:         00:11:22:33:44:55\n'
        'Default Gateway IP:  10.0.1.1\n'
        'Default Gateway MAC: 00:0a:0b:0c:0d:0e\n'
        '802.1q VLAN ID:      394\n')
    # all parameters are read from the LAN channel 1
    assert all(data[0] == 1 for (name, data) in ipmi.requests
               if name == 'GetLanConfigurationParametersReq')


def test_lan_print_not_supported(capsys):
    ipmi = create_ipmi({
        'GetLanConfigurationParameters': [
            lan_rsp([1]),
            lan_rsp([10, 0, 1, 224]),
            lan_rsp([255, 255, 255, 0]),
            lan_rsp([0, 0x11, 0x22, 0x33, 0x44, 0x55]),
            # the gateway parameters are not supported
            b'\x80',
            b'\x80',
            lan_rsp([0, 0]),                    # VLAN disabled
        ],
    })
    run_command(ipmi, 'lan print 2')
    out = capsys.readouterr().out
    assert 'Channel:             2\n' in out
    assert 'IP Address Source:   static\n' in out
    assert 'Default Gateway IP:  not supported\n' in out
    assert 'Default Gateway MAC: not supported\n' in out
    assert '802.1q VLAN ID:      disabled\n' in out


@pytest.mark.parametrize('command, data', [
    ('lan set ipaddr 10.0.1.224 1', b'\x01\x03\x0a\x00\x01\xe0'),
    ('lan set ipsrc dhcp 1', b'\x01\x04\x02'),
    ('lan set ipsrc static 1', b'\x01\x04\x01'),
    ('lan set vlan 394 1', b'\x01\x14\x8a\x81'),
    ('lan set vlan off 1', b'\x01\x14\x00\x00'),
])
def test_lan_set(command, data):
    ipmi = create_ipmi(b'\x00')
    run_command(ipmi, command)
    assert ipmi.requests == [('SetLanConfigurationParametersReq', data)]


def test_lan_set_lan_channel(capsys):
    # without a channel the LAN channel is looked up
    ipmi = create_ipmi({'GetChannelInfo': LAN_CHANNEL_INFO_RSP,
                        'SetLanConfigurationParameters': b'\x00'})
    run_command(ipmi, 'lan set ipsrc dhcp')
    assert ipmi.requests == [
        ('GetChannelInfoReq', b'\x01'),
        ('SetLanConfigurationParametersReq', b'\x01\x04\x02')]


class TestPrivLevel:
    @pytest.mark.parametrize('level', ['user', 'OPERATOR', 'Administrator'])
    def test_priv_level(self, level):
        args = build_parser().parse_args(['-L', level, 'bmc', 'info'])
        assert args.priv_level == level.lower()

    @pytest.mark.parametrize('level', ['oem', 'admin', 'callback'])
    def test_priv_level_invalid(self, capsys, level):
        # a usage error instead of a traceback
        with pytest.raises(SystemExit) as e:
            build_parser().parse_args(['-L', level, 'bmc', 'info'])
        assert e.value.code == 2
        assert 'invalid choice' in capsys.readouterr().err


class TestSdrList:
    @staticmethod
    def full_record():
        record = SdrFullSensorRecord()
        record.id = 1
        record.type = 0x01
        record.number = 0
        record.owner_lun = 1
        record.device_id_string = 'Temp'
        record.analog_data_format = record.DATA_FMT_UNSIGNED
        record.m = 1
        record.b = 0
        record.k1 = 0
        record.k2 = 0
        record.linearization = 0
        return record

    @staticmethod
    def compact_record():
        record = SdrCompactSensorRecord()
        record.id = 2
        record.type = 0x02
        record.number = 0
        record.owner_lun = 1
        record.device_id_string = 'State'
        return record

    def test_sdr_list(self, capsys):
        ipmi = MagicMock()
        ipmi.get_device_id.return_value.supports_function.return_value = True
        ipmi.sdr_entries.return_value = [self.full_record(),
                                                    self.compact_record()]
        # the states 0 are valid, as the sensor number 0
        ipmi.get_sensor_reading.return_value = (25, 0)

        cli.cmd_sdr_list(ipmi, argparse.Namespace(details=False))

        # the sensors are read with the LUN of their owner
        assert ipmi.get_sensor_reading.call_args_list == [
            ((0, 1),), ((0, 1),)]
        lines = capsys.readouterr().out.splitlines()
        assert lines[2] == ('0x0001 |   0 | Temp               |    25.000 '
                            '| 0x0')
        assert lines[3] == ('0x0002 |   0 | State              |        25 '
                            '| 0x0')

    def test_sdr_list_details(self, capsys):
        ipmi = MagicMock()
        ipmi.get_device_id.return_value.supports_function.return_value = True
        ipmi.sdr_entries.return_value = [
            SdrCommon.from_data(TestSdrShow.FULL_RECORD),
            SdrCommon.from_data(TestSdrShow.COMPACT_RECORD)]
        cli.cmd_sdr_list(ipmi, argparse.Namespace(details=True))

        # only the values of the records are printed
        ipmi.get_sensor_reading.assert_not_called()
        out = capsys.readouterr().out
        assert 'SDR-ID' not in out
        assert ('Record ID:              0x0001\n'
                'Record Type:            [0x01] Full Sensor Record\n'
                'Name:                   CPU Temp\n') in out
        assert ('\n\nRecord ID:              0x00d3\n'
                'Record Type:            [0x02] Compact Sensor Record\n'
                'Name:                   A4:Pres SFP-1\n') in out

    def test_sdr_list_options(self):
        parser = build_parser()
        assert not parser.parse_args(['sdr', 'list']).details
        assert parser.parse_args(['sdr', 'list', '-d']).details
        assert parser.parse_args(['sdr', 'list', '--details']).details

    def test_print_sdr_list_entry_not_available(self, capsys):
        cli.print_sdr_list_entry(3, None, 'Other', None, None)
        assert capsys.readouterr().out == (
            '0x0003 |  na | Other              |      None | na\n')


class TestSelList:

    ENTRIES = [
        # threshold event of the temperature sensor 4 of the BMC
        bytes([0x01, 0x00, 0x02, 0x00, 0x10, 0x20, 0x68, 0x20, 0x00,
               0x04, 0x01, 0x04, 0x01, 0x59, 0x55, 0x50]),
        # sensor-specific deassertion of the FRU hot swap sensor 0
        bytes([0x02, 0x00, 0x02, 0x10, 0x00, 0x00, 0x00, 0x82, 0x00,
               0x04, 0xf0, 0x00, 0xef, 0x02, 0x01, 0xff]),
        # OEM non-timestamped record
        bytes([0x03, 0x00, 0xe0] + list(range(1, 14))),
    ]

    def ipmi(self):
        ipmi = MagicMock()
        ipmi.sel_entries.return_value = [SelEntry(e) for e in self.ENTRIES]
        ipmi.get_device_id.return_value.supports_function.return_value = True
        record = SdrFullSensorRecord()
        record.id = 1
        record.owner_id = 0x20
        record.owner_lun = 0
        record.number = 4
        record.device_id_string = 'CPU Temp'
        record.analog_data_format = 0
        record.m = 1
        record.b = 0
        record.k1 = 0
        record.k2 = 0
        record.linearization = 0
        ipmi.sdr_entries.return_value = [record]
        return ipmi

    def test_options(self):
        parser = build_parser()
        args = parser.parse_args(['sel', 'list'])
        assert not args.details and not args.sdr
        args = parser.parse_args(['sel', 'list', '-d', '--sdr'])
        assert args.details and args.sdr
        # the global option for the log level is independent
        assert not args.verbose
        args = parser.parse_args(['-v', 'sel', 'list'])
        assert args.verbose and not args.details

    def test_list(self, capsys):
        ipmi = self.ipmi()
        cli.cmd_sel_list(ipmi, argparse.Namespace(details=False,
                                                       sdr=False))
        ipmi.sdr_repository_entries.assert_not_called()
        assert capsys.readouterr().out.splitlines() == [
            '0x0001 | 2025-05-11 02:48:32 | Temperature #0x04 '
            '| Upper Critical going high | Asserted '
            '| Reading 0x55, Threshold 0x50',
            '0x0002 | Pre-Init 16s        | FRU Hot Swap #0x00 '
            '| M2 - FRU Activation Request | Deasserted',
            '0x0003 | Unspecified         | OEM non-timestamped (0xe0) '
            '| 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d',
        ]

    def test_list_sdr(self, capsys):
        cli.cmd_sel_list(self.ipmi(), argparse.Namespace(details=False,
                                                              sdr=True))
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == ('0x0001 | 2025-05-11 02:48:32 '
                            '| Temperature CPU Temp '
                            '| Upper Critical going high | Asserted '
                            '| Reading [0x55] 85.000, '
                            'Threshold [0x50] 80.000')
        # the sensor of another owner has no record
        assert 'FRU Hot Swap #0x00' in lines[1]

    def test_list_details(self, capsys):
        cli.cmd_sel_list(self.ipmi(), argparse.Namespace(details=True,
                                                              sdr=True))
        out = capsys.readouterr().out
        assert ('SEL Record ID:   0x0001\n'
                'Record Type:     [0x02] System Event\n'
                'Timestamp:       [0x68201000] 2025-05-11 02:48:32\n'
                'Generator ID:    [0x0020] IPMB 0x20 LUN 0\n'
                'EvM Revision:    0x04\n'
                'Sensor Type:     [0x01] Temperature\n'
                'Sensor Number:   0x04\n'
                'Sensor Name:     CPU Temp\n'
                'Event Type:      [0x01] Threshold\n'
                'Event Direction: [0x0] Asserted\n'
                'Event Data:      59 55 50\n'
                'Description:     [0x09] Upper Critical going high\n'
                'Values:          Reading [0x55] 85.000, '
                'Threshold [0x50] 80.000\n'
                'Raw Data:        01 00 02 00 10 20 68 20 00 04 01 04 01 59 '
                '55 50\n') in out
        assert ('SEL Record ID:   0x0003\n'
                'Record Type:     [0xe0] OEM non-timestamped\n'
                'Timestamp:       Unspecified\n'
                'Raw Data:        03 00 e0 01 02') in out


class TestSelCommands:
    @staticmethod
    def run(command, rsp_data):
        ipmi = create_ipmi(rsp_data)
        args = build_parser().parse_args(['sel'] + command.split())
        args.func(ipmi, args)
        return ipmi

    # version 1.5, 3 entries, 0x0400 free bytes, the last addition, never
    # erased, all operations supported and the overflow flag
    SEL_INFO_RSP = (b'\x00\x51\x03\x00\x00\x04\x00\x10\x20\x68'
                    b'\xff\xff\xff\xff\x8f')
    ALLOC_INFO_RSP = b'\x00\x00\x02\x10\x00\x80\x01\x40\x00\x01'

    def test_info(self, capsys):
        ipmi = self.run('info', {'GetSelInfo': self.SEL_INFO_RSP,
                                 'GetSelAllocationInfo': self.ALLOC_INFO_RSP})
        assert [name for name, _ in ipmi.requests] == [
            'GetSelInfoReq', 'GetSelAllocationInfoReq']
        assert capsys.readouterr().out == (
            'Version:                 1.5\n'
            'Entries:                 3\n'
            'Free Space:              1024 bytes\n'
            'Last Add Time:           2025-05-11 02:48:32\n'
            'Last Erase Time:         Unspecified\n'
            'Overflow:                True\n'
            'Supported Commands:      get_sel_allocation_info, reserve_sel, '
            'partial_add_sel_entry, delete_sel\n'
            'Allocation Units:        512\n'
            'Allocation Unit Size:    16 bytes\n'
            'Free Allocation Units:   384\n'
            'Largest Free Block:      64 units\n'
            'Maximum Record Size:     1 units\n')

    def test_info_without_allocation_info(self, capsys):
        # only Reserve SEL supported
        ipmi = self.run('info', self.SEL_INFO_RSP[:-1] + b'\x02')
        assert [name for name, _ in ipmi.requests] == ['GetSelInfoReq']
        out = capsys.readouterr().out
        assert 'Supported Commands:      reserve_sel\n' in out
        assert 'Allocation' not in out

    def test_time_get(self, capsys):
        ipmi = self.run('time get', b'\x00\x00\x10\x20\x68')
        assert ipmi.requests == [('GetSelTimeReq', b'')]
        assert capsys.readouterr().out == '2025-05-11 02:48:32\n'

    def test_time_set(self, capsys):
        ipmi = create_ipmi({'SetSelTime': b'\x00',
                            'GetSelTime': b'\x00\x00\x10\x20\x68'})
        args = build_parser().parse_args(['sel', 'time', 'set',
                                          '2025-05-11 02:48:32'])
        args.func(ipmi, args)
        assert ipmi.requests[0] == ('SetSelTimeReq', b'\x00\x10\x20\x68')
        assert capsys.readouterr().out == '2025-05-11 02:48:32\n'

    def test_time_set_now(self, monkeypatch):
        monkeypatch.setattr(cli.time, 'time', lambda: 0x68201000 + 0.5)
        args = build_parser().parse_args(['sel', 'time', 'set', 'now'])
        assert args.time == 0x68201000

    def test_time_set_invalid(self, capsys):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['sel', 'time', 'set', '11.05.2025'])
        assert 'invalid time' in capsys.readouterr().err

    @pytest.mark.parametrize('rsp, output', [
        (b'\x00\x3c\x00', '+60 minutes'),
        (b'\x00\xc4\xff', '-60 minutes'),
        (b'\x00\xff\x07', 'unspecified'),
    ])
    def test_utc_offset_get(self, capsys, rsp, output):
        ipmi = self.run('utc-offset', rsp)
        assert ipmi.requests == [('GetSelTimeUtcOffsetReq', b'')]
        assert capsys.readouterr().out == f'UTC offset: {output}\n'

    @pytest.mark.parametrize('offset, data', [
        ('60', b'\x3c\x00'),
        ('-60', b'\xc4\xff'),
        ('unspecified', b'\xff\x07'),
    ])
    def test_utc_offset_set(self, offset, data):
        ipmi = create_ipmi({'SetSelTimeUtcOffset': b'\x00',
                            'GetSelTimeUtcOffset': b'\x00' + data})
        args = build_parser().parse_args(['sel', 'utc-offset', offset])
        args.func(ipmi, args)
        assert ipmi.requests[0] == ('SetSelTimeUtcOffsetReq', data)

    @pytest.mark.parametrize('offset', ['1441', '-1441', 'local'])
    def test_utc_offset_invalid(self, capsys, offset):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['sel', 'utc-offset', offset])
        assert 'invalid UTC offset' in capsys.readouterr().err

    def test_get(self, capsys):
        entry = TestSelList.ENTRIES[0]
        ipmi = self.run('get 1', {'ReserveSel': b'\x00\x34\x12',
                                  'GetSelEntry': b'\x00\xff\xff' + entry})
        assert ipmi.requests == [
            ('ReserveSelReq', b''),
            ('GetSelEntryReq', b'\x34\x12\x01\x00\x00\xff')]
        out = capsys.readouterr().out
        assert out.startswith('SEL Record ID:   0x0001\n')
        assert 'Description:     [0x09] Upper Critical going high\n' in out

    RECORD = ' '.join(f'0x{b:02x}' for b in TestSelList.ENTRIES[0])

    def test_add(self, capsys):
        ipmi = self.run(f'add {self.RECORD}', b'\x00\x07\x00')
        assert ipmi.requests == [('AddSelEntryReq', TestSelList.ENTRIES[0])]
        assert capsys.readouterr().out == 'Added SEL entry 0x0007\n'

    def test_add_partial(self, capsys):
        ipmi = self.run(f'add -p {self.RECORD}',
                        {'ReserveSel': b'\x00\x34\x12',
                         'PartialAddSelEntry': [b'\x00\x07\x00'] * 2})
        assert [name for name, _ in ipmi.requests] == [
            'ReserveSelReq', 'PartialAddSelEntryReq', 'PartialAddSelEntryReq']
        assert capsys.readouterr().out == 'Added SEL entry 0x0007\n'

    @pytest.mark.parametrize('data', ['0 ' * 15, '0 ' * 15 + '256'])
    def test_add_invalid(self, data):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['sel', 'add'] + data.split())

    def test_delete(self, capsys):
        ipmi = self.run('delete 1 0x0a',
                        {'ReserveSel': b'\x00\x34\x12',
                         'DeleteSelEntry': [b'\x00\x01\x00',
                                            b'\x00\x0a\x00']})
        assert ipmi.requests == [
            ('ReserveSelReq', b''),
            ('DeleteSelEntryReq', b'\x34\x12\x01\x00'),
            ('DeleteSelEntryReq', b'\x34\x12\x0a\x00')]
        assert capsys.readouterr().out == ('Deleted SEL entry 0x0001\n'
                                           'Deleted SEL entry 0x000a\n')

    @pytest.mark.parametrize('log, data, rsp, output', [
        ('mca', b'\x00', b'\x00\x11\x22\x33', '11 22 33\n'),
        ('oem2', b'\x02', b'\x00', 'no status data\n'),
    ])
    def test_aux_status(self, capsys, log, data, rsp, output):
        ipmi = self.run(f'aux-status {log}', rsp)
        assert ipmi.requests == [('GetAuxiliaryLogStatusReq', data)]
        assert capsys.readouterr().out == output


class TestSdrCommands:
    @staticmethod
    def run(command, rsp_data):
        ipmi = create_ipmi(rsp_data)
        args = build_parser().parse_args(['sdr'] + command.split())
        args.func(ipmi, args)
        return ipmi

    # version 1.5, 29 records, 0x0400 free bytes, the last addition, never
    # erased, modal updates, all operations supported
    REPOSITORY_INFO_RSP = (b'\x00\x51\x1d\x00\x00\x04\x00\x10\x20\x68'
                           b'\xff\xff\xff\xff\x4f')
    ALLOC_INFO_RSP = b'\x00\x00\x02\x10\x00\x80\x01\x40\x00\x04'

    def test_info(self, capsys):
        ipmi = self.run('info', {
            'GetSdrRepositoryInfo': self.REPOSITORY_INFO_RSP,
            'GetSdrRepositoryAllocationInfo': self.ALLOC_INFO_RSP})
        assert [name for name, _ in ipmi.requests] == [
            'GetSdrRepositoryInfoReq', 'GetSdrRepositoryAllocationInfoReq']
        assert capsys.readouterr().out == (
            'Version:                 1.5\n'
            'Records:                 29\n'
            'Free Space:              1024 bytes\n'
            'Last Add Time:           2025-05-11 02:48:32\n'
            'Last Erase Time:         Unspecified\n'
            'Overflow:                False\n'
            'Update Type:             modal\n'
            'Supported Commands:      get_allocation_info, reserve, '
            'partial_add, delete\n'
            'Allocation Units:        512\n'
            'Allocation Unit Size:    16 bytes\n'
            'Free Allocation Units:   384\n'
            'Largest Free Block:      64 units\n'
            'Maximum Record Size:     4 units\n')

    def test_info_without_allocation_info(self, capsys):
        # unspecified free space, non-modal updates, only Reserve supported
        rsp = (self.REPOSITORY_INFO_RSP[:4] + b'\xff\xff'
               + self.REPOSITORY_INFO_RSP[6:-1] + b'\x22')
        ipmi = self.run('info', rsp)
        assert [name for name, _ in ipmi.requests] == [
            'GetSdrRepositoryInfoReq']
        out = capsys.readouterr().out
        assert 'Free Space:              unspecified\n' in out
        assert 'Update Type:             non-modal\n' in out
        assert 'Supported Commands:      reserve\n' in out
        assert 'Allocation' not in out

    @pytest.mark.parametrize('command, data, label', [
        ('device-info', b'', 'Sensors:'),
        ('device-info -c', b'\x01', 'SDRs:'),
    ])
    def test_device_info(self, capsys, command, data, label):
        ipmi = self.run(command, b'\x00\x03\x85\x00\x10\x20\x68')
        assert ipmi.requests == [('GetDeviceSdrInfoReq', data)]
        assert capsys.readouterr().out == (
            f'{label:<25}3\n'
            'LUNs with Sensors:       0, 2\n'
            'Dynamic Population:      True\n'
            'Population Change:       2025-05-11 02:48:32\n')

    def test_device_info_static(self, capsys):
        self.run('device-info', b'\x00\x00\x00')
        out = capsys.readouterr().out
        assert 'LUNs with Sensors:       none\n' in out
        assert out.endswith('Population Change:       na\n')

    def test_time_get(self, capsys):
        ipmi = self.run('time get', b'\x00\x00\x10\x20\x68')
        assert ipmi.requests == [('GetSdrRepositoryTimeReq', b'')]
        assert capsys.readouterr().out == '2025-05-11 02:48:32\n'

    def test_time_set(self, capsys):
        ipmi = create_ipmi({'SetSdrRepositoryTime': b'\x00',
                            'GetSdrRepositoryTime':
                                b'\x00\x00\x10\x20\x68'})
        args = build_parser().parse_args(['sdr', 'time', 'set',
                                          '2025-05-11 02:48:32'])
        args.func(ipmi, args)
        assert ipmi.requests[0] == ('SetSdrRepositoryTimeReq',
                                    b'\x00\x10\x20\x68')
        assert capsys.readouterr().out == '2025-05-11 02:48:32\n'

    RECORD = '0 0 0x51 0x08 0x05 0x07 0x01 0x00 0x0a 0x01'
    RECORD_DATA = bytes([0, 0, 0x51, 0x08, 0x05, 0x07, 0x01, 0x00, 0x0a,
                         0x01])

    def test_add(self, capsys):
        ipmi = self.run(f'add {self.RECORD}', b'\x00\x2a\x00')
        assert ipmi.requests == [('AddSdrReq', self.RECORD_DATA)]
        assert capsys.readouterr().out == 'Added SDR 0x002a\n'

    def test_add_in_parts(self, capsys):
        ipmi = self.run(f'add -p 4 {self.RECORD}',
                        {'ReserveSdrRepository': b'\x00\x34\x12',
                         'PartialAddSdr': [b'\x00\x2a\x00'] * 3})
        assert [name for name, _ in ipmi.requests] == [
            'ReserveSdrRepositoryReq'] + ['PartialAddSdrReq'] * 3
        assert capsys.readouterr().out == 'Added SDR 0x002a\n'

    def test_add_invalid_byte(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['sdr', 'add', '0', '256'])

    def test_delete(self, capsys):
        ipmi = self.run('delete 1 0x0a',
                        {'ReserveSdrRepository': [b'\x00\x34\x12',
                                                  b'\x00\x35\x12'],
                         'DeleteSdr': [b'\x00\x01\x00',
                                       b'\x00\x0a\x00']})
        assert ipmi.requests == [
            ('ReserveSdrRepositoryReq', b''),
            ('DeleteSdrReq', b'\x34\x12\x01\x00'),
            ('ReserveSdrRepositoryReq', b''),
            ('DeleteSdrReq', b'\x35\x12\x0a\x00')]
        assert capsys.readouterr().out == ('Deleted SDR 0x0001\n'
                                           'Deleted SDR 0x000a\n')

    @pytest.mark.parametrize('mode, name', [
        ('enter', 'EnterSdrRepositoryUpdateModeReq'),
        ('exit', 'ExitSdrRepositoryUpdateModeReq'),
    ])
    def test_update_mode(self, mode, name):
        ipmi = self.run(f'update-mode {mode}', b'\x00')
        assert ipmi.requests == [(name, b'')]


class TestSensorCommands:
    @staticmethod
    def run(command, rsp_data):
        ipmi = create_ipmi(rsp_data)
        args = build_parser().parse_args(['sensor'] + command.split())
        args.func(ipmi, args)
        return ipmi

    TYPE_OUTPUT = ('Sensor Type:             [0x01] Temperature\n'
                   'Event/Reading Type:      [0x01] Threshold\n')

    def test_type(self, capsys):
        ipmi = self.run('type 0x10 -l 1', b'\x00\x01\x01')
        assert ipmi.requests == [('GetSensorTypeReq', b'\x10')]
        assert capsys.readouterr().out == self.TYPE_OUTPUT

    def test_type_set(self, capsys):
        ipmi = self.run('type 0x10 --set 0x01 0x01',
                        {'SetSensorType': b'\x00',
                         'GetSensorType': b'\x00\x01\x01'})
        assert ipmi.requests == [('SetSensorTypeReq', b'\x10\x01\x01'),
                                 ('GetSensorTypeReq', b'\x10')]
        assert capsys.readouterr().out == self.TYPE_OUTPUT

    def test_hysteresis(self, capsys):
        ipmi = self.run('hysteresis 0x10', b'\x00\x02\x03')
        assert ipmi.requests == [('GetSensorHysteresisReq', b'\x10\xff')]
        assert capsys.readouterr().out == (
            'Positive Hysteresis:     [0x02] 2\n'
            'Negative Hysteresis:     [0x03] 3\n')

    def test_hysteresis_set(self):
        ipmi = self.run('hysteresis 0x10 -s 4 5',
                        {'SetSensorHysteresis': b'\x00',
                         'GetSensorHysteresis': b'\x00\x04\x05'})
        assert ipmi.requests[0] == ('SetSensorHysteresisReq',
                                    b'\x10\xff\x04\x05')

    # temperature threshold sensor, upper critical going high (bit 9)
    # enabled, upper non-critical going high (bit 7) asserted
    EVENTS_RSP = {'GetSensorType': b'\x00\x01\x01',
                  'GetSensorEventEnable': b'\x00\xc0\x00\x02\x00\x02',
                  'GetSensorEventStatus': b'\x00\xc0\x80\x00'}

    def test_events(self, capsys):
        self.run('events 0x10', self.EVENTS_RSP)
        assert capsys.readouterr().out == self.TYPE_OUTPUT + (
            'Event Messages:          enabled\n'
            'Sensor Scanning:         enabled\n'
            'Reading Unavailable:     False\n'
            'Enabled Assertions:      [0x0200]\n'
            '                         Upper Critical going high\n'
            'Enabled Deassertions:    [0x0200]\n'
            '                         Upper Critical going high\n'
            'Asserted Events:         [0x0080]\n'
            '                         Upper Non-critical going high\n'
            'Deasserted Events:       na\n')

    @pytest.mark.parametrize('options, data', [
        # the other setting is kept
        ('-m off', b'\x10\x40'),
        ('-s off', b'\x10\x80'),
        ('-m off -s off', b'\x10\x00'),
        ('-m on', b'\x10\xc0'),
    ])
    def test_events_set(self, options, data):
        ipmi = self.run(f'events 0x10 {options}',
                        dict(self.EVENTS_RSP, SetSensorEventEnable=b'\x00'))
        assert ipmi.requests[1] == ('SetSensorEventEnableReq', data)

    def test_factors(self, capsys):
        ipmi = self.run('factors 0x10 0x80',
                        b'\x00\x90\xfe\xc5\x64\x05\x18\xd2')
        assert ipmi.requests == [('GetSensorReadingFactorsReq',
                                  b'\x10\x80')]
        assert capsys.readouterr().out == (
            'M:                       -2\n'
            'B:                       100\n'
            'K1 (B Exponent):         2\n'
            'K2 (Result Exponent):    -3\n'
            'Tolerance:               5\n'
            'Accuracy:                69\n'
            'Accuracy Exponent:       2\n'
            'Next Reading:            [0x90] 144\n')

    def test_set_reading(self):
        ipmi = self.run('set-reading 0x10 0x42', b'\x00')
        assert ipmi.requests == [('SetSensorReadingAndEventStatusReq',
                                  b'\x10\x01\x42')]

    @pytest.mark.parametrize('command', [
        'type 0x10 --set 0x01',
        'hysteresis 0x10 -s 256 1',
        'events 0x10 -m yes',
        'factors 0x10',
    ])
    def test_invalid(self, command):
        with pytest.raises(SystemExit):
            build_parser().parse_args(['sensor'] + command.split())


class TestSensorFindRead:
    FULL = SdrCommon.from_data(TestSdrShow.FULL_RECORD)
    COMPACT = SdrCommon.from_data(TestSdrShow.COMPACT_RECORD)

    @staticmethod
    def args(command):
        return build_parser().parse_args(['sensor'] + command.split())

    @pytest.mark.parametrize('command, name, sensor_type', [
        ('find', None, None),
        ('read', None, None),
        ('find cpu*', 'cpu*', None),
        ('read cpu* -t temperature', 'cpu*', 0x01),
        ('read --type power-supply', None, 0x08),
        ('find -t 0x02', None, 0x02),
    ])
    def test_options(self, command, name, sensor_type):
        args = self.args(command)
        assert args.name == name
        assert args.type == sensor_type

    def test_invalid_type(self, capsys):
        with pytest.raises(SystemExit):
            self.args('find -t humidity')
        assert 'unknown sensor type: humidity' in capsys.readouterr().err

    def test_find(self, capsys):
        ipmi = MagicMock()
        ipmi.find_sensors.return_value = [self.FULL, self.COMPACT]
        cli.cmd_sensor_find(ipmi, self.args('find cpu* -t temperature'))
        ipmi.find_sensors.assert_called_once_with(name='cpu*',
                                                  sensor_type=0x01)
        assert capsys.readouterr().out.splitlines() == [
            'SDR-ID | Num | Name               | Sensor Type',
            '=======|=====|====================|====================',
            '0x0001 |   4 | CPU Temp           | [0x01] Temperature',
            '0x00d3 | 211 | A4:Pres SFP-1      | [0x21] Slot / Connector']

    def test_find_json(self, capsys):
        ipmi = MagicMock()
        ipmi.find_sensors.return_value = [self.FULL]
        args = build_parser().parse_args(['-J', 'sensor', 'find'])
        cli.cmd_sensor_find(ipmi, args)
        assert json.loads(capsys.readouterr().out) == [
            {'record_id': 1, 'number': 4, 'name': 'CPU Temp',
             'sensor_type': 1, 'sensor_type_name': 'Temperature'}]

    def test_find_not_supported(self, capsys):
        ipmi = MagicMock()
        ipmi.find_sensors.side_effect = NotSupportedError()
        cli.cmd_sensor_find(ipmi, self.args('find'))
        out = capsys.readouterr()
        assert out.out == ''
        assert 'neither SDR repository nor sensor' in out.err

    def readings(self):
        return [
            SensorReading(self.FULL, 45, 45.0, 'degrees C', 0x00),
            SensorReading(self.FULL, 90, 90.0, 'degrees C', 0x18),
            SensorReading(self.FULL, None, None, 'degrees C', None),
            SensorReading(self.COMPACT, 0, None, '', 0x04),
            SensorReading(self.COMPACT, 0, None, '', 0x00),
            CompletionCodeError(0xcb),
        ]

    def test_read(self, capsys):
        ipmi = MagicMock()
        ipmi.find_sensors.return_value = [self.FULL] * 3 + [self.COMPACT] * 3
        ipmi.read_sensor.side_effect = self.readings()
        cli.cmd_sensor_read(ipmi, self.args('read'))
        assert ipmi.read_sensor.call_args_list[0] == ((self.FULL,),)
        assert capsys.readouterr().out.splitlines() == [
            'Name               | Value                    | States',
            '===================|==========================|'
            '====================',
            'CPU Temp           | 45.000 degrees C         | ok',
            'CPU Temp           | 90.000 degrees C         | '
            'Upper Non-critical, Upper Critical',
            'CPU Temp           | na                       | na',
            'A4:Pres SFP-1      | -                        | '
            'Slot / Connector Device Installed/Attached',
            'A4:Pres SFP-1      | -                        | -',
            'A4:Pres SFP-1      | ERR: CC=0xcb (Requested data not present)']

    def test_read_json(self, capsys):
        ipmi = MagicMock()
        ipmi.find_sensors.return_value = [self.FULL, self.COMPACT,
                                          self.COMPACT]
        readings = self.readings()
        ipmi.read_sensor.side_effect = [readings[1], readings[3],
                                        readings[5]]
        args = build_parser().parse_args(['-J', 'sensor', 'read'])
        cli.cmd_sensor_read(ipmi, args)
        assert json.loads(capsys.readouterr().out) == [
            {'name': 'CPU Temp', 'number': 4, 'raw': 90, 'value': 90.0,
             'unit': 'degrees C', 'states': 0x18,
             'state_names': ['Upper Non-critical', 'Upper Critical']},
            {'name': 'A4:Pres SFP-1', 'number': 211, 'raw': 0,
             'value': None, 'unit': '', 'states': 0x04,
             'state_names': ['Slot / Connector Device Installed/Attached']},
            {'name': 'A4:Pres SFP-1', 'number': 211,
             'completion_code': 0xcb}]


class TestCompletionCodeOutput:
    @pytest.mark.parametrize('error, output', [
        (CompletionCodeError(0xc1), '0xc1 (Invalid Command)'),
        # a command-specific code with its description
        (CompletionCodeError(0x81, cmdid=0x47, netfn=0x06),
         '0x81 (password test failed. Wrong password size was used.)'),
        # codes without description are described by their range
        (CompletionCodeError(0x42), '0x42 (device specific (OEM) completion '
                                    'code)'),
        (CompletionCodeError(0x85), '0x85 (command-specific completion '
                                    'code)'),
        (CompletionCodeError(0xe0), '0xe0 (unknown completion code)'),
    ])
    def test_format_completion_code(self, error, output):
        assert cli.format_completion_code(error) == output

    def test_main_prints_the_description(self, capsys, monkeypatch):
        ipmi = MagicMock()
        ipmi.get_device_id.side_effect = CompletionCodeError(0xd4)
        monkeypatch.setattr(cli, 'create_ipmi_connection',
                            lambda *args: ipmi)
        with pytest.raises(SystemExit) as e:
            cli.main(['-I', 'ipmitool', '-H', '10.0.0.1', 'bmc',
                           'info'])
        assert e.value.code == 1
        assert capsys.readouterr().out == (
            'Command failed due to "Cannot execute command due to '
            'insufficient privilege level" (CC=0xd4)\n')

    @pytest.mark.parametrize('error, output', [
        (CompletionCodeError(0xc1), 'Command'),
        (CompletionCodeError(0xc1, cmdid=0x01, netfn=0x06),
         'Command "GetDeviceId" (netfn=0x06, cmd=0x01)'),
        (CompletionCodeError(0xc1, cmdid=0x00, netfn=0x2c,
                             group_extension=0x00),
         'Command "GetPicmgProperties" (netfn=0x2c, cmd=0x00, '
         'group=0x00)'),
        # a command without message class
        (CompletionCodeError(0xc1, cmdid=0xff, netfn=0x30),
         'Command (netfn=0x30, cmd=0xff)'),
    ])
    def test_format_failed_command(self, error, output):
        assert cli.format_failed_command(error) == output

    def test_main_prints_the_failed_command(self, capsys, monkeypatch):
        # the error raised by the library carries the failed command
        ipmi = create_ipmi({'GetDeviceId': b'\xc1'})
        monkeypatch.setattr(cli, 'create_ipmi_connection',
                            lambda *args: ipmi)
        with pytest.raises(SystemExit):
            cli.main(['-I', 'ipmitool', '-H', '10.0.0.1', 'bmc',
                           'info'])
        assert capsys.readouterr().out == (
            'Command "GetDeviceId" (netfn=0x06, cmd=0x01) failed due to '
            '"Invalid Command" (CC=0xc1)\n')
