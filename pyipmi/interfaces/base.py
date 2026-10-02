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

from .. import Target
from ..logger import log
from ..msgs import create_message, encode_message, decode_message, Message
from ..session import Session


class Interface(object):
    """Base class of all interfaces.

    It defines the methods used by `pyipmi.Ipmi` and `pyipmi.Session`.
    An interface has to implement at least `send_and_receive_raw()`.
    """

    NAME: str | None = None

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def establish_session(self, session: Session) -> None:
        pass

    def close_session(self) -> None:
        pass

    def is_ipmc_accessible(self, target: Target) -> bool:
        raise NotImplementedError()

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Interface function to send and receive raw message.

        target: IPMI target
        lun: logical unit number
        netfn: network function
        raw_bytes: RAW bytes as bytestring, starting with the command id

        Returns the IPMI message response bytestring, starting with the
        completion code.
        """
        raise NotImplementedError()

    def send_and_receive(self, req: Message) -> Message:
        """Interface function to send and receive an IPMI message.

        req: IPMI message request

        Returns the IPMI message response.
        """
        log().debug('IPMI Request [%s]', req)

        raw_bytes = bytes((req.cmdid,)) + encode_message(req)
        rx_data = self.send_and_receive_raw(req.target, req.lun, req.netfn,
                                            raw_bytes)
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)

        log().debug('IPMI Response [%s])', rsp)

        return rsp
