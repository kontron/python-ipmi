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

"""A pure Python IPMI library.

A connection to an IPMI device is an :class:`Ipmi` object, created by
:func:`create_connection` for an interface (see
:func:`pyipmi.interfaces.create_interface`).
The connection sends the requests to its :class:`Target`, the BMC or a
controller behind it, which is reached over the :class:`Routing` hops of
the target. The IPMI commands are the methods of :class:`Ipmi`, which
inherits them from the command groups of the modules, e.g.
:mod:`pyipmi.bmc` and :mod:`pyipmi.sdr`.

Example:
    Print the device ID of a BMC over RMCP+::

        import pyipmi
        import pyipmi.interfaces

        interface = pyipmi.interfaces.create_interface('rmcpplus')
        ipmi = pyipmi.create_connection(interface)
        ipmi.session.set_session_type_rmcp('10.0.0.1', port=623)
        ipmi.session.set_auth_type_user('admin', 'admin')
        ipmi.target = pyipmi.Target(ipmb_address=0x20)

        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import time
import ast
import warnings
from typing import Any, Literal

from . import bmc
from . import chassis
from . import dcmi
from . import event
from . import fru
from . import hpm
from . import lan
from . import logger  # noqa: F401 - installs the NullHandler
from . import messaging
from . import picmg
from . import sdr
from . import sel
from . import sensor
from . import vita
from . import msgs

from .errors import IpmiTimeoutError, CompletionCodeError, RetryError
from .msgs import Message
from .msgs.registry import create_request_by_name
from .session import Session
from .utils import check_rsp_completion_code, is_string

try:
    from .version import __version__
except ImportError:
    __version__ = 'dev'


def create_connection(interface: Any) -> Ipmi:
    """Create a connection for an interface.

    The connection gets a new :class:`pyipmi.session.Session` for the
    interface. The target is not set, assign it to :attr:`Ipmi.target`
    before sending requests.

    Args:
        interface: The interface, e.g. created by
            :func:`pyipmi.interfaces.create_interface`.

    Returns:
        The connection.
    """
    session = Session()
    session.interface = interface
    return Ipmi(interface=interface, session=session)


class Requester:
    """The Requester class.

    This represents an IPMI device which initiates a request/response
    message exchange.
    """

    def __init__(self, ipmb_address: int) -> None:
        self.ipmb_address = ipmb_address


class NullRequester:
    """The NullRequester class.

    This requester is used for interfaces which doesn't require a valid
    requester.
    """

    @property
    def ipmb_address(self) -> int:
        raise AssertionError('NullRequester does not provide an IPMB address')


class Routing:
    """One hop of the path to a target, see :meth:`Target.set_routing`."""

    def __init__(self, rq_sa: int, rs_sa: int, channel: int | None) -> None:
        """Initialize the hop.

        Args:
            rq_sa: The requester slave address.
            rs_sa: The responder slave address.
            channel: The channel of the bridge to the next hop, None for
                the last hop.
        """
        self.rq_sa = rq_sa
        self.rs_sa = rs_sa
        self.channel = channel

    def __str__(self) -> str:
        s = 'Routing: Rq: %s Rs: %s Ch: %s' \
                % (self.rq_sa, self.rs_sa, self.channel)
        return s


class Target:
    """The Target class represents an IPMI target."""

    routing: list[Routing] | None = None
    ipmb_address: int | None = None

    def __init__(self, ipmb_address: int | None = None,
                 routing: str | list[tuple] | None = None) -> None:
        """Initialize the target.

        Args:
            ipmb_address: The IPMB address of the target, e.g. 0x20 for
                the BMC.
            routing: The path over which the target is reachable, used to
                build the bridged Send Message requests, see
                :meth:`set_routing`.
        """
        if ipmb_address:
            self.ipmb_address = ipmb_address

        if routing:
            self.set_routing(routing)

    def set_routing_information(self, routing: str | list[tuple]) -> None:
        """Set the path over which a target is reachable.

        An alias of :meth:`set_routing`.
        """
        self.set_routing(routing)

    def set_routing(self, routing: str | list[tuple]) -> None:
        """Set the path over which a target is reachable.

        Each hop of the path is a tuple ``(rq_sa, rs_sa, channel)``: the
        requester address, the responder address and the channel of the
        bridge to the next hop. The channel of the last hop is None.

        Args:
            routing: The list of hops, or its string representation as
                given on the command line.

        Example #1, access to an ATCA blade in a chassis (slave 0x81,
        target 0x82)::

            routing = [(0x81, 0x20, 0), (0x20, 0x82, None)]

        Example #2, access to an AMC in a uTCA chassis (slave 0x81,
        target 0x72)::

            routing = [(0x81, 0x20, 0), (0x20, 0x82, 7), (0x20, 0x72, None)]

                             uTCA - MCH                        AMC
                           .-------------------.             .--------.
                           |       .-----------|             |        |
                           | ShMC  | CM        |             | MMC    |
                channel=0  |       |           |  channel=7  |        |
            81 ------------| 0x20  |0x82  0x20 |-------------| 0x72   |
                           |       |           |             |        |
                           |       |           |             |        |
                           |       `-----------|             |        |
                           `-------------------´             `--------´
              `------------´     `---´        `---------------´

        Example #3, access to an AMC in an ATCA AMC carrier (slave 0x81,
        target 0x72)::

            routing = [(0x81, 0x20, 0), (0x20, 0x8e, 7), (0x20, 0x80, None)]
        """
        if is_string(routing):
            # if type(routing) in [unicode, str]:
            routing = ast.literal_eval(routing)
        self.routing = [Routing(*route) for route in routing]

    def __str__(self) -> str:
        if self.ipmb_address is None:
            string = 'Target: IPMB: none\n'
        else:
            string = 'Target: IPMB: 0x%02x\n' % self.ipmb_address
        if self.routing:
            for route in self.routing:
                string += ' %s\n' % route
        return string


class Ipmi(bmc.Bmc, chassis.Chassis, dcmi.Dcmi, fru.Fru, picmg.Picmg, hpm.Hpm,
           sdr.Sdr, sensor.Sensor, event.Event, sel.Sel, lan.Lan,
           messaging.Messaging, vita.Vita):
    """A connection to an IPMI device.

    The IPMI commands are the methods of this class, which it inherits
    from the command groups, e.g. :meth:`get_device_id` from the one of
    :mod:`pyipmi.bmc`. The requests are sent over the interface to
    the target.

    The connection is a context manager, which opens the interface and
    establishes the session on entry and closes them on exit. Set up the
    session before, see the example of :mod:`pyipmi`.
    """

    def __init__(self, interface: Any = None, target: Target | None = None,
                 session: Session | None = None,
                 requester: Any = None) -> None:
        """Initialize the connection.

        Args:
            interface: The interface the requests are sent over.
            target: The target of the requests.
            session: The session, a new one if not given. The interface
                of the session is set to ``interface``.
            requester: The requester of the requests, needed by interfaces
                that send the requests on the IPMB, a
                :class:`NullRequester` if not given.
        """
        self._interface = interface

        # we need a session, set if not passed
        if session is None:
            session = Session()
        self._session = session
        # session needs an interface
        self._session.interface = interface

        self._target = target
        self.requester = requester if requester is not None else NullRequester()

        for base in Ipmi.__bases__:
            base.__init__(self)  # type: ignore[misc]

    def __enter__(self) -> Ipmi:
        self.open()
        return self

    def __exit__(self, exception_type: Any, exception_value: Any,
                 traceback: Any) -> Literal[False]:
        self.close()
        return False

    def open(self) -> None:
        """Open the interface and establish the session."""
        self.interface.open()
        if self.session is not None:
            self.session.establish()

    def close(self) -> None:
        """Close the session and the interface."""
        if self.session is not None:
            self.session.close()
        self.interface.close()

    def is_target_accessible(self) -> bool:
        """Check if the target answers.

        Returns:
            True if the target answers. Depending on the interface, False
            is returned or an exception is raised if it does not.
        """
        return self.interface.is_target_accessible(self.target)

    def is_ipmc_accessible(self) -> bool:
        """Deprecated, the old name of :meth:`is_target_accessible`."""
        warnings.warn('is_ipmc_accessible is deprecated, use '
                      'is_target_accessible', DeprecationWarning,
                      stacklevel=2)
        return self.is_target_accessible()

    def wait_until_target_is_accessible(self, timeout: float,
                                        interval: float = 0.25) -> None:
        """Wait until the target is accessible.

        Args:
            timeout: The time to wait in seconds.
            interval: The time between the checks in seconds.

        Raises:
            IpmiTimeoutError: The target is not accessible after the
                timeout, if the interface raises it, see
                :meth:`is_target_accessible`.
        """
        start_time = time.time()
        while time.time() < start_time + (timeout):
            try:
                if self.is_target_accessible():
                    return
            except IpmiTimeoutError:
                pass
            time.sleep(interval)

        self.is_target_accessible()

    def wait_until_ipmb_is_accessible(self, timeout: float,
                                      interval: float = 0.25) -> None:
        """Deprecated, use :meth:`wait_until_target_is_accessible`."""
        warnings.warn('wait_until_ipmb_is_accessible is deprecated, use '
                      'wait_until_target_is_accessible', DeprecationWarning,
                      stacklevel=2)
        self.wait_until_target_is_accessible(timeout, interval)

    def send_message(self, req: Message, retry: int = 3) -> Message:
        """Send a request to the target and return the response.

        The request is sent again if the target is busy. The completion
        code of the response is not checked.

        Args:
            req: The request message.
            retry: The number of tries.

        Returns:
            The response message.

        Raises:
            RetryError: The target is still busy after ``retry`` tries.
            CompletionCodeError: The interface failed with another
                completion code, e.g. of a bridged Send Message request.
        """
        req.target = self.target
        req.requester = self.requester
        rsp = None

        while retry > 0:
            retry -= 1
            try:
                rsp = self.interface.send_and_receive(req)
                break
            except CompletionCodeError as e:
                if e.cc == msgs.constants.CC_NODE_BUSY:
                    continue
                raise
        else:
            raise RetryError()

        return rsp

    def send_message_by_name(self, name: str, *args: Any,
                             **kwargs: Any) -> Message:
        """Send a request by its name and return the response.

        Args:
            name: The name of the request, e.g. ``'GetDeviceId'``.
            *args: Not used.
            **kwargs: The fields of the request, set as attributes.

        Returns:
            The response message.

        Raises:
            CompletionCodeError: The completion code of the response is
                not successful.
        """
        req = create_request_by_name(name)

        for key, value in kwargs.items():
            setattr(req, key, value)

        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)
        return rsp

    def send_message_with_name(self, name: str, *args: Any,
                               **kwargs: Any) -> Message:
        """Deprecated, the old name of :meth:`send_message_by_name`."""
        warnings.warn('send_message_with_name is deprecated, use '
                      'send_message_by_name', DeprecationWarning,
                      stacklevel=2)
        return self.send_message_by_name(name, *args, **kwargs)

    def send_raw(self, lun: int, netfn: int, raw_bytes: bytes) -> bytes:
        """Send a raw request to the target and return the raw response.

        Args:
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code.
        """
        return self.interface.send_and_receive_raw(self.target, lun, netfn,
                                                   raw_bytes)

    def raw_command(self, lun: int, netfn: int, raw_bytes: bytes) -> bytes:
        """Deprecated, the old name of :meth:`send_raw`."""
        warnings.warn('raw_command is deprecated, use send_raw',
                      DeprecationWarning, stacklevel=2)
        return self.send_raw(lun, netfn, raw_bytes)

    @property
    def interface(self) -> Any:
        """The interface the requests are sent over."""
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set') from None

    @interface.setter
    def interface(self, interface: Any) -> None:
        self._interface = interface

    @property
    def session(self) -> Session:
        """The session of the connection."""
        try:
            return self._session
        except AttributeError:
            raise RuntimeError('No IPMI session has been set') from None

    @session.setter
    def session(self, session: Session) -> None:
        self._session = session

    @property
    def target(self) -> Target | None:
        """The target of the requests."""
        try:
            return self._target
        except AttributeError:
            raise RuntimeError('No IPMI target has been set') from None

    @target.setter
    def target(self, target: Target | None) -> None:
        self._target = target
