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

from ..errors import IpmiTimeoutError
from ..logger import log
from .ipmb import IpmbInterface, IpmbHeaderReq, rx_filter, encode_ipmb_msg

try:
    import pyaardvark
except ImportError:  # python 2
    pyaardvark = None
except RuntimeError:  # python 3
    pyaardvark = None


class Aardvark(IpmbInterface):
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

        super().__init__(slave_address)
        self.port = port
        self.serial_number = serial_number
        self.i2c_pullups = enable_i2c_pullups
        self.target_power = enable_target_power
        self.fastmode = enable_fastmode

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

            rx_data = array('B', [i2c_addr << 1, ]) + rx_data
            rsp_received = rx_filter(header, rx_data)

        return rx_data
