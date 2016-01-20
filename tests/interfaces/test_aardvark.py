#!/usr/bin/env python
#-*- coding: utf-8 -*-
import sys
from array import array

import nose
from mock import MagicMock, patch
from nose.tools import eq_, ok_, raises

from pyipmi.interfaces.ipmb import IpmbHeader

class MockPyaardvark:
    def enable_i2c_slave(self, d):
        pass

class TestAardvark:
    pass

#    @classmethod
#    def setup_class(self):
#        """Mock pyaardvark import
#        http://erikzaadi.com/2012/07/03/mocking-python-imports/
#        """
#        self.pyaardvark_mock = MagicMock()
#        self.pyaardvark_mock.open.return_value = MockPyaardvark()
#
#        modules = {
#            'pyaardvark': self.pyaardvark_mock,
#            'pyaardvark.open': self.pyaardvark_mock.open,
#        }
#
#        self.module_patcher = patch.dict('sys.modules', modules)
#        self.module_patcher.start()
#        ok_('pyaardvark' in sys.modules.keys())
#        ok_('pyaardvark.open' in sys.modules.keys())
#
#        from pyipmi.interfaces.aardvark import Aardvark
#        self.my_aardvark = Aardvark()
#
#    @classmethod
#    def teardown_class(self):
#        """Let's clean up"""
#        self.module_patcher.stop()
#
#    def test_rx_filter(self):
#        header = IpmbHeader()
#        header.rs_lun = 0
#        header.rs_sa = 0x72
#        header.rq_seq = 2
#        header.rq_lun = 0
#        header.rq_sa = 0x20
#        header.netfn = 6
#        header.cmd_id = 1
#
#        rx_data = (0x1c, 0xc4, 0x72, 0x08, 0x1, 0x85)
#
#        ok_(self.my_aardvark._rx_filter(0x20, header, rx_data))
#
#    def test_inc_sequence_number(self):
#        self.my_aardvark.next_sequence_number = 0
#        self.my_aardvark._inc_sequence_number()
#        eq_(self.my_aardvark.next_sequence_number, 1)
#
#        self.my_aardvark.next_sequence_number = 63
#        self.my_aardvark._inc_sequence_number()
#        eq_(self.my_aardvark.next_sequence_number, 0)
