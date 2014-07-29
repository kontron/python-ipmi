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

import time

import bmc
import chassis
import event
import fru
import functools
import hpm
import lan
import picmg
import sdr
import sel
import sensor

from pyipmi.errors import TimeoutError, CompletionCodeError

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

class Requester:
    '''The Requester class represents an IPMI device which initiates a
    request/response message exchange.
    '''

    def __init__(self, ipmb_address):
        self.ipmb_address = ipmb_address

class NullRequester:
    '''The NullRequester is used for interfaces which doesn't require a
    valid requester.
    '''

    @property
    def ipmb_address():
        raise AssertionError('NullRequester does not provide an IPMB address')

class Target:
    '''The Target class represents an IPMI target.'''
    class Routing:
        def __init__(self, address, bridge_channel):
            self.address = address
            self.bridge_channel = bridge_channel

    def __init__(self, ipmb_address):
        self.ipmb_address = ipmb_address

    def set_routing_information(self, rinfo):
        """Set the path over which a target is reachable.

        The path is given as a list of tuples in the form (address,
        bridge_channel).
        """

        self.routing = [ self.Routing(*r) for r in rinfo ]

class Session:
    AUTH_TYPE_NONE        = 0x00
    AUTH_TYPE_MD2         = 0x01
    AUTH_TYPE_MD5         = 0x02
    AUTH_TYPE_PASSWORD    = 0x04
    AUTH_TYPE_OEM         = 0x05

    def __init__(self):
        self.auth_type = self.AUTH_TYPE_NONE
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

    def set_auth_type_user(self, username, password):
        self.auth_type = self.AUTH_TYPE_PASSWORD
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
        if (hasattr(bmc.Bmc, '__init__')):
            bmc.Bmc.__init__(self)
        if (hasattr(chassis.Chassis, '__init__')):
            chassis.Chassis.__init__(self)
        if (hasattr(fru.Fru, '__init__')):
            fru.Fru.__init__(self)
        if (hasattr(picmg.Picmg, '__init__')):
            picmg.Picmg.__init__(self)
        if (hasattr(hpm.Hpm, '__init__')):
            hpm.Hpm.__init__(self)
        if (hasattr(sdr.Sdr, '__init__')):
            sdr.Sdr.__init__(self)
        if (hasattr(sensor.Sensor, '__init__')):
            sensor.Sensor.__init__(self)
        if (hasattr(event.Event, '__init__')):
            event.Event.__init__(self)
        if (hasattr(sel.Sel, '__init__')):
            sel.Sel.__init__(self)
        if (hasattr(lan.Lan, '__init__')):
            lan.Lan.__init__(self)

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

    def send_message(self, msg):
        msg.target = self.target
        msg.requester = self.requester

        retry = 3
        while True:
            retry -= 1
            try:
                ret = self.interface.send_and_receive(msg)
                break
            except CompletionCodeError, e:
                if e.cc == msgs.constants.CC_NODE_BUSY:
                    retry -= 1
                    continue

        return ret

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



