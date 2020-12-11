#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import MagicMock
from nose.tools import eq_, raises

from pyipmi.errors import IpmiTimeoutError
from pyipmi.interfaces import Ipmitool
from pyipmi import Session, Target
from pyipmi.utils import py3_array_tobytes


class TestIpmitool:

    def setup(self):
        self._interface = Ipmitool(interface_type='lan')
        self.session = Session()
        self.session.interface = self._interface
        self.session.set_session_type_rmcp('10.0.1.1')
        self.session.set_auth_type_user('admin', 'secret')
        self._interface.establish_session(self.session)

    def test_build_ipmitool_target_ipmb_address(self):
        target = Target(0xb0)
        cmd = self._interface._build_ipmitool_target(target)
        eq_(cmd, ' -t 0xb0')

    def test_build_ipmitool_target_routing_2(self):
        target = Target(routing=[(0x81, 0x20, 7), (0x20, 0x82, 0)])
        cmd = self._interface._build_ipmitool_target(target)
        eq_(cmd, ' -t 0x82 -b 7')

    def test_build_ipmitool_target_routing_3(self):
        target = Target(routing=[(0x81, 0x20, 0),
                                 (0x20, 0x82, 7),
                                 (0x20, 0x72, None)])
        cmd = self._interface._build_ipmitool_target(target)
        eq_(cmd, ' -T 0x82 -B 0 -t 0x72 -b 7')

    def test_send_and_receive(self):
        pass

    def test_rmcp_ping(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface.rmcp_ping()
        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-U "admin" -P "secret" '
                                     'session info all')

    def test_send_and_receive_raw_valid(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-U "admin" -P "secret" -t 0x20 -l 0 '
                                     'raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_lanplus(self):
        interface = Ipmitool(interface_type='lanplus')
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lanplus -H 10.0.1.1 -p 623 '
                                     '-U "admin" -P "secret" -t 0x20 -l 0 '
                                     'raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_no_auth(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface._session.auth_type = Session.AUTH_TYPE_NONE

        target = Target(0x20)
        self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 '
                                     '-P "" -t 0x20 -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_return_value(self):
        mock = MagicMock()
        mock.return_value = (b' 10 80 01 02 51 bd 98 3a 00 a8 '
                             b'06 00 03 00 00\n', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        eq_(data, b'\x00\x10\x80\x01\x02\x51\xbd\x98\x3a\x00\xa8\x06'
                  b'\x00\x03\x00\x00')

    def test_send_and_receive_raw_completion_code_timeout(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 '
                             b'netfn=0x6 lun=0x0 cmd=0x1 rsp=0xc3): '
                             b'Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        eq_(data, b'\xc3')

    def test_send_and_receive_raw_completion_code_not_ok(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 '
                             b'netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): '
                             b'Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, b'\x01')

        eq_(data, b'\xcc')

    @raises(IpmiTimeoutError)
    def test_send_and_receive_raw_timeout_without_response(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command '
                             b'(channel=0x0 netfn=0x6 lun=0x0 cmd=0x1)\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
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
                                     'raw 0x06 0x01')

    def test_parse_output_rsp(self):
        test_str = b' 12 34 56 78 \r\n d0 0f af fe de ad be ef\naa 55\r\nbb    \n'
        cc, rsp = self._interface._parse_output(test_str)
        eq_(cc, None)
        eq_(py3_array_tobytes(rsp), b'\x12\x34\x56\x78\xd0\x0f\xaf\xfe\xde\xad\xbe\xef\xaa\x55\xbb')

    def test_parse_output_rsp_suppressed_error(self):
        test_str = b'Get HPM.x Capabilities request failed, compcode = c9\n'\
                   b' 12 34 56 78 \r\n d0 0f af fe de ad be ef\naa 55\r\nbb    \n'
        cc, rsp = self._interface._parse_output(test_str)
        eq_(cc, None)
        eq_(py3_array_tobytes(rsp), b'\x12\x34\x56\x78\xd0\x0f\xaf\xfe\xde\xad\xbe\xef\xaa\x55\xbb')

    def test_parse_output_cc(self):
        test_str = b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n'
        cc, rsp = self._interface._parse_output(test_str)
        eq_(cc, 0xcc)
        eq_(rsp, None)

    def test_parse_output_cc_suppressed_error(self):
        test_str = b'Get HPM.x Capabilities request failed, compcode = c9\n'\
                   b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n'
        cc, rsp = self._interface._parse_output(test_str)
        eq_(cc, 0xcc)
        eq_(rsp, None)
