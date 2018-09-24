#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, ok_

from pyipmi.chassis import ChassisStatus
import pyipmi.msgs.chassis
from pyipmi.msgs import decode_message


def test_chassisstatus_object():
    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\xff\xff\xff')

    status = ChassisStatus(msg)

    eq_(status.power_on, True)
    eq_(status.overload, True)
    eq_(status.interlock, True)
    eq_(status.fault, True)
    eq_(status.control_fault, True)
    eq_(status.restore_policy, 3)

    ok_('ac_failed' in status.last_event)
    ok_('overload' in status.last_event)
    ok_('interlock' in status.last_event)
    ok_('fault' in status.last_event)
    ok_('power_on_via_ipmi' in status.last_event)

    ok_('intrusion', status.chassis_state)
    ok_('front_panel_lockout', status.chassis_state)
    ok_('drive_fault', status.chassis_state)
    ok_('cooling_fault', status.chassis_state)
