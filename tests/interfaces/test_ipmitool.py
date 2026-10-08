#!/usr/bin/env python

from unittest.mock import MagicMock

import pytest

from pyipmi.errors import IpmiTimeoutError, IpmiConnectionError, IpmiLongPasswordError, AuthenticationError
from pyipmi.interfaces import Ipmitool
from pyipmi import Session, Target
from pyipmi.utils import py3_array_tobytes


class TestIpmitool:

    def setup_method(self):
        self._interface = Ipmitool(interface_type='lan')
        self.session = Session()
        self.session.interface = self._interface
        self.session.set_session_type_rmcp('10.0.1.1')
        self.session.set_auth_type_user('admin', 'secret')
        self._interface.establish_session(self.session)

    def test_build_ipmitool_target_ipmb_address(self):
        target = Target(0xb0)
        cmd = self._interface._build_ipmitool_target(target)
        assert cmd == ' -t 0xb0'

    def test_build_ipmitool_target_routing_2(self):
        target = Target(routing=[(0x81, 0x20, 7), (0x20, 0x82, 0)])
        cmd = self._interface._build_ipmitool_target(target)
        assert cmd == ' -t 0x82 -b 7'

    def test_build_ipmitool_target_routing_3(self):
        target = Target(routing=[(0x81, 0x20, 0),
                                 (0x20, 0x82, 7),
                                 (0x20, 0x72, None)])
        cmd = self._interface._build_ipmitool_target(target)
        assert cmd == ' -T 0x82 -B 0 -t 0x72 -b 7'

    def test_build_ipmitool_target_routing_4(self):
        target = None
        cmd = self._interface._build_ipmitool_target(target)
        assert cmd == ''

    def test_build_ipmitool_target_routing_1(self):
        # a single hop is the BMC itself, no bridging
        target = Target(0x20, routing=[(0x81, 0x20, 0)])
        cmd = self._interface._build_ipmitool_target(target)
        assert cmd == ''

    def test_build_ipmitool_target_routing_3_missing_channel(self):
        # the second hop needs a channel for ipmitool (-b)
        target = Target(0xa8, routing=[(0x81, 0x20, 0),
                                       (0x20, 0x82, None),
                                       (0x20, 0xa8, None)])
        with pytest.raises(ValueError, match='routing entry 1'):
            self._interface._build_ipmitool_target(target)

    def test_build_ipmitool_target_routing_2_missing_channel(self):
        target = Target(routing=[(0x81, 0x20, None), (0x20, 0x82, 0)])
        with pytest.raises(ValueError, match='routing entry 0'):
            self._interface._build_ipmitool_target(target)

    def test_build_ipmitool_target_routing_too_long(self):
        target = Target(routing=[(0x81, 0x20, 0), (0x20, 0x82, 7),
                                 (0x20, 0x72, 0), (0x72, 0x74, None)])
        with pytest.raises(RuntimeError, match='at most double bridging'):
            self._interface._build_ipmitool_target(target)

    def test_send_and_receive(self):
        pass

    def test_rmcp_ping(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface.rmcp_ping()
        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -U admin -P secret '
                                     'session info all')

    def test_send_and_receive_raw_valid(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_lanplus(self):
        interface = Ipmitool(interface_type='lanplus')
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lanplus -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_cipher_0(self):
        interface = Ipmitool(interface_type='lanplus', cipher=0)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lanplus -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -C 0 '
                                     '-U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_cipher(self):
        interface = Ipmitool(cipher='7')
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -C 7 '
                                     '-U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_no_auth(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface._session.auth_type = Session.AUTH_TYPE_NONE

        target = Target(0x20)
        self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -P "" '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    @pytest.mark.parametrize('username, password', [
        ('ad$_min', 'pass$_word'),
        ('admin', 'pa$$word'),
        ('admin', 'pa"ss word'),
        ('admin', 'pa`id`ss'),
        ('admin', "pa'ss"),
        ('admin', 'pa\\$HOME'),
        ('admin', 'pass\\'),
    ])
    def test_credentials_with_shell_special_chars(self, username, password):
        self.session.set_auth_type_user(username, password)
        # replace ipmitool with printf to get every argument on its own line
        # after the command line was processed by the shell
        self._interface.IPMITOOL_PATH = 'printf "%s\\n"'

        cmd = self._interface._build_ipmitool_cmd(Target(0x20), 0, 0x6,
                                                  b'\x01')
        output, _ = self._interface._run_ipmitool(cmd)
        args = output.decode().splitlines()

        assert args[args.index('-U') + 1] == username
        assert args[args.index('-P') + 1] == password

    @pytest.mark.parametrize('host', [
        '10.0.1.1; echo injected',
        '10.0.1.1 && echo injected',
        '$(echo injected)',
        '`echo injected`',
        'host name',
    ])
    def test_host_with_shell_special_chars(self, host):
        self.session.set_session_type_rmcp(host)
        # replace ipmitool with printf to get every argument on its own line
        # after the command line was processed by the shell
        self._interface.IPMITOOL_PATH = 'printf "%s\\n"'

        cmd = self._interface._build_ipmitool_cmd(Target(0x20), 0, 0x6,
                                                  b'\x01')
        output, _ = self._interface._run_ipmitool(cmd)
        args = output.decode().splitlines()

        assert 'injected' not in args
        assert args[args.index('-H') + 1] == host
        assert args[args.index('-p') + 1] == '623'

    def test_rmcp_ping_host_with_shell_special_chars(self):
        self.session.set_session_type_rmcp('10.0.1.1; echo injected')
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface.rmcp_ping()

        cmd = mock.call_args[0][0]
        assert " -H '10.0.1.1; echo injected' -p 623 " in cmd

    def test_serial_port_with_shell_special_chars(self):
        interface = Ipmitool(interface_type='serial-terminal')
        self.session.set_session_type_serial('/dev/tty2; echo injected',
                                             115200)
        interface.establish_session(self.session)
        interface.IPMITOOL_PATH = 'printf "%s\\n"'

        cmd = interface._build_serial_ipmitool_cmd(Target(0x20), 0, 0x6,
                                                   b'\x01')
        output, _ = interface._run_ipmitool(cmd)
        args = output.decode().splitlines()

        assert 'injected' not in args
        assert args[args.index('-D') + 1] == '/dev/tty2; echo injected:115200'

    def test_send_and_receive_raw_return_value(self):
        mock = MagicMock()
        mock.return_value = (b' 10 80 01 02 51 bd 98 3a 00 a8 '
                             b'06 00 03 00 00\n', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        assert data == b'\x00\x10\x80\x01\x02\x51\xbd\x98' \
                       b'\x3a\x00\xa8\x06\x00\x03\x00\x00'

    def test_send_and_receive_raw_completion_code_timeout(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 '
                             b'netfn=0x6 lun=0x0 cmd=0x1 rsp=0xc3): '
                             b'Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        assert data == b'\xc3'

    def test_send_and_receive_raw_completion_code_not_ok(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 '
                             b'netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): '
                             b'Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        assert data == b'\xcc'

    def test_send_and_receive_raw_timeout_without_response(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command '
                             b'(channel=0x0 netfn=0x6 lun=0x0 cmd=0x1)\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        with pytest.raises(IpmiTimeoutError):
            self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

    def test_send_and_receive_raw_serial(self):
        interface = Ipmitool(interface_type='serial-terminal')
        self.session.set_session_type_serial('/dev/tty2', 115200)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I serial-terminal '
                                     '-D /dev/tty2:115200 -t 0x20 -l 0 '
                                     'raw 0x06 0x01 2>&1')

    @pytest.mark.parametrize('interface_type', ['lan', 'serial-terminal'])
    def test_send_and_receive_raw_completion_code_on_stderr(self,
                                                            interface_type):
        # ipmitool prints the completion code to stderr and exits with 1
        interface = Ipmitool(interface_type=interface_type)
        if interface_type == 'serial-terminal':
            self.session.set_session_type_serial('/dev/tty2', 115200)
        interface.establish_session(self.session)
        interface.IPMITOOL_PATH = (
            "sh -c 'echo \"Unable to send RAW command (channel=0x0 "
            "netfn=0x6 lun=0x0 cmd=0x1 rsp=0xc1): Invalid command\" >&2; "
            "exit 1' ipmitool")

        data = interface.send_and_receive_raw(Target(0x20), 0, 0x6, b'\x01')
        assert data == b'\xc1'

    @pytest.mark.parametrize('interface_type, target, system_interface', [
        ('open', Target(), True),
        ('open', Target(0x20), True),
        ('open', Target(0x72), False),
        ('open', Target(0x72, routing=[(0x20, 0x72, 0)]), True),
        ('open', Target(0x72, routing=[(0x20, 0x20, 7), (0x20, 0x72, None)]),
         False),
        ('lan', Target(0x20), False),
        ('lanplus', Target(0x20), False),
    ])
    def test_is_system_interface(self, interface_type, target,
                                 system_interface):
        interface = Ipmitool(interface_type=interface_type)
        assert interface.is_system_interface(target) is system_interface

    def test_rmcp_ping_serial_terminal(self):
        interface = Ipmitool(interface_type='serial-terminal')
        with pytest.raises(RuntimeError, match='^rmcp_ping not supported'):
            interface.rmcp_ping()

    @pytest.mark.parametrize('cipher', ['-1', '256', '666'])
    def test_ipmitool_cipher_out_of_range(self, cipher):
        with pytest.raises(RuntimeError):
            Ipmitool(cipher=cipher)

    @pytest.mark.parametrize('cipher', ['0', '17', '255'])
    def test_ipmitool_cipher_in_range(self, cipher):
        Ipmitool(cipher=cipher)

    def test_send_and_receive_raw_retries_timeout(self):
        interface = Ipmitool(interface_type='lanplus', cipher='3',
                             retries=1, timeout=2)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lanplus -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -C 3 -R 1 -N 2 '
                                     '-U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_retries_zero(self):
        interface = Ipmitool(retries=0)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        interface.send_and_receive_raw(Target(0x20), 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -L ADMINISTRATOR -R 0 '
                                     '-U admin -P secret '
                                     '-t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_rmcp_ping_retries_timeout(self):
        interface = Ipmitool(retries=1, timeout=2)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        interface.rmcp_ping()
        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-v -R 1 -N 2 -U admin -P secret '
                                     'session info all')

    @pytest.mark.parametrize('kwargs', [
        {'interface_type': 'open', 'retries': 1},
        {'interface_type': 'serial-terminal', 'timeout': 1},
        {'retries': -1},
        {'timeout': 0},
    ])
    def test_ipmitool_retries_timeout_invalid(self, kwargs):
        with pytest.raises(RuntimeError):
            Ipmitool(**kwargs)

    def test_parse_output_rsp(self):
        test_str = b' 12 34 56 78 \r\n d0 0f af fe de ad be ef\naa 55\r\nbb    \n'
        cc, rsp = self._interface._parse_output(test_str)
        assert cc is None
        assert py3_array_tobytes(rsp) == b'\x12\x34\x56\x78\xd0\x0f\xaf\xfe\xde\xad\xbe\xef\xaa\x55\xbb'

    def test_parse_output_rsp_suppressed_error(self):
        test_str = b'Get HPM.x Capabilities request failed, compcode = c9\n'\
                   b' 12 34 56 78 \r\n d0 0f af fe de ad be ef\naa 55\r\nbb    \n'
        cc, rsp = self._interface._parse_output(test_str)
        assert cc is None
        assert py3_array_tobytes(rsp) == b'\x12\x34\x56\x78\xd0\x0f\xaf\xfe\xde\xad\xbe\xef\xaa\x55\xbb'

    def test_parse_output_rsp_suppressed_unexpected_id(self):
        test_str = b'Received a response with unexpected ID 0 vs. 1\n'\
                   b' 12 34 56 78 \r\n d0 0f af fe de ad be ef\naa 55\r\nbb    \n'
        cc, rsp = self._interface._parse_output(test_str)
        assert cc is None
        assert py3_array_tobytes(rsp) == b'\x12\x34\x56\x78\xd0\x0f\xaf\xfe\xde\xad\xbe\xef\xaa\x55\xbb'

    def test_parse_output_rsp_verbose_mixed_with_debug_text(self):
        # With "-v" ipmitool interleaves plain-text debug lines with the
        # actual hex response line. A single non-hex debug line must not
        # discard the response bytes already found on other lines.
        test_str = (
            b'Loading IANA PEN Registry...\n'
            b'Using best available cipher suite 3\n'
            b'Running Get VSO Capabilities\n'
            b'my_addr 0x20, transit 0, target 0x20\n'
            b'Invalid completion code received: Invalid command\n'
            b'Discovered IPMB address 0x0\n'
            b'RAW REQ (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 data_len=0)\n'
            b'RAW RSP (15 bytes)\n'
            b' 20 01 04 00 02 bf 7c 2a 00 69 09 00 00 00 00\n'
        )
        cc, rsp = self._interface._parse_output(test_str)
        assert cc is None
        assert py3_array_tobytes(rsp) == (
            b'\x20\x01\x04\x00\x02\xbf\x7c\x2a\x00\x69\x09\x00\x00\x00\x00'
        )

    def test_parse_output_rsp_verbose_excludes_echoed_request_bytes(self):
        # With "-v" and a command that has a request payload (e.g. GetSdr),
        # ipmitool echoes the outgoing bytes as its own "RAW REQUEST (N
        # bytes)" hex dump before printing "RAW RSP". Those echoed bytes
        # must not be prepended to the parsed response.
        test_str = (
            b'Loading IANA PEN Registry...\n'
            b'Using best available cipher suite 3\n'
            b'\n'
            b'Running Get VSO Capabilities my_addr 0x20, transit 0, target 0x20\n'
            b'Invalid completion code received: Invalid command\n'
            b'Discovered IPMB address 0x0\n'
            b'RAW REQ (channel=0x0 netfn=0xa lun=0x0 cmd=0x23 data_len=6)\n'
            b'RAW REQUEST (6 bytes)\n'
            b' 21 00 00 00 00 05\n'
            b'RAW RSP (7 bytes)\n'
            b' 47 00 04 00 51 01 33\n'
        )
        cc, rsp = self._interface._parse_output(test_str)
        assert cc is None
        assert py3_array_tobytes(rsp) == b'\x47\x00\x04\x00\x51\x01\x33'

    def test_parse_output_cc(self):
        test_str = b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n'
        cc, rsp = self._interface._parse_output(test_str)
        assert cc == 0xcc
        assert rsp is None

    def test_parse_output_cc_suppressed_error(self):
        test_str = b'Get HPM.x Capabilities request failed, compcode = c9\n'\
                   b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n'
        cc, rsp = self._interface._parse_output(test_str)
        assert cc == 0xcc
        assert rsp is None

    def test_parse_output_connection_error_rmcp_plus(self):
        test_str = b'Error: Unable to establish IPMI v2 / RMCP+ session\n'
        with pytest.raises(IpmiConnectionError):
            cc, rsp = self._interface._parse_output(test_str)
            assert cc == 0xcc
            assert rsp is None

    def test_parse_output_connection_error(self):
        test_str = b'Error: Unable to establish LAN session'
        with pytest.raises(IpmiConnectionError):
            cc, rsp = self._interface._parse_output(test_str)
            assert rsp is None

    def test_parse_output_connection_error_rmcp(self):
        test_str = b'Error: Unable to establish IPMI v1.5 / RMCP session'
        with pytest.raises(IpmiConnectionError):
            cc, rsp = self._interface._parse_output(test_str)
            assert rsp is None

    def test_parse_long_password_error(self):
        test_str = b'lanplus: password is longer than 20 bytes.'
        with pytest.raises(IpmiLongPasswordError):
            cc, rsp = self._interface._parse_output(test_str)
            assert rsp is None

    def test_parse_output_authentication_error(self):
        test_str = b'Loading ...\nUsing ...\n> RAKP 2 HMAC is invalid\nError:'
        with pytest.raises(AuthenticationError):
            cc, rsp = self._interface._parse_output(test_str)
            assert rsp is None
