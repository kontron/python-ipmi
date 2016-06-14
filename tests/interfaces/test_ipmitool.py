#!/usr/bin/env python
#-*- coding: utf-8 -*-

from array import array

import nose
from mock import MagicMock
from nose.tools import eq_, raises

from pyipmi.errors import TimeoutError
from pyipmi.interfaces import Ipmitool
from pyipmi import Session, Target

class TestIpmitool:

    def setup(self):
        self._interface = Ipmitool(interface_type='lan')
        self.session = Session()
        self.session.interface = self._interface
        self.session.set_session_type_rmcp('10.0.1.1')
        self.session.set_auth_type_user('admin', 'secret')
        self._interface.establish_session(self.session)

    def test_send_and_receive_raw_valid(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        data = self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 -t 0x20 -U "admin" -P "secret" -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_lanplus(self):
        interface = Ipmitool(interface_type='lanplus')
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        data = interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        mock.assert_called_once_with('ipmitool -I lanplus -H 10.0.1.1 -p 623 -t 0x20 -U "admin" -P "secret" -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_no_auth(self):
        mock = MagicMock()
        mock.return_value = (b'', 0)
        self._interface._run_ipmitool = mock

        self._interface._session.set_auth_type(Session.AUTH_TYPE_NONE)

        target = Target(0x20)
        data = self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        mock.assert_called_once_with('ipmitool -I lan -H 10.0.1.1 -p 623 -t 0x20 -P "" -l 0 raw 0x06 0x01 2>&1')

    def test_send_and_receive_raw_return_value(self):
        mock = MagicMock()
        mock.return_value = (b' 10 80 01 02 51 bd 98 3a 00 a8 06 00 03 00 00\n', 0)
        self._interface._run_ipmitool = mock

        target = Target(0x20)
        data = self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        eq_(data, array('B',
           b'\x00\x10\x80\x01\x02\x51\xbd\x98\x3a\x00\xa8\x06\x00\x03\x00\x00'))

    def test_send_and_receive_raw_completion_code_timeout(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xc3): Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        eq_(data, array('B', b'\xc3'))

    def test_send_and_receive_raw_completion_code_not_ok(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        data = self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        eq_(data, array('B', b'\xcc'))

    @raises(TimeoutError)
    def test_send_and_receive_raw_timeout_without_response(self):
        mock = MagicMock()
        mock.return_value = (b'Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1)\n', 1)

        target = Target(0x20)
        self._interface._run_ipmitool = mock
        self._interface.send_and_receive_raw(target, 0, 0x6, '\x01')


    def test_send_and_receive_raw_serial(self):
        interface = Ipmitool(interface_type='serial-terminal')
        self.session.set_session_type_serial('/dev/tty2', 115200)
        interface.establish_session(self.session)

        mock = MagicMock()
        mock.return_value = (b'', 0)
        interface._run_ipmitool = mock

        target = Target(0x20)
        data = interface.send_and_receive_raw(target, 0, 0x6, '\x01')

        mock.assert_called_once_with('ipmitool -I serial-terminal -D /dev/tty2:115200 -t 0x20 -l 0 raw 0x06 0x01')

