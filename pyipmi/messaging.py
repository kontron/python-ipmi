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

"""Messaging commands: channels and users.

The commands read the channel information and authentication
capabilities, and manage the users of the BMC: their names, passwords and
access rights per channel.

The commands are the methods of :class:`Messaging`, which are available on
:class:`pyipmi.Ipmi`.

Example:
    Create user 3 with administrator access on channel 1::

        from pyipmi.messaging import UserPrivilegeLevel

        ipmi.set_username(3, 'admin')
        ipmi.set_user_password(3, 'secret')
        ipmi.set_user_access(3, ipmi_msg=True, link_auth=True,
                             callback_only=False,
                             priv_level=UserPrivilegeLevel.ADMINISTRATOR,
                             channel=1)
        ipmi.enable_user(3)
"""

from __future__ import annotations

from enum import Enum

from .session import Session
from .msgs import create_request_by_name, Message
from .utils import check_completion_code, check_rsp_completion_code
from .state import State
from .mixin import IpmiMixin


class PasswordOperation(int, Enum):
    """The operations of the Set User Password command."""

    DISABLE = 0b00
    ENABLE = 0b01
    SET_PASSWORD = 0b10
    TEST_PASSWORD = 0b11


class UserPrivilegeLevel(str, Enum):
    """The privilege levels of a user, the values are their names."""

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


class Messaging(IpmiMixin):
    """Messaging commands, available on :class:`pyipmi.Ipmi`."""

    def get_channel_authentication_capabilities(
            self, channel: int,
            priv_lvl: int) -> ChannelAuthenticationCapabilities:
        """Get the authentication capabilities of a channel.

        Args:
            channel: The channel number.
            priv_lvl: The requested privilege level, one of the
                ``PRIV_LEVEL_*`` constants of :class:`pyipmi.session.Session`.

        Returns:
            The authentication capabilities.
        """
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.channel.number = channel
        req.privilege_level.requested = priv_lvl
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        caps = ChannelAuthenticationCapabilities(rsp)
        return caps

    def get_channel_info(self, channel: int) -> ChannelInfo:
        """Get the information about a channel.

        Args:
            channel: The channel number.

        Returns:
            The channel information.

        Raises:
            CompletionCodeError: The BMC rejected the request, e.g. for a
                channel that is not implemented.
        """
        req = create_request_by_name('GetChannelInfo')
        req.channel.number = channel
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return ChannelInfo(rsp)

    def set_username(self, userid: int = 0, username: str = '') -> None:
        """Set the name of a user.

        Args:
            userid: The user ID.
            username: The user name, at most 16 characters.
        """
        req = create_request_by_name('SetUserName')
        req.userid.userid = userid
        req.user_name = username.ljust(16, '\x00')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_username(self, userid: int = 0) -> bytes:
        """Get the name of a user.

        Args:
            userid: The user ID.

        Returns:
            The user name as the 16 bytes of the response, padded with null
            bytes.
        """
        req = create_request_by_name('GetUserName')
        req.userid.userid = userid
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.user_name

    def get_user_access(self, userid: int = 0, channel: int = 0) -> UserAccess:
        """Get the access rights of a user on a channel.

        Args:
            userid: The user ID.
            channel: The channel number.

        Returns:
            The user access.
        """
        req = create_request_by_name('GetUserAccess')
        req.userid.userid = userid
        req.channel.channel_number = channel
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return UserAccess(rsp)

    def set_user_access(self, userid: int, ipmi_msg: bool, link_auth: bool,
                        callback_only: bool, priv_level: UserPrivilegeLevel,
                        channel: int = 0, enable_change: int = 1,
                        user_session_limit: int = 0) -> None:
        """Set the access rights of a user on a channel.

        Args:
            userid: The user ID.
            ipmi_msg: Enable IPMI messaging for the user.
            link_auth: Enable link authentication for the user.
            callback_only: Restrict the user to callback connections.
            priv_level: The maximum privilege level of the user.
            channel: The channel number.
            enable_change: 1 to change the access bits ``ipmi_msg``,
                ``link_auth`` and ``callback_only``, 0 to keep them.
            user_session_limit: The maximum number of simultaneous sessions
                of the user, 0 for no limit.
        """
        req = create_request_by_name('SetUserAccess')
        req.channel_access.channel_number = channel
        req.channel_access.ipmi_msg = ipmi_msg
        req.channel_access.link_auth = link_auth
        req.channel_access.callback = callback_only
        req.channel_access.enable_change = enable_change
        req.userid.userid = userid
        req.privilege.privilege_level = CONVERT_USER_PRIVILEGE_TO_RAW.get(
            priv_level, 0x0F)
        req.session_limit.simultaneous_session_limit = user_session_limit
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def set_user_password(self, userid: int, password: str = '') -> None:
        """Set the password of a user.

        Args:
            userid: The user ID.
            password: The password, at most 16 characters.

        Raises:
            ValueError: The password is longer than 16 characters.
        """
        if len(password) > 16:
            raise ValueError("Password length cannot be greater than 16.")
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.SET_PASSWORD
        req.password = password.ljust(16, '\x00')
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def enable_user(self, userid: int) -> None:
        """Enable a user.

        Args:
            userid: The user ID.
        """
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.ENABLE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def disable_user(self, userid: int) -> None:
        """Disable a user.

        Args:
            userid: The user ID.
        """
        req = create_request_by_name('SetUserPassword')
        req.userid.userid = userid
        req.operation.operation = PasswordOperation.DISABLE
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)


class ChannelAuthenticationCapabilities(State):
    """The authentication capabilities of a channel.

    Attributes:
        channel (int): The channel number.
        auth_types (list[str]): The supported authentication types:
            ``'none'``, ``'md2'``, ``'md5'``, ``'straight'`` (password) and
            ``'oem_proprietary'``.
        ipmi_1_5 (bool): The channel reports no IPMI v2.0 extended
            capabilities.
        ipmi_2_0 (bool): The channel supports IPMI v2.0 extended
            capabilities.
    """

    _functions = {
        'none': Session.AUTH_TYPE_NONE,
        'md2': Session.AUTH_TYPE_MD2,
        'md5': Session.AUTH_TYPE_MD5,
        'straight': Session.AUTH_TYPE_PASSWORD,
        'oem_proprietary': Session.AUTH_TYPE_OEM,
    }

    def _from_response(self, rsp: Message) -> None:
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

    def get_max_auth_type(self) -> int | None:
        """Return the strongest supported authentication type.

        The types are preferred in the order MD5, MD2, straight password,
        OEM and none.

        Returns:
            The authentication type, one of the ``AUTH_TYPE_*`` constants of
            :class:`pyipmi.session.Session`, None if no type is supported.
        """
        for auth_type in ('md5', 'md2', 'straight', 'oem_proprietary', 'none'):
            if auth_type in self.auth_types:
                return self._functions[auth_type]
        return None

    def __str__(self) -> str:
        """Return the capabilities as multi-line string."""
        s = 'Authentication Capabilities:\n'
        s += '  IPMI v1.5: %s\n' % self.ipmi_1_5
        s += '  IPMI v2.0: %s\n' % self.ipmi_2_0
        s += '  Auth. types: %s\n' % ' '.join(self.auth_types)
        s += '  Max Auth. type: %s\n' % self.get_max_auth_type()
        return s


class ChannelInfo(State):
    """The information about a channel.

    Attributes:
        channel (int): The channel number.
        medium_type (int): The channel medium type, e.g. 1 for IPMB and 4
            for 802.3 LAN.
        protocol_type (int): The channel protocol type, e.g. 1 for IPMB-1.0.
        session_support (int): 0 session-less, 1 single-session, 2
            multi-session, 3 session-based.
        active_session_count (int): The number of active sessions.
        vendor_id (int): The IANA enterprise number of the vendor.
    """

    def _from_response(self, rsp: Message) -> None:
        self.channel = rsp.channel.number
        self.medium_type = rsp.medium.type
        self.protocol_type = rsp.protocol.type
        self.session_support = rsp.session.support
        self.active_session_count = rsp.session.active_count
        self.vendor_id = rsp.vendor_id

    def __str__(self) -> str:
        """Return the channel number, medium type and protocol type."""
        return ('Channel %d: medium 0x%02x protocol 0x%02x'
                % (self.channel, self.medium_type, self.protocol_type))


class UserAccess(State):
    """The access rights of a user on a channel.

    Attributes:
        user_count (int): The maximum number of user IDs.
        enabled_user_count (int): The number of enabled user IDs.
        enabled_status (int): The enable status of the user: 0
            unspecified, 1 enabled, 2 disabled.
        fixed_name_user_count (int): The number of user IDs with a fixed
            name.
        privilege_level (UserPrivilegeLevel): The maximum privilege level
            of the user.
        ipmi_messaging (bool): IPMI messaging is enabled for the user.
        link_auth (bool): Link authentication is enabled for the user.
        callback_only (bool): The user is restricted to callback
            connections.
    """

    def _from_response(self, rsp: Message) -> None:
        self.user_count = rsp.max_user.max_user
        self.enabled_user_count = rsp.enabled_user.count
        self.enabled_status = rsp.enabled_user.status
        self.fixed_name_user_count = rsp.fixed_names.count
        self.privilege_level = CONVERT_RAW_TO_USER_PRIVILEGE.get(rsp.channel_access.privilege, UserPrivilegeLevel.RESERVED)
        self.ipmi_messaging = rsp.channel_access.ipmi_msg == 1
        self.link_auth = rsp.channel_access.link_auth == 1
        self.callback_only = rsp.channel_access.callback == 1

    def __str__(self) -> str:
        """Return the user access as multi-line string."""
        s = 'User Access:\n'
        s += '  Max user number: %i\n' % self.user_count
        s += '  Enabled user: %i\n' % self.enabled_user_count
        s += '  Enabled status: %i\n' % self.enabled_status
        s += '  Fixed name user: %i\n' % self.fixed_name_user_count
        s += '  Privilege level: %s\n' % self.privilege_level
        s += '  IPMI messaging: %s\n' % self.ipmi_messaging
        s += '  Link Auth.: %s\n' % self.link_auth
        s += '  Callback only: %s' % self.callback_only
        return s
