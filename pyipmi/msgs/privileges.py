# Copyright (c) 2026  Kontron Europe GmbH
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

"""The minimum privilege levels of the IPMI commands.

A session sends a command at its present privilege level, the command
needs a minimum level: the ones of IPMI v2.0 Appendix G (Table G-1),
PICMG 3.0, PICMG HPM.1 (Table 6-2) and VITA 46.11 (Table 10.1.2-2), by
network function, command and group extension. Some commands are for the
session-less local interfaces only (``LOCAL_INTERFACE``, e.g. the device
SDR commands) or the system interface only (``SYSTEM_INTERFACE``); both
are above all session levels.

A request message has its level as ``__privilege__``; the IPMI commands
the library has no messages for have it by ID. A command without a level,
e.g. an OEM command, has none here: the OEM defines it.

Example:
    >>> from pyipmi.msgs import constants, privileges
    >>> privileges.required_privilege(constants.NETFN_STORAGE,
    ...                               constants.CMDID_CLEAR_SEL)
    3
"""

from __future__ import annotations

from . import constants
from .registry import DEFAULT_REGISTRY

NONE = 0x00         # before a session, e.g. Get Session Challenge
CALLBACK = 0x01
USER = 0x02
OPERATOR = 0x03
ADMINISTRATOR = 0x04
# the session-less local interfaces only (IPMB, system interface, ...),
# and the system interface only: no session level has them
LOCAL_INTERFACE = 0x10
SYSTEM_INTERFACE = 0x11
NAMES = {NONE: 'none', CALLBACK: 'callback', USER: 'user',
         OPERATOR: 'operator', ADMINISTRATOR: 'administrator',
         LOCAL_INTERFACE: 'local interfaces only',
         SYSTEM_INTERFACE: 'system interface only'}

# the IPMI commands the library has no messages for, as (network function,
# command, group extension); the messages have their level as
# __privilege__
WITHOUT_MESSAGES: dict[tuple[int, int, int | None], int] = {
    # the IPMI commands without messages (Table G-1):
    # Get NetFn Support, Get Command Support, Get Command Sub-function
    # Support, Get Configurable Commands and Sub-functions, Set/Get Command
    # Enables, Set/Get Command Sub-function Enables, Get OEM NetFn IANA
    # Support
    **{(constants.NETFN_APP, cmd, None): USER
       for cmd in (0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x61, 0x63, 0x64)},
    (constants.NETFN_APP, 0x60, None): ADMINISTRATOR,
    (constants.NETFN_APP, 0x62, None): ADMINISTRATOR,
    # Get System GUID (before a session), Set/Get System Info Parameters,
    # Get AuthCode
    (constants.NETFN_APP, 0x37, None): NONE,
    (constants.NETFN_APP, 0x58, None): ADMINISTRATOR,
    (constants.NETFN_APP, 0x59, None): USER,
    (constants.NETFN_APP, 0x3f, None): OPERATOR,
    # the payload commands: Get Payload Activation Status, Get Payload
    # Instance Info, Set/Get User Payload Access, Get Channel Payload
    # Support and Version, Get Channel OEM Payload Info, Get Channel Cipher
    # Suites (before a session), Set Channel Security Keys, Get System
    # Interface Capabilities
    (constants.NETFN_APP, 0x4a, None): USER,
    (constants.NETFN_APP, 0x4b, None): USER,
    (constants.NETFN_APP, 0x4c, None): ADMINISTRATOR,
    (constants.NETFN_APP, 0x4d, None): OPERATOR,
    (constants.NETFN_APP, 0x4e, None): USER,
    (constants.NETFN_APP, 0x4f, None): USER,
    (constants.NETFN_APP, 0x50, None): USER,
    (constants.NETFN_APP, 0x56, None): ADMINISTRATOR,
    (constants.NETFN_APP, 0x57, None): USER,
    # Alert Immediate, PET Acknowledge (at any level)
    (constants.NETFN_SENSOR_EVENT, 0x16, None): ADMINISTRATOR,
    (constants.NETFN_SENSOR_EVENT, 0x17, None): NONE,
    # Suspend BMC ARPs, Get IP/UDP/RMCP Statistics
    (constants.NETFN_TRANSPORT, 0x03, None): ADMINISTRATOR,
    (constants.NETFN_TRANSPORT, 0x04, None): USER,
}


def required_privilege(netfn: int, cmd: int,
                       group: int | None = None) -> int | None:
    """Return the minimum privilege level of a command.

    Args:
        netfn: The network function of the request (or of its response).
        cmd: The command.
        group: The group extension of a group extension command (PICMG,
            VITA), ignored for the other network functions.

    Returns:
        The level, ``LOCAL_INTERFACE`` or ``SYSTEM_INTERFACE``; None for a
        command that is not listed.
    """
    netfn &= ~1
    if netfn != constants.NETFN_GROUP_EXTENSION:
        group = None
    request = DEFAULT_REGISTRY.registry.get((netfn, cmd, group))
    if request is not None:
        return request.__privilege__
    return WITHOUT_MESSAGES.get((netfn, cmd, group))
