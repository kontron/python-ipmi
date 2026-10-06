# Copyright (c) 2014  Kontron Europe GmbH
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

"""Event receiver commands.

A controller sends its event messages to the event receiver, usually the
BMC, which logs them in the SEL. ``EVENT_ASSERTION`` and
``EVENT_DEASSERTION`` are the event directions of an event message.

The commands are the methods of :class:`Event`, which are available on
:class:`pyipmi.Ipmi`.

Example:
    Send the events of the target to the BMC (8-bit address 0x20)::

        ipmi.set_event_receiver(0x20 >> 1, 0)
"""

from __future__ import annotations

from .utils import check_completion_code
from .msgs import create_request_by_name
from .mixin import IpmiMixin

EVENT_ASSERTION = 0
EVENT_DEASSERTION = 1


class Event(IpmiMixin):
    """Event receiver commands, available on :class:`pyipmi.Ipmi`."""

    def set_event_receiver(self, ipmb_address: int, lun: int) -> None:
        """Set the event receiver of the target.

        Args:
            ipmb_address: The 7-bit IPMB address of the event receiver, e.g.
                0x10 for the BMC at the 8-bit address 0x20. An 8-bit
                address is truncated to 7 bits.
            lun: The LUN of the event receiver.

        Raises:
            CompletionCodeError: The target rejected the request.
        """
        req = create_request_by_name('SetEventReceiver')
        req.event_receiver.ipmb_i2c_slave_address = ipmb_address
        req.event_receiver.lun = lun
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_event_receiver(self) -> tuple[int, int]:
        """Get the event receiver of the target.

        Returns:
            A tuple of the 7-bit IPMB address and the LUN of the event
            receiver.
        """
        req = create_request_by_name('GetEventReceiver')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        ipmb_address = rsp.event_receiver.ipmb_i2c_slave_address
        lun = rsp.event_receiver.lun
        return (ipmb_address, lun)
