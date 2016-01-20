#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, ok_, raises

from pyipmi.chassis import *
import pyipmi.msgs.chassis
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

def test_chassisstatus_object():
    m = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(m, '\x00\xff\xff\xff')

    c = ChassisStatus(m)

    eq_(c.power_on, True)
    eq_(c.overload, True)
    eq_(c.interlock, True)
    eq_(c.fault, True)
    eq_(c.control_fault, True)
    eq_(c.restore_policy, 3)

    ok_('ac_failed' in c.last_event)
    ok_('overload' in c.last_event)
    ok_('interlock' in c.last_event)
    ok_('fault' in c.last_event)
    ok_('power_on_via_ipmi' in c.last_event)

    ok_('intrusion', c.chassis_state)
    ok_('front_panel_lockout', c.chassis_state)
    ok_('drive_fault', c.chassis_state)
    ok_('cooling_fault', c.chassis_state)
