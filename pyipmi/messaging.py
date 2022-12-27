# Copyright (c) 2016  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

from enum import Enum

from .session import Session
from .msgs import create_request_by_name
from .utils import check_completion_code
from .state import State


class PasswordOperation(int, Enum):
    DISABLE = 0b00
    ENABLE = 0b01
    SET_PASSWORD = 0b10
    TEST_PASSWORD = 0b11


class UserPrivilegeLevel(str, Enum):
    RESERVED = "reserved"
    CALLBACK = "callback"
    USER = "user"
    OPERATOR = "operator"
    ADMINISTRATOR = "administrator"
    OEM = "oem"
    NO_ACCESS = "no access"


CONVERT_RAW_TO_USER_PRIVILEGE = {
    0x00: UserPrivilegeLevel.RESERVED,
    0x01: UserPrivilegeLevel.CALLBACK,
    0x02: UserPrivilegeLevel.USER,
    0x03: UserPrivilegeLevel.OPERATOR,
    0x04: UserPrivilegeLevel.ADMINISTRATOR,
    0x05: UserPrivilegeLevel.OEM,
    0x0F: UserPrivilegeLevel.NO_ACCESS
}

CONVERT_USER_PRIVILEGE_TO_RAW = {
    UserPrivilegeLevel.RESERVED:      0x00,
    UserPrivilegeLevel.CALLBACK:      0x01,
    UserPrivilegeLevel.USER:          0x02,
    UserPrivilegeLevel.OPERATOR:      0x03,
    UserPrivilegeLevel.ADMINISTRATOR: 0x04,
    UserPrivilegeLevel.OEM:           0x05,
    UserPrivilegeLevel.NO_ACCESS:     0x0F
}


class Messaging(object):
    def get_channel_authentication_capabilities(self, channel, priv_lvl):
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.channel.number = channel
        req.privilege_level.requested = priv_lvl
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        caps = ChannelAuthenticationCapabilities(rsp)
        return caps

    def set_username(self, userid=0, username=''):
        req = create_request_by_name('SetUserName')
        req.userid.userid = userid
        req.user_name = username.ljust(16, '\x00')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_username(self, userid=0):
        req = create_request_by_name('GetUserName')
        req.userid.userid = userid
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.user_name

    def get_user_access(self, userid=0, channel=0):
        req = create_request_by_name('GetUserAccess')
        req.userid.userid = userid
        req.channel.channel_number = channel
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return UserAccess(rsp)

    def set_user_access(self, userid, ipmi_msg, link_auth, callback_only,
                        priv_level, channel=0, enable_change=1):
        req = create_request_by_name('SetUserAccess')
        req.channel_access.channel_number = channel
        req.channel_access.ipmi_msg = ipmi_msg
        req.channel_access.link_auth = link_auth
        req.channel_access.callback = callback_only
        req.channel_access.enable_change = enable_change
        req.userid.userid = userid
        req.privilege.privilege_level = CONVERT_USER_PRIVILEGE_TO_RAW.get(
            priv_level, 0x0F)
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_user_password(self, userid, password=''):
        if len(password) > 16:
            raise ValueError("Password length cannot be greater than 20.")
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.SET_PASSWORD
        req.password = password.ljust(16, '\x00')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def enable_user(self, userid):
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.ENABLE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def disable_user(self, userid):
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.DISABLE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)


class ChannelAuthenticationCapabilities(State):

    _functions = {
        'none': Session.AUTH_TYPE_NONE,
        'md2': Session.AUTH_TYPE_MD2,
        'md5': Session.AUTH_TYPE_MD5,
        'straight': Session.AUTH_TYPE_PASSWORD,
        'oem_proprietary': Session.AUTH_TYPE_OEM,
    }

    def _from_response(self, rsp):
        self.channel = rsp.channel_number
        self.auth_types = []

        self.ipmi_1_5 = False
        self.ipmi_2_0 = False

        if rsp.support.ipmi_2_0:
            self.ipmi_2_0 = True
        else:
            self.ipmi_1_5 = True

        for function in self._functions.keys():
            if hasattr(rsp.support, function):
                if getattr(rsp.support, function):
                    self.auth_types.append(function)

    def get_max_auth_type(self):
        for auth_type in ('md5', 'md2', 'straight', 'oem_proprietary', 'none'):
            if auth_type in self.auth_types:
                return self._functions[auth_type]
        return None

    def __str__(self):
        s = 'Authentication Capabilities:\n'
        s += '  IPMI v1.5: %s\n' % self.ipmi_1_5
        s += '  IPMI v2.0: %s\n' % self.ipmi_2_0
        s += '  Auth. types: %s\n' % ' '.join(self.auth_types)
        s += '  Max Auth. type: %s\n' % self.get_max_auth_type()
        return s


class UserAccess(State):

    def _from_response(self, rsp):
        self.user_count = rsp.max_user.max_user
        self.enabled_user_count = rsp.enabled_user.count
        self.enabled_status = rsp.enabled_user.status
        self.fixed_name_user_count = rsp.fixed_names.count
        self.privilege_level = CONVERT_RAW_TO_USER_PRIVILEGE.get(rsp.channel_access.privilege, UserPrivilegeLevel.RESERVED)
        self.ipmi_messaging = rsp.channel_access.ipmi_msg == 1
        self.link_auth = rsp.channel_access.link_auth == 1
        self.callback_only = rsp.channel_access.callback == 1

    def __str__(self):
        s = 'User Access:\n'
        s += '  Max user number: %i\n' % self.user_count
        s += '  Enabled user: %i\n' % self.enabled_user_count
        s += '  Enabled status: %i\n' % self.enabled_status
        s += '  Fixed name user: %i\n' % self.fixed_name_user_count
        s += '  Privilege level: %s\n' % self.privilege_level
        s += '  IPMI messaging: %s\n' % self.ipmi_messaging
        s += '  Link Auth.: %s\n' % self.link_auth
        s += '  Callback only: %s' % self.callback_only
