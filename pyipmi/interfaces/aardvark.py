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

from __future__ import annotations

import time
from array import array

from .. import Target
from ..msgs import create_message, encode_message, decode_message, Message
from ..errors import IpmiTimeoutError
from ..logger import log
from ..interfaces.ipmb import IpmbHeaderReq, checksum, rx_filter, encode_ipmb_msg
from ..session import Session
from ..utils import py3_array_tobytes

try:
    import pyaardvark
except ImportError:  # python 2
    pyaardvark = None
except RuntimeError:  # python 3
    pyaardvark = None


class Aardvark(object):
    """This interface uses an I2C USB adapter."""

    NAME = 'aardvark'

    def __init__(self, slave_address: int = 0x20, port: int = 0,
                 serial_number: str | None = None,
                 enable_i2c_pullups: bool | None = None,
                 enable_target_power: bool | None = None,
                 enable_fastmode: bool | None = None) -> None:
        if pyaardvark is None:
            raise RuntimeError('No pyaardvark module found. You can not '
                               'use this interface.')

        self.slave_address = slave_address
        self.port = port
        self.serial_number = serial_number
        self.i2c_pullups = enable_i2c_pullups
        self.target_power = enable_target_power
        self.fastmode = enable_fastmode
        self.timeout = 0.25
        self.max_retries = 3
        self.next_sequence_number = 0

    def open(self) -> None:
        self._dev = pyaardvark.open(self.port, self.serial_number)
        self._dev.enable_i2c_slave(self.slave_address >> 1)

        if self.i2c_pullups:
            self.enable_pullups(self.i2c_pullups)
        if self.target_power:
            self.enable_target_power(self.target_power)

        if self.fastmode is not None:
            self.enable_fastmode(self.fastmode)
        else:
            self.enable_fastmode(False)

    def close(self) -> None:
        self._dev.close()

    def enable_pullups(self, enabled: bool) -> None:
        self._dev.i2c_pullups = enabled

    def enable_target_power(self, enabled: bool) -> None:
        self._dev.target_power = enabled

    def enable_fastmode(self, enabled: bool) -> None:
        if enabled:
            self._dev.i2c_bitrate = 400
        else:
            self._dev.i2c_bitrate = 100

    def raw_write(self, address: int, data: bytes) -> None:
        self._dev.i2c_master_write(address, data)

    def establish_session(self, session: Session) -> None:
        pass

    def close_session(self) -> None:
        pass

    def is_ipmc_accessible(self, target: Target) -> bool:
        header = IpmbHeaderReq()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = 1
        self._send_raw(header, None)
        self._receive_raw(header)
        return True

    def _inc_sequence_number(self) -> None:
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    @staticmethod
    def _encode_ipmb_msg_req(header: IpmbHeaderReq, cmd_data: bytes) -> array:
        data = header.encode()
        data.extend(cmd_data)
        data.append(checksum(data[2:]))

        return data

    def _send_raw(self, header: IpmbHeaderReq,
                  raw_bytes: bytes | None) -> None:
        raw_bytes = encode_ipmb_msg(header, raw_bytes)
        i2c_addr = header.rs_sa >> 1

        raw_bytes = array('B', raw_bytes)
        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % b for b in raw_bytes]))
        self._dev.i2c_master_write(i2c_addr, raw_bytes[1:])

    def _receive_raw(self, header: IpmbHeaderReq) -> array:
        start_time = time.time()
        rsp_received = False
        poll_returned_no_data = False
        while not rsp_received:
            timeout = self.timeout - (time.time() - start_time)

            if timeout <= 0 or poll_returned_no_data:
                raise IpmiTimeoutError()

            ret = self._dev.poll(int(timeout * 1000))

            # poll returns an empty list if no event is pending
            if not ret:
                poll_returned_no_data = True
                continue

            (i2c_addr, rx_data) = self._dev.i2c_slave_read()
            rx_data = array('B', rx_data)
            log().debug('I2C RX from %02Xh [%s]', i2c_addr << 1,
                        ' '.join(['%02x' % c for c in rx_data]))

            rq_sa = array('B', [i2c_addr << 1, ])
            rsp_received = rx_filter(header, rq_sa + rx_data)

        return rx_data

    def _send_and_receive(self, target: Target, lun: int, netfn: int,
                          cmdid: int, payload: bytes) -> bytes:
        """Send and receive data using aardvark interface.

        target:
        lun:
        netfn:
        cmdid:
        payload: IPMI message payload as bytestring

        Returns the received data as bytestring
        """
        self._inc_sequence_number()

        # assemble IPMB header
        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = cmdid

        retries = 0
        while retries < self.max_retries:
            try:
                self._send_raw(header, payload)
                rx_data = self._receive_raw(header)
                break
            except IpmiTimeoutError:
                pass
            except IOError:
                pass

            retries += 1
            time.sleep(retries*0.2)

        else:
            raise IpmiTimeoutError()

        return py3_array_tobytes(rx_data)[5:-1]

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        """Interface function to send and receive raw message.

        target: IPMI target
        lun: logical unit number
        netfn: network function
        raw_bytes: RAW bytes as bytestring

        Returns the IPMI message response bytestring.
        """
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])

    def send_and_receive(self, req: Message) -> Message:
        """Interface function to send and receive an IPMI message.

        target: IPMI target
        req: IPMI message request

        Returns the IPMI message response.
        """
        log().debug('IPMI Request [%s]', req)

        rx_data = self._send_and_receive(target=req.target,
                                         lun=req.lun,
                                         netfn=req.netfn,
                                         cmdid=req.cmdid,
                                         payload=encode_message(req))
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)

        log().debug('IPMI Response [%s])', rsp)

        return rsp
