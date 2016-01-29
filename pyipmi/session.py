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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


class Session(object):
    AUTH_TYPE_NONE        = 0x0
    AUTH_TYPE_MD2         = 0x1
    AUTH_TYPE_MD5         = 0x2
    AUTH_TYPE_PASSWORD    = 0x4
    AUTH_TYPE_OEM         = 0x5

    PRIV_LEVEL_USER = 2
    PRIV_LEVEL_OPERATOR = 3
    PRIV_LEVEL_ADMINISTRATOR = 4
    PRIV_LEVEL_OEM = 5

    def __init__(self):
        self.auth_type = self.AUTH_TYPE_NONE
        self.established = False
        self.sid = 0
        self._auth_username = None
        self._auth_password = None
        self.sequence_number = 0

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def set_session_type_rmcp(self, host, port=623):
        self._rmcp_host = host
        self._rmcp_port = port


    def set_auth_type_user(self, username, password):
        self.auth_type = self.AUTH_TYPE_PASSWORD
        self._auth_username = username
        self._auth_password = password

    def establish(self):
        if hasattr(self.interface, 'establish_session'):
            self.interface.establish_session(self)

    def close(self):
        if hasattr(self.interface, 'close_session'):
            self.interface.close_session()

    def rmcp_ping(self):
        if hasattr(self.interface, 'rmcp_ping'):
            self.interface.rmcp_ping()

    def __str__(self):
        s = 'Session:\n'
        s += '  ID: 0x%08x\n' % self.sid
        s += '  Seq: 0x%08x\n' % self.sequence_number
        s += '  Host: %s:%s\n' % (self._rmcp_host, self._rmcp_port)
        s += '  Auth.: %s\n' % self.auth_type
        s += '  User: %s\n' % self._auth_username
        s += '  Password: %s\n' % self._auth_password
        s += '\n'
        return s

    interface = property(_get_interface, _set_interface)
