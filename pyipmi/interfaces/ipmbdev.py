from __future__ import annotations

import os
import select
import time
from array import array

from ..errors import IpmiTimeoutError
from ..logger import log
from .ipmb import IpmbInterface, IpmbHeaderReq, rx_filter, encode_ipmb_msg


class IpmbDev(IpmbInterface):
    """This interface uses ipmb-dev-int linux driver."""

    NAME = 'ipmbdev'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ipmb-0') -> None:
        # TODO: slave address is currently not defined here
        super().__init__(slave_address)
        self.port = port

    def open(self) -> None:
        self._dev = os.open(self.port, os.O_RDWR)

    def close(self) -> None:
        os.close(self._dev)

    def _send_raw(self, header: IpmbHeaderReq,
                  raw_bytes: bytes | None) -> None:
        raw_bytes = encode_ipmb_msg(header, raw_bytes)
        i2c_addr = header.rs_sa >> 1

        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % b for b in raw_bytes]))
        os.write(self._dev, bytes([len(raw_bytes)]) + raw_bytes)

    def _receive_raw(self, header: IpmbHeaderReq) -> array:
        start_time = time.time()
        rsp_received = False
        poll_returned_no_data = False
        while not rsp_received:
            timeout = self.timeout - (time.time() - start_time)

            if timeout <= 0 or poll_returned_no_data:
                raise IpmiTimeoutError()

            r, w, e = select.select([self._dev], [], [], timeout)
            if self._dev not in r:
                poll_returned_no_data = True
                continue

            rx_data = os.read(self._dev, 256)
            # ipmb-dev-int puts message length into first byte
            assert rx_data[0] == len(rx_data) - 1
            rx_data = rx_data[1:]

            rx_data = array('B', rx_data)
            log().debug('I2C RX from %02Xh [%s]', rx_data[3],
                        ' '.join(['%02x' % c for c in rx_data]))

            rsp_received = rx_filter(header, rx_data)

        return rx_data
