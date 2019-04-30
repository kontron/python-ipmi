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


from .session import Session
from .msgs import create_request_by_name
from .utils import check_completion_code
from .state import State


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


class ChannelAuthenticationCapabilities(State):

    _functions = {
        'none': Session.AUTH_TYPE_NONE,
        'md2': Session.AUTH_TYPE_MD2,
        'md5': Session.AUTH_TYPE_MD5,
        'straight': Session.AUTH_TYPE_PASSWORD,
        'oem_proprietary': Session.AUTH_TYPE_OEM,
    }

    def _from_response(self, rsp):
        self.channel= rsp.channel_number
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
