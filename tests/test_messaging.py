#!/usr/bin/env python

import pytest

from pyipmi.errors import CompletionCodeError
from pyipmi.messaging import UserPrivilegeLevel
from pyipmi.session import Session

from .ipmi_helper import create_ipmi


def test_get_channel_authentication_capabilities():
    ipmi = create_ipmi(b'\x00\x01\x96\x04\x03\x00\x00\x00\x00')
    caps = ipmi.get_channel_authentication_capabilities(0xe, 4)
    assert ipmi.requests == [
        ('GetChannelAuthenticationCapabilitiesReq', b'\x0e\x04')]
    assert caps.channel == 1
    assert caps.ipmi_2_0 is True
    assert caps.ipmi_1_5 is False
    assert caps.auth_types == ['md2', 'md5', 'straight']
    assert caps.get_max_auth_type() == Session.AUTH_TYPE_MD5
    assert 'IPMI v2.0: True' in str(caps)


def test_get_channel_authentication_capabilities_ipmi_1_5():
    ipmi = create_ipmi(b'\x00\x01\x01\x04\x00\x00\x00\x00\x00')
    caps = ipmi.get_channel_authentication_capabilities(0xe, 4)
    assert caps.ipmi_1_5 is True
    assert caps.auth_types == ['none']
    assert caps.get_max_auth_type() == Session.AUTH_TYPE_NONE


def test_set_username():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_username(3, 'admin')
    assert ipmi.requests == [('SetUserNameReq', b'\x03admin' + b'\x00' * 11)]


def test_get_username():
    ipmi = create_ipmi(b'\x00admin' + b'\x00' * 11)
    assert ipmi.get_username(3).rstrip(b'\x00') == b'admin'
    assert ipmi.requests == [('GetUserNameReq', b'\x03')]


def test_get_user_access():
    # 10 users, 2 enabled, 1 fixed name, administrator with IPMI messaging
    ipmi = create_ipmi(b'\x00\x0a\x42\x01\x14')
    access = ipmi.get_user_access(userid=2, channel=1)
    assert ipmi.requests == [('GetUserAccessReq', b'\x01\x02')]
    assert access.user_count == 10
    assert access.enabled_user_count == 2
    assert access.enabled_status == 1
    assert access.fixed_name_user_count == 1
    assert access.privilege_level == UserPrivilegeLevel.ADMINISTRATOR
    assert access.ipmi_messaging is True
    assert access.link_auth is False
    assert access.callback_only is False
    assert 'Max user number: 10' in str(access)


def test_set_user_access():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_user_access(2, ipmi_msg=True, link_auth=False,
                         callback_only=False,
                         priv_level=UserPrivilegeLevel.OPERATOR, channel=1)
    assert ipmi.requests == [('SetUserAccessReq', b'\x91\x02\x03\x00')]


def test_set_user_password():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_user_password(2, 'secret')
    assert ipmi.requests == [
        ('SetUserPasswordReq', b'\x02\x02secret' + b'\x00' * 10)]


def test_set_user_password_too_long():
    ipmi = create_ipmi(b'\x00')
    with pytest.raises(ValueError, match='greater than 16'):
        ipmi.set_user_password(2, 'x' * 17)
    assert ipmi.requests == []


@pytest.mark.parametrize('method, operation', [
    ('enable_user', 0x01),
    ('disable_user', 0x00),
])
def test_enable_disable_user(method, operation):
    ipmi = create_ipmi(b'\x00')
    getattr(ipmi, method)(5)
    (name, data) = ipmi.requests[0]
    assert name == 'SetUserPasswordReq'
    assert data[:2] == bytes([5, operation])


def test_completion_code_error():
    ipmi = create_ipmi(b'\xcc')
    with pytest.raises(CompletionCodeError) as e:
        ipmi.enable_user(5)
    assert e.value.cc == 0xcc
