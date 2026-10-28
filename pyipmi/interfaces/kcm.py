# Copyright (c) 2026  Kontron Europe GmbH
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

"""Interface for the IPMB channels of a KCM.

The KCM is connected to both IPMB buses of a chassis, IPMB-A on channel 0
and IPMB-B on channel 1, and to the host over a serial port, which needs the
pyserial package. :class:`Kcm` is the interface for one channel of the KCM,
:class:`KcmDevice` the serial connection shared by the channels.

Example:
    Get the device ID of the IPMC at 0x82 on IPMB-B::

        interface = pyipmi.interfaces.create_interface(
            'kcm', slave_address=0x20, port='/dev/ttyUSB0', channel=1)
        ipmi = pyipmi.create_connection(interface)
        ipmi.target = pyipmi.Target(ipmb_address=0x82)
        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import logging
import queue
import struct
import threading
import time
from typing import Any
from collections.abc import Callable

from .ipmb import IpmbInterface
from .router import MessageRouter

logger = logging.getLogger(__name__)

try:
    import serial
except ImportError:
    serial = None

STX = 0x02
ETX = 0x03

# host to device
CMD_GET_BRIDGE_INFO = 0
CMD_SEND_MESSAGE = 1
CMD_CONFIGURE_I2C_CHANNEL = 2
CMD_GET_STATUS_INFO = 3

# device to host, the ids have another meaning than from host to device
RSP_GET_BRIDGE_INFO = 4
RSP_STATUS = 5
EVT_RECEIVED_I2C_MESSAGE = 6
RSP_STATUS_INFO = 7

# a frame carries at most 127 bytes: cmd, payload and CRC
MAX_FRAME_LEN = 127

# the oldest firmware with a known layout of the status reply, 1.6 and 1.7
# use the same one
MIN_FIRMWARE_VERSION = 0x0106


def crc8(data: bytes) -> int:
    """Return the CRC-8 of the KCM protocol.

    Polynomial 0x97, initial value 0xff, no reflection and no final XOR.

    Args:
        data: The binary frame, the command id and the payload.

    Returns:
        The CRC.
    """
    crc = 0xff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x97) & 0xff
            else:
                crc = (crc << 1) & 0xff
    return crc


def encode_frame(cmd: int, payload: bytes) -> bytes:
    """Encode a frame for the serial line.

    Args:
        cmd: The command id.
        payload: The payload, starting with the sequence number.

    Returns:
        The frame: STX, the hex encoded command, payload and CRC, ETX.
    """
    data = bytes((cmd,)) + payload
    data += bytes((crc8(data),))
    return bytes((STX,)) + data.hex().upper().encode() + bytes((ETX,))


def decode_frame(body: bytes) -> tuple[int, bytes] | None:
    """Decode the hex body of a frame received between STX and ETX.

    Args:
        body: The hex encoded command, payload and CRC.

    Returns:
        The command id and the payload, or None if the frame is invalid.
    """
    try:
        data = bytes.fromhex(body.decode('ascii'))
    except ValueError:
        return None
    if len(data) < 2 or crc8(data[:-1]) != data[-1]:
        return None
    return data[0], data[1:-1]


class KcmError(IOError):
    """The KCM failed or did not reply."""


class KcmDevice:
    """Connection to the serial port of a KCM.

    Both channels of a KCM share one serial port, so the interfaces of
    the channels share one device (see `acquire()`). A receive thread reads
    all frames from the KCM: replies are passed to the waiting
    `command()` by their sequence number, received IPMB messages to the
    listener of their channel.
    """

    _devices: dict[str, KcmDevice] = {}
    _devices_lock = threading.Lock()

    def __init__(self, port: str, baudrate: int = 115200,
                 cmd_timeout: float = 1.0) -> None:
        """Initialize the device, it is opened by :meth:`open`.

        Args:
            port: The serial port, a device path or a pyserial URL.
            baudrate: The baud rate of the serial port.
            cmd_timeout: The time to wait for the reply to a command in
                seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.cmd_timeout = cmd_timeout
        self.firmware_version: int | None = None
        self._ser: Any = None
        self._rx_buf = bytearray()
        self._seq = 0
        self._replies: dict[int, queue.Queue] = {}
        self._replies_lock = threading.Lock()
        self._listeners: dict[int, Callable[[bytes], None]] = {}
        self._listeners_lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._users = 0

    @classmethod
    def acquire(cls, port: str, baudrate: int = 115200) -> KcmDevice:
        """Return the open device of the port, open it on first use.

        Args:
            port: The serial port, a device path or a pyserial URL.
            baudrate: The baud rate of the serial port, used when the
                device is opened.

        Returns:
            The device, release it with :meth:`release`.
        """
        with cls._devices_lock:
            device = cls._devices.get(port)
            if device is None:
                device = cls(port, baudrate)
                device.open()
                cls._devices[port] = device
            device._users += 1
            return device

    def release(self) -> None:
        """Release a device returned by `acquire()`, close it on last use."""
        with self._devices_lock:
            self._users -= 1
            if self._users > 0:
                return
            if self._devices.get(self.port) is self:
                del self._devices[self.port]
        self.close()

    def open(self) -> None:
        """Open the serial port and start the receive thread.

        The firmware version of the KCM is read and stored in
        :attr:`firmware_version`.

        Raises:
            RuntimeError: The pyserial package is not installed.
            KcmError: The KCM did not reply or its firmware
                is too old.
        """
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        self._ser = serial.serial_for_url(self.port, baudrate=self.baudrate,
                                          timeout=0.05)
        self._rx_buf = bytearray()
        self._stop.clear()
        self._reader = threading.Thread(target=self._read_loop,
                                        name='kcm-rx',
                                        daemon=True)
        self._reader.start()

        try:
            reply = self.command(CMD_GET_BRIDGE_INFO, b'',
                                 RSP_GET_BRIDGE_INFO)
            if len(reply) < 2:
                raise KcmError('invalid KCM info reply')
            (version,) = struct.unpack_from('<H', reply)
            if version < MIN_FIRMWARE_VERSION:
                raise KcmError(
                    f'KCM firmware {version >> 8:d}.{version & 0xff:d}, '
                    f'interface needs {MIN_FIRMWARE_VERSION >> 8:d}.'
                    f'{MIN_FIRMWARE_VERSION & 0xff:d}')
        except Exception:
            self.close()
            raise

        self.firmware_version = version
        logger.debug('KCM firmware %d.%d on %s',
                     version >> 8, version & 0xff, self.port)

    def close(self) -> None:
        """Stop the receive thread and close the serial port."""
        self._stop.set()
        if self._reader is not None:
            cancel_read = getattr(self._ser, 'cancel_read', None)
            if cancel_read is not None:
                cancel_read()
            self._reader.join()
            self._reader = None
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def add_listener(self, channel: int,
                     listener: Callable[[bytes], None]) -> None:
        """Pass IPMB messages received on the channel to the listener.

        The listener is called in the receive thread and must not block.

        Args:
            channel: The channel number.
            listener: The listener, called with the message.

        Raises:
            KcmError: The channel already has a listener.
        """
        with self._listeners_lock:
            if channel in self._listeners:
                raise KcmError(
                    f'channel {channel:d} is already in use')
            self._listeners[channel] = listener

    def remove_listener(self, channel: int) -> None:
        """Remove the listener of the channel, if there is one.

        Args:
            channel: The channel number.
        """
        with self._listeners_lock:
            self._listeners.pop(channel, None)

    def has_listener(self, channel: int) -> bool:
        """Check if the channel has a listener.

        Args:
            channel: The channel number.

        Returns:
            True if the channel has a listener.
        """
        return channel in self._listeners

    def _next_seq(self) -> int:
        with self._replies_lock:
            self._seq = (self._seq + 1) & 0xffff
            return self._seq

    def command(self, cmd: int, data: bytes, reply_cmd: int) -> bytes:
        """Send a command to the KCM and return its reply.

        Args:
            cmd: The command id.
            data: The payload after the sequence number.
            reply_cmd: The command id of the expected reply.

        Returns:
            The payload of the reply after the sequence number.

        Raises:
            KcmError: The frame is too long, or no reply within
                the command timeout.
        """
        seq = self._next_seq()
        payload = struct.pack('<H', seq) + data
        if len(payload) + 2 > MAX_FRAME_LEN:
            # the receive buffer of the KCM would overflow
            raise KcmError(
                f'frame too long ({len(payload) + 2:d} bytes)')

        replies: queue.Queue = queue.Queue()
        with self._replies_lock:
            self._replies[seq] = replies
        try:
            frame = encode_frame(cmd, payload)
            logger.debug('KCM TX %s', frame[1:-1].decode())
            self._ser.write(frame)

            deadline = time.monotonic() + self.cmd_timeout
            while True:
                timeout = max(0.0, deadline - time.monotonic())
                try:
                    rsp_cmd, rsp_data = replies.get(timeout=timeout)
                except queue.Empty:
                    raise KcmError('no reply from KCM') from None
                if rsp_cmd == reply_cmd:
                    return rsp_data
                logger.debug('KCM unexpected reply %d to %d',
                             rsp_cmd, cmd)
        finally:
            with self._replies_lock:
                del self._replies[seq]

    def _read_frame(self) -> tuple[int, bytes] | None:
        """Return the next valid frame or None if none is read."""
        while True:
            end = self._rx_buf.find(ETX)
            if end < 0:
                # bytes outside of a frame are ignored
                start = self._rx_buf.rfind(STX)
                if start < 0:
                    self._rx_buf.clear()
                else:
                    del self._rx_buf[:start]
                data = self._ser.read(self._ser.in_waiting or 1)
                if not data:
                    return None
                self._rx_buf += data
                continue

            # an STX inside a frame restarts the frame, so the frame starts
            # at the last STX before the ETX
            start = self._rx_buf.rfind(STX, 0, end)
            if start < 0:
                del self._rx_buf[:end + 1]
                continue
            body = bytes(self._rx_buf[start + 1:end])
            del self._rx_buf[:end + 1]
            logger.debug('KCM RX %s', body.decode(errors='replace'))
            frame = decode_frame(body)
            if frame is not None:
                return frame

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self._read_frame()
            except Exception as e:
                if not self._stop.is_set():
                    logger.error('KCM receive failed: %s', e)
                return

            if frame is None:
                continue
            cmd, payload = frame
            if len(payload) < 2:
                continue
            if cmd == EVT_RECEIVED_I2C_MESSAGE:
                self._dispatch(payload[2:])
                continue
            (seq,) = struct.unpack_from('<H', payload)
            with self._replies_lock:
                replies = self._replies.get(seq)
            if replies is not None:
                replies.put((cmd, payload[2:]))

    def _dispatch(self, data: bytes) -> None:
        if not data:
            return
        listener = self._listeners.get(data[0])
        if listener is None:
            return
        try:
            listener(data[1:])
        except Exception:
            logger.exception('KCM rx listener failed')


class Kcm(IpmbInterface):
    """This interface uses one IPMB channel of the KCM.

    Channel 0 is IPMB-A, channel 1 IPMB-B. An interface for the other
    channel of the same KCM can be opened at the same time; they share
    the serial port.

    Incoming requests are ignored by default. To answer them, e.g. to
    acknowledge the Platform Event Messages of the IPMCs, set a
    `MessageRouter` with registered handlers.
    """

    NAME = 'kcm'

    def __init__(self, slave_address: int = 0x20,
                 port: str = '/dev/ttyUSB0', channel: int = 0,
                 baudrate: int = 115200, i2c_speed: int = 100000,
                 router: MessageRouter | None = None) -> None:
        """Initialize the interface.

        Args:
            slave_address: The own IPMB address, set on the channel of the
                KCM when the interface is opened.
            port: The serial port of the KCM, a device path or a
                pyserial URL.
            channel: The channel of the KCM, 0 for IPMB-A and 1 for
                IPMB-B.
            baudrate: The baud rate of the serial port.
            i2c_speed: The I2C bit rate of the channel in Hz.
            router: The router of the received messages, see
                :class:`~pyipmi.interfaces.ipmb.IpmbInterface`.

        Raises:
            RuntimeError: The pyserial package is not installed.
        """
        if serial is None:
            raise RuntimeError('No pyserial module found. You can not '
                               'use this interface.')

        super().__init__(slave_address, router)
        self.port = port
        self.channel = channel
        self.baudrate = baudrate
        self.i2c_speed = i2c_speed
        self._device: KcmDevice | None = None

    def open(self) -> None:
        """Open the KCM and configure the channel.

        Raises:
            KcmError: The KCM failed, or the channel is
                already used by another interface.
        """
        device = KcmDevice.acquire(self.port, self.baudrate)
        # claim the channel first, so the configuration of a channel used
        # by another interface is not changed
        try:
            device.add_listener(self.channel, self._receive_frame)
        except Exception:
            device.release()
            raise
        try:
            self._check_status(device.command(
                CMD_CONFIGURE_I2C_CHANNEL,
                struct.pack('<BBI', self.channel, self.slave_address,
                            self.i2c_speed),
                RSP_STATUS))
        except Exception:
            device.remove_listener(self.channel)
            device.release()
            raise
        self._device = device

    def close(self) -> None:
        """Release the KCM, it is closed if no other channel uses it."""
        if self._device is not None:
            self._device.remove_listener(self.channel)
            self._device.release()
            self._device = None
        super().close()

    @staticmethod
    def _check_status(reply: bytes) -> None:
        if len(reply) < 2:
            raise KcmError('invalid status reply')
        if reply[0] != 1:
            raise KcmError(f'KCM error code {reply[1]:d}')

    def send_frame(self, frame: bytes) -> None:
        """Send a complete IPMB message, starting with rsSA.

        The rsSA is sent as the address of the I2C write, the KCM
        converts it to the 7-bit address.

        Args:
            frame: The message.

        Raises:
            KcmError: The interface is not open, or the KCM
                failed to send the message, e.g. it was not acknowledged.
        """
        if self._device is None:
            raise KcmError('interface is not open')

        frame = bytes(frame)
        logger.debug('IPMB TX channel %d [%s]', self.channel, frame.hex(' '))
        self._check_status(self._device.command(
            CMD_SEND_MESSAGE, bytes((self.channel,)) + frame, RSP_STATUS))
