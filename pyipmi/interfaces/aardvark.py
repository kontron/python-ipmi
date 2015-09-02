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
import array

from pyipmi import Session
from pyipmi.msgs import create_message, encode_message, decode_message
from pyipmi.errors import TimeoutError
from pyipmi.logger import log

try:
    import pyaardvark
except ImportError:
    pyaardvark = None

class ChecksumError(Exception):
    pass

class Aardvark:
    NAME = 'aardvark'

    def __init__(self, slave_address=0x20, port=0, serial_number=None,
            enable_i2c_pullups=True):
        if pyaardvark is None:
            raise RuntimeError('No pyaardvark module found. You can not '
                    'use this interface.')
        self.slave_address = slave_address
        self.timeout = 0.25 # 250 ms
        self.max_retries = 3
        self.next_sequence_number = 0

        self._dev = pyaardvark.open(port, serial_number)
        self._dev.enable_i2c_slave(self.slave_address >> 1)

    def enable_pullups(self, enabled):
        self._dev.i2c_pullups = enabled

    def enable_target_power(self, enabled):
        self._dev.target_power = enabled

    def raw_write(self, address, data):
        self._dev.i2c_master_write(address, data)

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

    def close_session(self, session):
        self._dev.close()

    def is_ipmc_accessible(self, target):
        rq_seq = self.next_sequence_number
        self._inc_sequence_number()
        rs_sa = target.ipmb_address
        rs_lun = 0
        net_fn = 6
        cmd_id = 1

        self._send_raw(rs_sa, rs_lun, rq_seq, net_fn, chr(cmd_id))
        rx_data = self._receive_raw(rs_sa, rs_lun, 0, rq_seq, net_fn, cmd_id)
        return True

    def _csum(self, data):
        csum = 0
        for b in data:
            csum += b
        return -csum % 256

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _encode_ipmb_msg_req(self, rs_sa, rs_lun, netfn, rq_sa, rq_lun, rq_seq,
            cmd_id, cmd_data):
        data = array.array('B')
        data.append(netfn << 2 | rs_lun)
        data.append(self._csum((rs_sa, data[0])))
        data.append(rq_sa)
        data.append(rq_seq << 2 | rq_lun)
        data.append(cmd_id)
        data.extend(cmd_data)
        data.append(self._csum(data[2:]))

        return data

    def _decode_ipmb_msg_rsp(self, addr, data):
        # shift i2c address by one
        addr = addr << 1

        # verify checksums
        if self._csum((addr, data[0], data[1])) != 0:
            raise ChecksumError()

        if self._csum(data[2:]) != 0:
            raise ChecksumError()

        # decode fields
        rs_sa = addr
        netfn = (data[0] >> 2) & 0x3f
        rq_lun = data[0] & 0x3
        rq_sa = data[2]
        rs_lun = data[3] & 0x3
        rq_seq = (data[3] >> 2) & 0x3f
        cmd_id = data[4]
        cmd_data = data[5:-1]
        return (rs_sa, netfn, rq_lun, rq_sa, rs_lun, rq_seq, cmd_id, cmd_data)

    def _rx_filter(self, rq_sa, rq_lun, rq_seq, rs_sa, rs_lun, netfn, cmd_id, rx_data):

        match = True

        if (self._csum((rq_sa, rx_data[0], rx_data[1])) != 0):
            log().warning('Header checksum failed')
            match = False
        if self._csum(rx_data[2:]) != 0:
            log().warning('payload checksum failed')
            match = False
        if rq_sa != self.slave_address:
            log().debug('slave address mismatch')
            match = False
        if rx_data[0] & ~3 != (netfn << 2) | 4:
            log().debug('NetFn mismatch')
            match = False
        if rx_data[2] != rs_sa:
            log().debug('target address mismatch')
            match = False
        if rx_data[0] & 3 != rq_lun:
            log().debug('request LUN mismatch')
            match = False
        if rx_data[3] & 3 != rs_lun & 3:
            log().debug('responder LUN mismatch')
            match = False
        if rx_data[3] >> 2 != rq_seq:
            log().debug('sequence number mismatch')
            match = False
        if rx_data[4] != cmd_id:
            log().debug('command id mismatch')
            match = False

        return match

    def _send_raw(self, rs_sa, rs_lun, rq_seq, netfn, raw_bytes):
        rq_sa = self.slave_address
        cmd_id = ord(raw_bytes[0])
        cmd_data =  [ord(c) for c in raw_bytes[1:]]

        tx_data = self._encode_ipmb_msg_req(rs_sa, rs_lun, netfn, rq_sa,
                        0, rq_seq, cmd_id, cmd_data)

        i2c_addr = rs_sa >> 1
        self._dev.i2c_master_write(i2c_addr, tx_data.tostring())
        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                ' '.join(['%02x' % b for b in tx_data]))

    def _receive_raw(self, rs_sa, rs_lun, rq_lun, rq_seq, netfn, cmd_id):
        start_time = time.time()
        rsp_received = False
        poll_returned_no_data = False
        while not rsp_received:
            timeout = self.timeout - (time.time() - start_time)

            if timeout <= 0 or poll_returned_no_data:
                raise TimeoutError()

            ret = self._dev.poll(int(timeout * 1000))

            # poll returns an empty list if no event is pending
            if not ret:
                poll_returned_no_data = True
                continue

            (i2c_addr, rx_data) = self._dev.i2c_slave_read()
            log().debug('I2C RX from %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % ord(c) for c in rx_data]))
            rx_data = array.array('B', rx_data)

            rq_sa = i2c_addr << 1
            rsp_received = self._rx_filter(rq_sa, rq_lun, rq_seq, rs_sa,
                                    rs_lun, netfn, cmd_id, rx_data)

        return rx_data

    def _send_and_receive_raw(self, target, rs_lun, netfn, raw_bytes):

        if hasattr(target, 'routing') and len(target.routing) > 1:
            raise RuntimeError('Bridging is not supported yet')

        rq_seq = self.next_sequence_number
        self._inc_sequence_number()
        rs_sa = target.ipmb_address
        cmd_id = ord(raw_bytes[0])

        retries = 0
        while retries < self.max_retries:
            try:
                self._send_raw(rs_sa, rs_lun, rq_seq, netfn, raw_bytes)
                rx_data = self._receive_raw(rs_sa, rs_lun, 0, rq_seq,
                            netfn, cmd_id)
                break
            except TimeoutError:
                log().warning('I2C transaction timed out'),
                pass

            retries += 1

        else:
            raise TimeoutError()

        return rx_data.tostring()

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        rx_data = self._send_and_receive_raw(target, lun, netfn, raw_bytes)
        return rx_data[5:-1]

    def send_and_receive(self, msg):
        """Sends an IPMI request message and waits for its response.

        `msg` is a IPMI Message containing both the request and response.
        """

        log().debug('IPMI Request [%s]', msg)

        rx_data = self._send_and_receive_raw(msg.target, msg.lun,
                    msg.netfn, chr(msg.cmdid) + encode_message(msg))

        msg = create_message(msg.cmdid, msg.netfn + 1)
        decode_message(msg, rx_data[5:-1])

        log().debug('IPMI Response [%s])', msg)

        return msg
