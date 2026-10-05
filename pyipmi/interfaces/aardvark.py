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

import queue
import threading
import time
from typing import Any
from collections.abc import Callable

from ..logger import log
from .ipmb import IpmbInterface
from .router import MessageRouter

try:
    import pyaardvark
except ImportError:  # python 2
    pyaardvark = None
except RuntimeError:  # python 3
    pyaardvark = None

# The receive thread checks the adapter for received messages in this
# interval. In between, it waits for device calls of other threads.
POLL_INTERVAL = 0.001


class _DeviceCall:
    """A device function call, done by the receive thread."""

    def __init__(self, func: Callable[..., Any], args: tuple) -> None:
        self.func = func
        self.args = args
        self.done = threading.Event()
        self.result: Any = None
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            self.result = self.func(*self.args)
        except Exception as e:
            self.error = e
        self.done.set()


class Aardvark(IpmbInterface):
    """This interface uses an I2C USB adapter.

    The adapter is enabled as I2C slave with the own IPMB address. A receive
    thread passes all received messages to the router, so the interface
    can also answer incoming requests (see `MessageRouter`).

    The Aardvark API is not thread-safe. While the receive thread runs, it
    does all device accesses, the other threads pass them to it.
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
        self._calls: queue.Queue = queue.Queue()

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
        self._run_calls()
        self._dev.close()
        super().close()

    def _wakeup_receiver(self) -> None:
        self._calls.put(None)

    def _call(self, func: Callable[..., Any], *args: Any) -> Any:
        """Call a device function, in the receive thread if it runs."""
        receiver = self._receiver
        if receiver is None or receiver is threading.current_thread():
            return func(*args)

        call = _DeviceCall(func, args)
        self._calls.put(call)
        if not call.done.wait(1.0):
            raise OSError('aardvark receive thread does not respond')
        if call.error is not None:
            raise call.error
        return call.result

    def _run_calls(self, timeout: float = 0) -> None:
        """Run the queued device calls, wait up to timeout for the first."""
        try:
            call = self._calls.get(timeout=timeout) if timeout else \
                self._calls.get_nowait()
            while True:
                if call is not None:
                    call.run()
                call = self._calls.get_nowait()
        except queue.Empty:
            pass

    def enable_pullups(self, enabled: bool) -> None:
        self._call(setattr, self._dev, 'i2c_pullups', enabled)

    def enable_target_power(self, enabled: bool) -> None:
        self._call(setattr, self._dev, 'target_power', enabled)

    def enable_fastmode(self, enabled: bool) -> None:
        bitrate = 400 if enabled else 100
        self._call(setattr, self._dev, 'i2c_bitrate', bitrate)

    def raw_write(self, address: int, data: bytes) -> None:
        self._call(self._dev.i2c_master_write, address, data)

    def send_frame(self, frame: bytes) -> None:
        i2c_addr = frame[0] >> 1

        log().debug('IPMB TX [%s]', bytes(frame).hex(' '))
        self._call(self._dev.i2c_master_write, i2c_addr, bytes(frame[1:]))

    def _read_frame(self, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        while not self._stop_receiver_event.is_set():
            events = self._dev.poll(0)
            if pyaardvark.POLL_I2C_READ in events:
                (i2c_addr, rx_data) = self._dev.i2c_slave_read()
                # the adapter strips the own address (rqSA) of the message
                return bytes((i2c_addr << 1,)) + bytes(rx_data)
            if time.monotonic() >= deadline:
                break
            # a device call wakes up the wait immediately
            self._run_calls(POLL_INTERVAL)
        return None
