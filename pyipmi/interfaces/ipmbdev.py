from __future__ import annotations

import os
import select

from ..logger import log
from .ipmb import IpmbInterface
from .router import MessageRouter


class IpmbDev(IpmbInterface):
    """This interface uses ipmb-dev-int linux driver.

    The driver receives all messages addressed to the slave address of the
    device. A receive thread passes them to the router, so the interface can
    also answer incoming requests (see `MessageRouter`).
    """

    NAME = 'ipmbdev'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ipmb-0',
                 router: MessageRouter | None = None) -> None:
        # TODO: slave address is currently not defined here
        super().__init__(slave_address, router)
        self.port = port

    def open(self) -> None:
        self._dev = os.open(self.port, os.O_RDWR)
        # wakes up the receive thread on close
        self._wakeup_r, self._wakeup_w = os.pipe()
        self._start_receiver()

    def close(self) -> None:
        self._stop_receiver()
        os.close(self._dev)
        os.close(self._wakeup_r)
        os.close(self._wakeup_w)
        super().close()

    def _wakeup_receiver(self) -> None:
        os.write(self._wakeup_w, b'\0')

    def send_frame(self, frame: bytes) -> None:
        i2c_addr = frame[0] >> 1

        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % b for b in frame]))
        os.write(self._dev, bytes([len(frame)]) + bytes(frame))

    def _read_frame(self, timeout: float) -> bytes | None:
        r, w, e = select.select([self._dev, self._wakeup_r], [], [], timeout)
        if self._dev not in r:
            return None

        rx_data = os.read(self._dev, 256)
        # ipmb-dev-int puts message length into first byte
        if not rx_data or rx_data[0] != len(rx_data) - 1:
            log().debug('ipmbdev RX bad length [%s]', rx_data.hex(' '))
            return None
        return rx_data[1:]
