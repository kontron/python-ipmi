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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from __future__ import absolute_import
from builtins import object

import time
import sys

from . import bmc
from . import chassis
from . import event
from . import fru
#import functools
from . import hpm
from . import lan
from . import picmg
from . import sdr
from . import sel
from . import sensor
from . import msgs

from .errors import TimeoutError, CompletionCodeError
from .msgs.registry import create_request_by_name
from .utils import check_completion_code

try:
    from version import __version__
except ImportError:
    __version__ = 'dev'

def create_connection(interface):
    session = Session()
    session.interface = interface
    ipmi = Ipmi()
    ipmi.interface = interface
    ipmi.session = session
    ipmi.requester = NullRequester()
    return ipmi

class Requester(object):
    '''The Requester class represents an IPMI device which initiates a
    request/response message exchange.
    '''

    def __init__(self, ipmb_address):
        self.ipmb_address = ipmb_address

class NullRequester(object):
    '''The NullRequester is used for interfaces which doesn't require a
    valid requester.
    '''

    @property
    def ipmb_address(self):
        raise AssertionError('NullRequester does not provide an IPMB address')


class Target(object):
    def __init__(self, ipmb_address, routing=None):
        """
        `ipmb_address` is the IPMB target address
        `routing` is the bridging information used to build send message
        commands.
        """
        self.ipmb_address = ipmb_address
        if routing:
            self.set_routing(routing)

    '''The Target class represents an IPMI target.'''
    class Routing(object):
        def __init__(self, address, bridge_channel):
            self.address = address
            self.bridge_channel = bridge_channel


    def set_routing_information(self, rinfo):
        self.set_routing(self, rinfo)

    def set_routing(self, rinfo):
        """Set the path over which a target is reachable.

        The path is given as a list of tuples in the form (address,
        bridge_channel).
        """

        self.routing = [ self.Routing(*r) for r in rinfo ]


class Session(object):
    AUTH_TYPE_NONE        = 0x00
    AUTH_TYPE_MD2         = 0x01
    AUTH_TYPE_MD5         = 0x02
    AUTH_TYPE_PASSWORD    = 0x04
    AUTH_TYPE_OEM         = 0x05

    def __init__(self):
        self.set_auth_type(self.AUTH_TYPE_NONE)
        self.established = False

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def set_session_type_rmcp(self, host, port=623):
        self._rmcp_host = host
        self._rmcp_port = port

    def set_session_type_serial(self, port, baudrate):
        self._serial_port = port
        self._serial_baudrate = baudrate

    def set_auth_type(self, auth_type):
        self.auth_type = auth_type

    def set_auth_type_user(self, username, password):
        self.set_auth_type(self.AUTH_TYPE_PASSWORD)
        self._auth_username = username
        self._auth_password = password

    def establish(self):
        if hasattr(self.interface, 'establish_session'):
            self.interface.establish_session(self)

    def close(self):
        if hasattr(self.interface, 'close_session'):
            self.interface.close_session(self)

    def rmcp_ping(self):
        if hasattr(self.interface, 'rmcp_ping'):
            self.interface.rmcp_ping()

    interface = property(_get_interface, _set_interface)

class Ipmi(bmc.Bmc, chassis.Chassis, fru.Fru, picmg.Picmg, hpm.Hpm,
        sdr.Sdr, sensor.Sensor, event.Event, sel.Sel, lan.Lan):

    def __init__(self):
        for base in Ipmi.__bases__:
            base.__init__(self)

    def is_ipmc_accessible(self):
        return self.interface.is_ipmc_accessible(self.target)

    def wait_until_ipmb_is_accessible(self, timeout, interval=0.25):
        start_time = time.time()
        while time.time() < start_time + (timeout):
            try:
                self.is_ipmc_accessible()
            except TimeoutError:
                time.sleep(interval)

        self.is_ipmc_accessible()

    def send_message(self, req):
        req.target = self.target
        req.requester = self.requester

        retry = 3
        while True:
            retry -= 1
            try:
                rsp = self.interface.send_and_receive(req)
                break
            except CompletionCodeError as e:
                if e.cc == msgs.constants.CC_NODE_BUSY:
                    retry -= 1
                    continue

        return rsp

    def send_message_with_name(self, name, *args, **kwargs):
        req = create_request_by_name(name)

        for k, v in kwargs.items():
            setattr(req, k, v)

        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp

    def raw_command(self, lun, netfn, raw_bytes):
        return self.interface.send_and_receive_raw(self.target, lun, netfn,
                raw_bytes)

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _get_session(self):
        try:
            return self._session
        except AttributeError:
            raise RuntimeError('No IPMI session has been set')

    def _get_target(self):
        try:
            return self._target
        except AttributeError:
            raise RuntimeError('No IPMI target has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def _set_session(self, session):
        self._session = session

    def _set_target(self, target):
        self._target = target

    target = property(_get_target, _set_target)
    interface = property(_get_interface, _set_interface)
    session = property(_get_session, _set_session)