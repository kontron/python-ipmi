# -*- coding: utf-8 -*-
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
import ast

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
    def __init__(self, ipmb_address, routing=None):
        """
        `ipmb_address` is the IPMB target address
        `routing` is the bridging information used to build send message
        commands.
        """

        self.routing = None
        self.ipmb_address = ipmb_address
        if routing:
            self.set_routing(routing)

    '''The Target class represents an IPMI target.'''
    class Routing:
        def __init__(self, rq_sa, rs_sa, channel):
            self.rq_sa = rq_sa
            self.rs_sa = rs_sa
            self.channel = channel

        def __str__(self):
            s = 'Routing: Rq: %s Rs: %s Ch: %s' \
                    % (self.rq_sa, self.rs_sa, self.channel)
            return s

    def set_routing_information(self, routing):
        self.set_routing(routing)

    def set_routing(self, routing):
        """Set the path over which a target is reachable.

        The path is given as a list of tuples in the form (address,
        bridge_channel).

        Example #1: access to an ATCA blade in a chassis
              slave = 0x81, target = 0x82
              rotuing = [(0x81,0x20,0),(0x20,0x82,7)]

        Example #2: access to an AMC in a uTCA chassis
              slave = 0x81, target = 0x72
              routing = [(0x81,0x20,0),(0x20,0x82,7),(0x20,0x72,None)]


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
         \              /   \     /      \                 /
          `------------´     `---´        `---------------´

        Example #3: access to an AMC in a ATCA AMC carrier

        slave = 0x81, target = 0x72
        routing = [(0x81,0x20,0),(0x20,0x8e,7),(0x20,0x80,None)]

        """
        if type(routing) in  [unicode, str]:
            routing = ast.literal_eval(routing)

        self.routing = [ self.Routing(*r) for r in routing ]

    def __str__(self):
        s = 'Target: IPMB: 0x%02x\n' % self.ipmb_address
        if self.routing:
            for r in self.routing:
                s += ' %s\n' % r
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
