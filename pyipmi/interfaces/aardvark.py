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

    def __init__(self, port=0, serial_number=None):
        if pyaardvark is None:
            raise RuntimeError('No pyaardvark module found. You can not '
                    'use this interface.')

        self.slave_address = 0x20
        self.timeout = 0.25 # 250 ms
        self.max_retries = 3
        self.next_sequence_number = 0

        self._dev = pyaardvark.open(port, serial_number)
        self._dev.enable_i2c = True
        self._dev.i2c_pullups = True
        self._dev.i2c_slave_enable(self.slave_address >> 1)

    def enable_pullups(self, enabled):
        self._dev.i2c_enable_pullups(enabled)

    def enable_target_power(self, enabled):
        self._dev.enable_target_power(enabled)

    def raw_write(self, address, data):
        self._dev.i2c_master_write(address, data)

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

    def close_session(self, session):
        self._dev.close()

    def _csum(self, data):
        csum = 0
        for b in data:
            csum += b
        return -csum % 256

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _encode_ipmb_msg(self, rs_sa, netfn, rq_lun, rq_sa, rs_lun, rq_seq,
            cmd_id, cmd_data):
        data = array.array('B')
        data.append(netfn << 2 | rq_lun)
        data.append(self._csum((rs_sa, data[0])))
        data.append(rq_sa)
        data.append(rq_seq << 2 | rs_lun)
        data.append(cmd_id)
        data.extend(cmd_data)
        data.append(self._csum(data[2:]))

        return data

    def _decode_ipmb_msg(self, addr, data):
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

    def _send_and_receive_raw(self, target, lun, netfn, raw_bytes):

        if hasattr(target, 'routing') and len(target.routing) > 1:
            raise RuntimeError('Bridging is not supported yet')

        tx_data = array.array('B')
        tx_data.append(netfn << 2 | lun)
        tx_data.append(self._csum((target.ipmb_address, tx_data[0])))
        tx_data.append(self.slave_address)
        tx_data.append(self.next_sequence_number << 2)
        tx_data.extend([ord(c) for c in raw_bytes])
        tx_data.append(self._csum(tx_data[2:]))

        addr = target.ipmb_address >> 1
        self._dev.i2c_master_write(addr, tx_data.tostring())
        log().debug('I2C TX to %02Xh [%s]', addr,
                ' '.join(['%02x' % b for b in tx_data]))

        # receive messages
        start_time = time.time()
        timeout = self.timeout - (time.time() - start_time)
        rsp_received = False
        while not rsp_received and timeout > 0:
            ret = self._dev.poll(int(timeout * 1000))
            if ret == pyaardvark.POLL_NO_DATA:
                raise TimeoutError()

            (addr, rx_data) = self._dev.i2c_slave_read()
            log().debug('I2C RX from %02Xh [%s]', addr,
                    ' '.join(['%02x' % ord(c) for c in rx_data]))
            rx_data = array.array('B', rx_data)

            addr <<= 1

            if (self._csum((addr, rx_data[0], rx_data[1])) == 0  # hdr csum
                    and self._csum(rx_data[2:]) == 0             # payload csum
                    and addr == self.slave_address
                    and rx_data[0] & ~3 == (tx_data[0] & ~3) | 4 # netfn + 1
                    and rx_data[2] == target.ipmb_address
                    and rx_data[0] & 3 == tx_data[3] & 3         # rq_lun
                    and rx_data[3] & 3 == tx_data[0] & 3         # rs_lun
                    and rx_data[3] >> 2 == self.next_sequence_number
                    and rx_data[4] == tx_data[4]):               # command id
                rsp_received = True
            self._inc_sequence_number()
            timeout = self.timeout - (time.time() - start_time)

        return rx_data.tostring()

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        rx_data = self._send_and_receive_raw(target, lun, netfn, raw_bytes)
        return rx_data[5:-1]

    def send_and_receive(self, msg):
        """Sends an IPMI request message and waits for its response.

        `msg` is a IPMI Message containing both the request and response.
        """

        log().debug('IPMI Request [%s]', msg)

        retries = 0
        while retries < self.max_retries:
            try:
                rx_data = self._send_and_receive_raw(msg.target, msg.lun,
                        msg.netfn, chr(msg.cmdid) + encode_message(msg))
                break
            except TimeoutError:
                pass

            retries += 1

        else:
            raise TimeoutError()

        msg = create_message(msg.cmdid, msg.netfn + 1)
        decode_message(msg, rx_data[5:-1])

        log().debug('IPMI Response [%s])', msg)

        return msg

