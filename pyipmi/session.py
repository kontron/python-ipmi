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


class Session(object):
    AUTH_TYPE_NONE = 0x00
    AUTH_TYPE_MD2 = 0x01
    AUTH_TYPE_MD5 = 0x02
    AUTH_TYPE_PASSWORD = 0x04
    AUTH_TYPE_OEM = 0x05

    PRIV_LEVEL_USER = 2
    PRIV_LEVEL_OPERATOR = 3
    PRIV_LEVEL_ADMINISTRATOR = 4
    PRIV_LEVEL_OEM = 5

    _interface = None
    _auth_type = AUTH_TYPE_NONE
    _auth_username = None
    _auth_password = None
    _rmcp_host = None
    _rmcp_port = None
    _serial_port = None
    _serial_baudrate = None

    def __init__(self):
        self.established = False
        self.sid = 0
        self.sequence_number = 0
        self.activated = False

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def increment_sequence_number(self):
        self.sequence_number += 1
        if self.sequence_number > 0xffffffff:
            self.sequence_number = 1

    def set_session_type_rmcp(self, host, port=623):
        self._rmcp_host = host
        self._rmcp_port = port

    @property
    def rmcp_host(self):
        return self._rmcp_host

    @property
    def rmcp_port(self):
        return self._rmcp_port

    def set_session_type_serial(self, port, baudrate):
        self._serial_port = port
        self._serial_baudrate = baudrate

    @property
    def serial_port(self):
        return self._serial_port

    @property
    def serial_baudrate(self):
        return self._serial_baudrate

    def _set_auth_type(self, auth_type):
        self._auth_type = auth_type

    def _get_auth_type(self):
        return self._auth_type

    def set_auth_type_user(self, username, password):
        self._auth_type = self.AUTH_TYPE_PASSWORD
        self._auth_username = username
        self._auth_password = password

    @property
    def auth_username(self):
        return self._auth_username

    @property
    def auth_password(self):
        return self._auth_password

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
        string = 'Session:\n'
        string += '  ID: 0x%08x\n' % self.sid
        string += '  Seq: 0x%08x\n' % self.sequence_number
        string += '  Host: %s:%s\n' % (self._rmcp_host, self._rmcp_port)
        string += '  Auth.: %s\n' % self.auth_type
        string += '  User: %s\n' % self._auth_username
        string += '  Password: %s\n' % self._auth_password
        string += '\n'
        return string

    interface = property(_get_interface, _set_interface)
    auth_type = property(_get_auth_type, _set_auth_type)
