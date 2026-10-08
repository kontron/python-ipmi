#!/usr/bin/env python

import argparse
import logging
import os

import pytest

from unittest.mock import MagicMock

from pyipmi import ipmitool
from pyipmi.errors import CompletionCodeError
from pyipmi.msgs import create_response_by_name, decode_message
from pyipmi.ipmitool import build_parser, log_level, parse_interface_options
from pyipmi.sdr import SdrCommon

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
        names = ipmitool.logger_names()
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
            ipmitool.setup_logging(False, [
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
        assert args.func is ipmitool.cmd_bmc_info
        assert args.needs_connection

    @pytest.mark.parametrize('command, func', [
        ('bmc info', 'cmd_bmc_info'),
        ('bmc reset cold', 'cmd_bmc_reset'),
        ('chassis status', 'cmd_chassis_status'),
        ('chassis power cycle', 'cmd_chassis_power'),
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
        ipmitool.main(['fru', 'print-file', path] + extra)
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
        ipmitool.main(['fru', 'print-file', path] + extra)
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
            ipmitool.main(['fru', 'print-file', str(path)])
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
        ipmitool.main(['hpm', 'check', path])
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
        ipmitool.cmd_chassis_power(ipmi, args)
        assert ipmi.requests == [('ChassisControlReq', bytes([control]))]


class TestCreateIpmiConnection:
    @staticmethod
    def routing(ipmi):
        return [(r.rq_sa, r.rs_sa, r.channel) for r in ipmi.target.routing]

    def test_channel_rmcp(self):
        # like ipmitool -t 0x82 -b 0: bridged by the BMC on channel 0
        ipmi = ipmitool.create_ipmi_connection('rmcp', None, 0x82, None,
                                               '10.0.0.1', 623, 'admin',
                                               'admin', None, 0)
        assert ipmi.target.ipmb_address == 0x82
        assert self.routing(ipmi) == [(0x81, 0x20, 0), (0x20, 0x82, None)]

    def test_channel_ipmitool(self):
        ipmi = ipmitool.create_ipmi_connection('ipmitool', None, 0x72, None,
                                               '10.0.0.1', 623, 'admin',
                                               'admin', None, 7)
        ipmi.interface.establish_session(ipmi.session)
        assert ipmi.interface._build_ipmitool_target(ipmi.target) \
            == ' -t 0x72 -b 7'

    def test_channel_uses_own_address(self, monkeypatch):
        # the requester of the first hop is the own address of the interface
        interface = MagicMock(slave_address=0x24)
        monkeypatch.setattr(ipmitool.pyipmi.interfaces, 'create_interface',
                            lambda name, **kwargs: interface)
        ipmi = ipmitool.create_ipmi_connection('openipmblink', None, 0x72,
                                               None, None, 623, '', '', None,
                                               7)
        assert self.routing(ipmi) == [(0x24, 0x20, 7), (0x20, 0x72, None)]

    def test_routing(self):
        ipmi = ipmitool.create_ipmi_connection('rmcp', None, 0x72,
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
        assert 'Manufacturer Name: Unknown' in out
        assert 'Product ID:       0x8006' in out

    def test_mc_confirmation_record_manufacturer_name(self, capsys):
        # manufacturer ID 15000
        data = [0x45, 0x00, 0x51, 0x13, 0x1b, 0x20, 0x00, 0x01,
                0x02, 0x01, 0x51, 0x98, 0x3a, 0x00, 0x06, 0x80,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        record = SdrCommon.from_data(data)
        assert record.manufacturer_name == 'Kontron'
        ipmitool.sdr_show(None, record)

        out = capsys.readouterr().out
        assert 'Manufacturer ID:  0x03a98' in out
        assert 'Manufacturer Name: Kontron' in out

    @pytest.mark.parametrize('data', [
        # OEM record
        [0x05, 0x00, 0x51, 0xc0, 0x05, 0x57, 0x01, 0x00, 0xaa, 0xbb],
        # unknown record type
        [0x01, 0x00, 0x51, 0x0a, 0x00],
    ])
    def test_record_without_id_string(self, capsys, data):
        ipmitool.sdr_show(None, SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert f'SDR type:         0x{data[3]:02x}' in out
        assert 'Device Id string' not in out

    def test_fru_device_locator_record(self, capsys):
        data = [0x02, 0x00, 0x51, 0x11, 0x10, 0x20, 0x00, 0x00,
                0x00, 0x00, 0x10, 0x00, 0x0a, 0x01, 0x00, 0xc4,
                0x46, 0x52, 0x55, 0x31]
        ipmitool.sdr_show(None, SdrCommon.from_data(data))

        out = capsys.readouterr().out
        assert 'Device Id string: FRU1' in out
        assert 'Entity:           10.1' in out


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
        assert out[3].endswith('ERR: CC=0xcc')

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
            'baseboard  | ERR: CC=0xcb']

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
    ipmitool.cmd_bmc_info(ipmi, None)
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
