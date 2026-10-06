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

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Target
    from .bmc import DeviceId
    from .messaging import ChannelInfo
    from .msgs import Message


class IpmiMixin:
    """Base class of the command groups the `Ipmi` class is composed of.

    The command groups use the messaging API of the `Ipmi` class and the
    commands of other command groups. These are declared here for static
    type checking only.
    """

    if TYPE_CHECKING:
        @property
        def interface(self) -> Any: ...

        @property
        def target(self) -> Target | None: ...

        def send_message(self, req: Message, retry: int = 3) -> Message: ...

        def send_message_with_name(self, name: str, *args: Any,
                                   **kwargs: Any) -> Message: ...

        # bmc.Bmc
        def get_device_id(self) -> DeviceId: ...

        # messaging.Messaging
        def get_channel_info(self, channel: int) -> ChannelInfo: ...
