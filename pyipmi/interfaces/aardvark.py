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

import threading
import time

from ..logger import log
from .ipmb import IpmbInterface
from .router import MessageRouter

try:
    import pyaardvark
except ImportError:  # python 2
    pyaardvark = None
except RuntimeError:  # python 3
    pyaardvark = None

# maximum time the receive thread blocks the device while polling
POLL_INTERVAL_MS = 10


class Aardvark(IpmbInterface):
    """This interface uses an I2C USB adapter.

    The adapter is enabled as I2C slave with the own IPMB address. A receive
    thread passes all received messages to the router, so the interface
    can also answer incoming requests (see `MessageRouter`).
    """

    NAME = 'aardvark'

    def __init__(self, slave_address: int = 0x20, port: int = 0,
                 serial_number: str | None = None,
                 enable_i2c_pullups: bool | None = None,
                 enable_target_power: bool | None = None,
                 enable_fastmode: bool | None = None,
                 router: MessageRouter | None = None) -> None:
        if pyaardvark is None:
            raise RuntimeError('No pyaardvark module found. You can not '
                               'use this interface.')

        super().__init__(slave_address, router)
        self.port = port
        self.serial_number = serial_number
        self.i2c_pullups = enable_i2c_pullups
        self.target_power = enable_target_power
        self.fastmode = enable_fastmode
        # the Aardvark API is not thread-safe
        self._dev_lock = threading.Lock()

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

        self._start_receiver()

    def close(self) -> None:
        self._stop_receiver()
        self._dev.close()
        super().close()

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
        with self._dev_lock:
            self._dev.i2c_master_write(address, data)

    def send_frame(self, frame: bytes) -> None:
        i2c_addr = frame[0] >> 1

        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % b for b in frame]))
        with self._dev_lock:
            self._dev.i2c_master_write(i2c_addr, bytes(frame[1:]))

    def _read_frame(self, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._dev_lock:
                events = self._dev.poll(POLL_INTERVAL_MS)
                if pyaardvark.POLL_I2C_READ not in events:
                    continue
                (i2c_addr, rx_data) = self._dev.i2c_slave_read()

            # the adapter strips the own address (rqSA) of the message
            return bytes((i2c_addr << 1,)) + bytes(rx_data)
        return None
