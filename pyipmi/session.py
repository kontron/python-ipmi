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


from __future__ import annotations

from typing import Any


def _to_bytes(value: str | bytes | None) -> bytes:
    if value is None:
        return b''
    if isinstance(value, str):
        return value.encode()
    return value


class Session:
    AUTH_TYPE_NONE = 0x00
    AUTH_TYPE_MD2 = 0x01
    AUTH_TYPE_MD5 = 0x02
    AUTH_TYPE_PASSWORD = 0x04
    AUTH_TYPE_OEM = 0x05

    PRIV_LEVEL_USER = 2
    PRIV_LEVEL_OPERATOR = 3
    PRIV_LEVEL_ADMINISTRATOR = 4
    PRIV_LEVEL_OEM = 5

    session_id: int | None = None
    _interface: Any = None
    _priv_level = PRIV_LEVEL_ADMINISTRATOR
    _auth_type = AUTH_TYPE_NONE
    _auth_username: str | bytes | None = None
    _auth_password: str | bytes | None = None
    _rmcp_host: str | None = None
    _rmcp_port: int | None = None
    _serial_port: str | None = None
    _serial_baudrate: int | None = None

    def __init__(self) -> None:
        self.established = False
        self.sid = 0
        self.sequence_number = 0
        self.activated = False

    def _get_interface(self) -> Any:
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set') from None

    def _set_interface(self, interface: Any) -> None:
        self._interface = interface

    def increment_sequence_number(self) -> None:
        self.sequence_number += 1
        if self.sequence_number > 0xffffffff:
            self.sequence_number = 1

    def set_session_type_rmcp(self, host: str, port: int = 623) -> None:
        self._rmcp_host = host
        self._rmcp_port = port

    @property
    def rmcp_host(self) -> str | None:
        return self._rmcp_host

    @property
    def rmcp_port(self) -> int | None:
        return self._rmcp_port

    def set_session_type_serial(self, port: str, baudrate: int) -> None:
        self._serial_port = port
        self._serial_baudrate = baudrate

    @property
    def serial_port(self) -> str | None:
        return self._serial_port

    @property
    def serial_baudrate(self) -> int | None:
        return self._serial_baudrate

    @property
    def priv_level(self) -> int:
        return self._priv_level

    def set_priv_level(self, level: str) -> None:
        LEVELS = {
                   'user': self.PRIV_LEVEL_USER,
                   'operator': self.PRIV_LEVEL_OPERATOR,
                   'administrator': self.PRIV_LEVEL_ADMINISTRATOR,
                 }
        self._priv_level = LEVELS[level.lower()]

    def _set_auth_type(self, auth_type: int) -> None:
        self._auth_type = auth_type

    def _get_auth_type(self) -> int:
        return self._auth_type

    def set_auth_type_user(self, username: str | bytes,
                           password: str | bytes) -> None:
        self._auth_type = self.AUTH_TYPE_PASSWORD
        self._auth_username = username
        self._auth_password = password

    @property
    def auth_username(self) -> str | bytes | None:
        return self._auth_username

    @property
    def auth_password(self) -> str | bytes | None:
        return self._auth_password

    @property
    def auth_username_bytes(self) -> bytes:
        """The user name as UTF-8 encoded bytes, empty if not set."""
        return _to_bytes(self._auth_username)

    @property
    def auth_password_bytes(self) -> bytes:
        """The password as UTF-8 encoded bytes, empty if not set."""
        return _to_bytes(self._auth_password)

    def establish(self) -> None:
        if hasattr(self.interface, 'establish_session'):
            self.interface.establish_session(self)

    def close(self) -> None:
        if hasattr(self.interface, 'close_session'):
            self.interface.close_session()

    def rmcp_ping(self) -> None:
        if hasattr(self.interface, 'rmcp_ping'):
            self.interface.rmcp_ping()

    def __str__(self) -> str:
        string = 'Session:\n'
        string += f'  ID: 0x{self.sid:08x}\n'
        string += f'  Seq: 0x{self.sequence_number:08x}\n'
        string += f'  Host: {self._rmcp_host}:{self._rmcp_port}\n'
        string += f'  Auth.: {self.auth_type}\n'
        string += f'  User: {str(self._auth_username)}\n'
        string += f'  Password: {str(self._auth_password)}\n'
        string += '\n'
        return string

    interface = property(_get_interface, _set_interface)
    auth_type = property(_get_auth_type, _set_auth_type)
