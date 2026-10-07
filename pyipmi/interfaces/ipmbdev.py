"""Interface for the ipmb-dev-int Linux driver.

Example:
    Get the device ID of the BMC on the IPMB of ``/dev/ipmb-0``::

        interface = pyipmi.interfaces.create_interface(
            'ipmbdev', slave_address=0x24, port='/dev/ipmb-0')
        ipmi = pyipmi.create_connection(interface)
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import logging
import os
import select

from .ipmb import IpmbInterface
from .router import MessageRouter

logger = logging.getLogger(__name__)


class IpmbDev(IpmbInterface):
    """This interface uses the ipmb-dev-int Linux driver.

    The driver receives all messages addressed to the slave address of the
    device. A receive thread passes them to the router, so the interface can
    also answer incoming requests (see `MessageRouter`).
    """

    NAME = 'ipmbdev'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ipmb-0',
                 router: MessageRouter | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The own IPMB address. The address the driver
                receives on is configured in the driver, not here.
            port: The device file of the driver.
            router: The router of the received messages, see
                :class:`~pyipmi.interfaces.ipmb.IpmbInterface`.
        """
        # TODO: slave address is currently not defined here
        super().__init__(slave_address, router)
        self.port = port

    def open(self) -> None:
        """Open the device file and start the receive thread."""
        self._dev = os.open(self.port, os.O_RDWR)
        # wakes up the receive thread on close
        self._wakeup_r, self._wakeup_w = os.pipe()
        self._start_receiver()

    def close(self) -> None:
        """Stop the receive thread and close the device file."""
        self._stop_receiver()
        os.close(self._dev)
        os.close(self._wakeup_r)
        os.close(self._wakeup_w)
        super().close()

    def _wakeup_receiver(self) -> None:
        os.write(self._wakeup_w, b'\0')

    def send_frame(self, frame: bytes) -> None:
        """Send a complete IPMB message, starting with rsSA.

        Args:
            frame: The message.
        """
        logger.debug('IPMB TX [%s]', bytes(frame).hex(' '))
        os.write(self._dev, bytes([len(frame)]) + bytes(frame))

    def _read_frame(self, timeout: float) -> bytes | None:
        r, w, e = select.select([self._dev, self._wakeup_r], [], [], timeout)
        if self._dev not in r:
            return None

        rx_data = os.read(self._dev, 256)
        # ipmb-dev-int puts message length into first byte
        if not rx_data or rx_data[0] != len(rx_data) - 1:
            logger.debug('ipmbdev RX bad length [%s]', rx_data.hex(' '))
            return None
        return rx_data[1:]
