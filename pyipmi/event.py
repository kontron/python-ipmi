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
                0x10 for the BMC at the 8-bit address 0x20.
            lun: The LUN of the event receiver (0 - 3).

        Raises:
            ValueError: The address is not a 7-bit address or the LUN is out
                of range.
            CompletionCodeError: The target rejected the request.
        """
        if not 0 <= ipmb_address <= 0x7f:
            raise ValueError(f'event receiver address 0x{ipmb_address:x} is '
                             'not a 7-bit '
                             'IPMB address')
        if not 0 <= lun <= 3:
            raise ValueError(f'event receiver LUN {lun:d} is out of range')
        req = create_request_by_name('SetEventReceiver')
        req.event_receiver.ipmb_i2c_slave_address = ipmb_address
        req.event_receiver.lun = lun
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def disable_event_message_generation(self) -> None:
        """Disable the event message generation of the target.

        The event receiver address is set to 0xFF, which disables the
        event messages. :meth:`get_event_receiver` returns the address
        0x7F then.

        Raises:
            CompletionCodeError: The target rejected the request.
        """
        req = create_request_by_name('SetEventReceiver')
        # the address byte 0xFF includes its reserved bit 0
        req.event_receiver._value = 0xff
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
