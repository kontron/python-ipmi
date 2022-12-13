#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, ok_

from pyipmi.messaging import UserAccess, UserPrivilegeLevel
import pyipmi.msgs.device_messaging
from pyipmi.msgs import decode_message

def test_useraccess_object():
    msg = pyipmi.msgs.device_messaging.GetUserAccessRsp()
    decode_message(msg, b'\x00\x0a\x42\x01\x13')

    user_access = UserAccess(msg)

    eq_(user_access.user_count, 10)
    eq_(user_access.enabled_user_count, 2)
    eq_(user_access.enabled_status, 1)
    eq_(user_access.fixed_name_user_count, 1)
    eq_(user_access.privilege_level, UserPrivilegeLevel.OPERATOR)
    ok_(user_access.ipmi_messaging, 1)
    ok_(not user_access.link_auth, 0)
    ok_(not user_access.callback_only, 0)
