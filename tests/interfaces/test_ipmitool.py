#!/usr/bin/env python
#-*- coding: utf-8 -*-

from array import array

import nose
from mock import MagicMock
from nose.tools import eq_, raises

from pyipmi.errors import TimeoutError
from pyipmi.interfaces import Ipmitool

class TestIpmitool:

    def setup(self):
        self.interface = Ipmitool()

    def test_send_and_receive_raw_valid(self):
        mock = MagicMock()
        mock.return_value = (' 10 80 01 02 51 bd 98 3a 00 a8 06 00 03 00 00\n', 0)

        self.interface._run_ipmitool = mock
        data = self.interface.send_and_receive_raw(0x20, 0, 0x6, '\x01')

        eq_(data, array('c', '\x00\x10\x80\x01\x02\x51\xbd\x98\x3a\x00\xa8\x06\x00\x03\x00\x00'))
        mock.assert_called_once_with(0x20, '-l 0 raw 0x06 0x01')

    def test_send_and_receive_raw_completion_code_timeout(self):
        mock = MagicMock()
        mock.return_value = ('Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xc3): Ignore Me\n', 1)

        self.interface._run_ipmitool = mock
        data = self.interface.send_and_receive_raw(0x20, 0, 0x6, '\x01')

        eq_(data, array('c', '\xc3'))

    def test_send_and_receive_raw_completion_code_not_ok(self):
        mock = MagicMock()
        mock.return_value = ('Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1 rsp=0xcc): Ignore Me\n', 1)

        self.interface._run_ipmitool = mock
        data = self.interface.send_and_receive_raw(0x20, 0, 0x6, '\x01')

        eq_(data, array('c', '\xcc'))

    @raises(TimeoutError)
    def test_send_and_receive_raw_timeout_without_response(self):
        mock = MagicMock()
        mock.return_value = ('Unable to send RAW command (channel=0x0 netfn=0x6 lun=0x0 cmd=0x1)\n', 1)

        self.interface._run_ipmitool = mock
        self.interface.send_and_receive_raw(0x20, 0, 0x6, '\x01')
