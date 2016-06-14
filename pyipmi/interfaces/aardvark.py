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

from builtins import object

import time
import array

from ..msgs import create_message, encode_message, decode_message
from ..errors import TimeoutError
from ..logger import log
from ..interfaces.ipmb import IpmbHeader, checksum

try:
    import pyaardvark
except ImportError:
    pyaardvark = None


class Aardvark(object):
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
        header = IpmbHeader()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmd_id = ord(1)
        raw_data = []

        self._send_raw(header, raw_data)
        rx_data = self._receive_raw(header)
        return True

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _encode_ipmb_msg_req(self, header, cmd_data):
        data = header.encode()
        data.extend(cmd_data)
        data.append(checksum(data[2:]))

        return data

    def _rx_filter(self, header, rx_data):

        log().debug('[%s]' % ' '.join(['%02x' % b for b in rx_data]))

        checks = [
            (checksum(rx_data[0:3]), 0, 'Header checksum failed'),
            (checksum(rx_data[3:]), 0, 'payload checksum failed'),
            (rx_data[0], header.rq_sa, 'slave address mismatch'),
            (rx_data[1] & ~3, header.netfn << 2 | 4, 'NetFn mismatch'),
            (rx_data[3], header.rs_sa, 'target address mismatch'),
            (rx_data[1] & 3, header.rq_lun, 'request LUN mismatch'),
            (rx_data[4] & 3, header.rs_lun & 3, 'responder LUN mismatch'),
            (rx_data[4] >> 2, header.rq_seq, 'sequence number mismatch'),
            (rx_data[5], header.cmd_id, 'command id mismatch'),
        ]

        match = True

        for left, right, msg in checks:
            if left != right:
                log().debug('%s (%02Xh != %02Xh)' % (msg, left, right))
                match = False

        return match

    def _send_raw(self, header, raw_bytes):

        cmd_data =  [ord(c) for c in raw_bytes]
        tx_data = self._encode_ipmb_msg_req(header, cmd_data)

        i2c_addr = header.rs_sa >> 1
        self._dev.i2c_master_write(i2c_addr, tx_data.tostring())
        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                ' '.join(['%02x' % b for b in tx_data]))

    def _receive_raw(self, header):
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
            log().debug('I2C RX from %02Xh [%s]', i2c_addr << 1,
                    ' '.join(['%02x' % ord(c) for c in rx_data]))

            rx_data = array.array('B', rx_data)
            rq_sa = array.array('B', [i2c_addr << 1,])

            rsp_received = self._rx_filter(header, rq_sa + rx_data)

        return rx_data

    def _send_and_receive(self, target, lun, netfn, cmdid, payload):
        self._inc_sequence_number()

        # assemble IPMB header
        header = IpmbHeader()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmd_id = cmdid

        retries = 0
        while retries < self.max_retries:
            try:
                self._send_raw(header, payload)
                rx_data = self._receive_raw(header)
                break
            except TimeoutError:
                log().warning('I2C transaction timed out'),
                pass

            retries += 1

        else:
            raise TimeoutError()

        return rx_data.tostring()[5:-1]

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        return self._send_and_receive(target, lun, netfn, ord(raw_bytes[0]),
                raw_bytes[1:])

    def send_and_receive(self, msg):
        """Sends an IPMI request message and waits for its response.

        `msg` is a IPMI Message containing both the request and response.
        """

        log().debug('IPMI Request [%s]', msg)

        rx_data = self._send_and_receive(msg.target, msg.lun, msg.netfn,
                msg.cmdid, encode_message(msg))
        msg = create_message(msg.cmdid, msg.netfn + 1)
        decode_message(msg, rx_data)

        log().debug('IPMI Response [%s])', msg)

        return msg
