#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from nose.tools import eq_, raises

from pyipmi.msgs.message import Message

class TestMessage:

    def test_message(self):
        msg = Message()
        msg.__netfn__ = 0x1
        msg.__cmdid__ = 0x2

        eq_(msg.lun, 0)
        eq_(msg.netfn, 1)
        eq_(msg.cmdid, 2)
