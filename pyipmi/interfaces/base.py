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

"""The base class of the interfaces.

:class:`Interface` defines the methods an interface provides to
:class:`pyipmi.Ipmi` and :class:`pyipmi.session.Session`. A new interface
is derived from it and implements at least :meth:`send_and_receive_raw`.
"""

from __future__ import annotations

import logging
import warnings

from .. import Target
from ..msgs import create_message, encode_message, decode_message, Message
from ..session import Session

logger = logging.getLogger(__name__)


class Interface:
    """Base class of all interfaces.

    It defines the methods used by :class:`pyipmi.Ipmi` and
    :class:`pyipmi.session.Session`. An interface has to implement at
    least :meth:`send_and_receive_raw`. The other methods do nothing by
    default, except :meth:`is_target_accessible`, which is not
    implemented, and :meth:`send_and_receive`, which encodes the request
    and sends it with :meth:`send_and_receive_raw`.

    Attributes:
        NAME: The name of the interface for
            :func:`pyipmi.interfaces.create_interface`.
        MAX_REQUEST_DATA_SIZE: The maximum request data length of a
            message sent directly (not bridged) by the interface, None
            for the IPMB default.
    """

    NAME: str | None = None

    # maximum request data length of a message sent directly (not bridged)
    # by the interface, None for the IPMB default
    MAX_REQUEST_DATA_SIZE: int | None = None

    def open(self) -> None:
        """Open the interface.

        Called by :meth:`pyipmi.Ipmi.open`. Does nothing by default.
        """

    def close(self) -> None:
        """Close the interface.

        Called by :meth:`pyipmi.Ipmi.close`. Does nothing by default.
        """

    def establish_session(self, session: Session) -> None:
        """Establish the session.

        Called by :meth:`pyipmi.session.Session.establish`. Does nothing
        by default, for interfaces without a session.

        Args:
            session: The session with the host and the credentials.
        """

    def close_session(self) -> None:
        """Close the session.

        Called by :meth:`pyipmi.session.Session.close`. Does nothing by
        default.
        """

    def is_target_accessible(self, target: Target) -> bool:
        """Check if the target answers.

        An interface implements it, if it supports the check. An interface
        which implements only the deprecated :meth:`is_ipmc_accessible` is
        still called by it, with a DeprecationWarning.

        Args:
            target: The target.

        Returns:
            True if the target answers.

        Raises:
            NotImplementedError: The interface does not implement it.
        """
        # an interface which implements only the old name
        if type(self).is_ipmc_accessible is not Interface.is_ipmc_accessible:
            warnings.warn('is_ipmc_accessible is deprecated, implement '
                          'is_target_accessible', DeprecationWarning,
                          stacklevel=2)
            return self.is_ipmc_accessible(target)
        raise NotImplementedError()

    def is_ipmc_accessible(self, target: Target) -> bool:
        """Deprecated, the old name of :meth:`is_target_accessible`."""
        warnings.warn('is_ipmc_accessible is deprecated, use '
                      'is_target_accessible', DeprecationWarning,
                      stacklevel=2)
        return self.is_target_accessible(target)

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Send a raw request to the target and return the raw response.

        Every interface has to implement it.

        Args:
            target: The target of the request.
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code.

        Raises:
            NotImplementedError: The interface does not implement it.
        """
        raise NotImplementedError()

    def send_and_receive(self, req: Message) -> Message:
        """Send a request message and return the response message.

        The request is encoded and sent with :meth:`send_and_receive_raw`
        to the target, LUN and network function of the request, and the
        response is decoded. An interface may override it.

        Args:
            req: The request message.

        Returns:
            The response message. Its completion code is not checked.
        """
        logger.debug('IPMI Request [%s]', req)

        raw_bytes = bytes((req.cmdid,)) + encode_message(req)
        rx_data = self.send_and_receive_raw(req.target, req.lun, req.netfn,
                                            raw_bytes)
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)

        logger.debug('IPMI Response [%s]', rsp)

        return rsp
