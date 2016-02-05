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
import messaging

from pyipmi.session import Session
from pyipmi.errors import TimeoutError, CompletionCodeError
from pyipmi.msgs.registry import create_request_by_name
from pyipmi.utils import check_completion_code

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
    return ipmi

class Target(object):
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

        Example:  slave = 0x81, target = 0x72
                  routing = [(0x20,0),(0x82,7)]


                       +-------------------+             +--------+
                       |       +-----------|             |        |
                       | ShMC  |CM         |             |        |
            channel=0  |       |           |  channel=7  |        |
        81 ------------| 0x20  |0x82  0x20 |-------------| 0x72   |
                       |       |           |             |        |
                       |       +-----------|             |        |
                       +-------------------+             +--------+


        """

        self.routing = [ self.Routing(*r) for r in rinfo ]

    def __str__(self):
        s = 'Target:\n'
        s += '  ipmb: 0x%02x\n' % self.ipmb_address

        if hasattr(self, 'routing'):
            for r in self.routing:
                s += ' r: 0x%02x 0x%x\n' % (r.address, r.bridge_channel)
        return s




class Ipmi(bmc.Bmc, chassis.Chassis, fru.Fru, picmg.Picmg, hpm.Hpm,
        sdr.Sdr, sensor.Sensor, event.Event, sel.Sel, lan.Lan,
        messaging.Messaging):

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

    def send_message(self, req, retry=3):
        req.target = self.target

        for islast in map(lambda x: x == retry-1, range(retry)):
            try:
                rsp = self.interface.send_and_receive(req)
                break
            except CompletionCodeError, e:
                if islast or e.cc != msgs.constants.CC_NODE_BUSY:
                    raise e
        return rsp

    def send_message_with_name(self, name, *args, **kwargs):
        req = create_request_by_name(name)

        for k, v in kwargs.iteritems():
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
