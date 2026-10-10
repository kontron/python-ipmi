#!/usr/bin/env python

import os
import socket
import time

import pytest
from unittest.mock import patch

import pyipmi
from pyipmi.errors import IpmiConnectionError, IpmiTimeoutError
from pyipmi.interfaces import create_interface
from pyipmi.interfaces.ipmbsim import (MSG_FRAME, MSG_REGISTER,
                                       MSG_REGISTERED, MSG_STATUS,
                                       STATUS_ADDRESS_IN_USE, STATUS_NAK,
                                       STATUS_OK, IpmbSim, IpmbSimBroker,
                                       decode_msgs, encode_msg, take_msg)
from pyipmi.interfaces.router import MessageRouter


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / 'ipmb.sock')


@pytest.fixture
def broker(path):
    broker = IpmbSimBroker(path)
    broker.start()
    yield broker
    broker.close()


@pytest.fixture
def bmc(broker, path):
    """A BMC at 0x20 that answers Get Device ID."""
    router = MessageRouter()
    router.register_raw_handler(6, 1, lambda intf, hdr, data: b'\x00\x42')
    intf = IpmbSim(slave_address=0x20, path=path, router=router)
    intf.open()
    yield intf
    intf.close()
    router.close()


def wait_for(condition):
    for _ in range(100):
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError('timeout')


def raw_client(path, address):
    """A connection to the broker without the interface, registered."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    sock.connect(path)
    sock.sendall(encode_msg(MSG_REGISTER, bytes((1, address))))
    assert receive(sock) == (MSG_REGISTERED, bytes((STATUS_OK,)))
    return sock


def receive(sock):
    buffer = bytearray()
    while (msg := take_msg(buffer)) is None:
        buffer += sock.recv(4096)
    return msg


def test_encode_decode_msgs():
    buffer = bytearray(encode_msg(MSG_FRAME, b'\x20\x18')
                       + encode_msg(MSG_STATUS, b'\x00') + b'\x03\x05\x01')
    assert decode_msgs(buffer) == [(MSG_FRAME, b'\x20\x18'),
                                   (MSG_STATUS, b'\x00')]
    # the incomplete message stays
    assert buffer == b'\x03\x05\x01'
    with pytest.raises(ValueError):
        encode_msg(MSG_FRAME, bytes(256))


def test_create_interface(path):
    intf = create_interface('ipmbsim', slave_address=0x81, path=path)
    assert isinstance(intf, IpmbSim)
    assert (intf.slave_address, intf.path) == (0x81, path)


def test_request_and_response(bmc, path):
    intf = IpmbSim(slave_address=0x81, path=path)
    ipmi = pyipmi.create_connection(intf)
    ipmi.target = pyipmi.Target(0x20)
    with ipmi:
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    assert rsp == b'\x00\x42'


def test_broker_addresses(broker, bmc, path):
    intf = IpmbSim(slave_address=0x81, path=path)
    intf.open()
    try:
        wait_for(lambda: broker.addresses == [0x20, 0x81])
    finally:
        intf.close()
    wait_for(lambda: broker.addresses == [0x20])


def test_address_in_use(bmc, path):
    intf = IpmbSim(slave_address=0x20, path=path)
    with pytest.raises(IpmiConnectionError, match='used by another interface'):
        intf.open()


def test_invalid_address(broker, path):
    intf = IpmbSim(slave_address=0x00, path=path)
    with pytest.raises(IpmiConnectionError, match='address is invalid'):
        intf.open()


def test_no_broker(path):
    intf = IpmbSim(slave_address=0x20, path=path)
    with pytest.raises(IpmiConnectionError, match='no IPMB broker'):
        intf.open()


def test_nak_without_device(broker, path):
    intf = IpmbSim(slave_address=0x81, path=path)
    intf.open()
    try:
        # NAK: the frame is not sent, no waiting for the response
        with pytest.raises(OSError, match='no device at IPMB address 0x72'):
            intf.send_frame(b'\x72\x18\x76\x81\x04\x01\x7a')
        intf.max_retries = 1
        start = time.monotonic()
        with pytest.raises(IpmiTimeoutError):
            intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
        assert time.monotonic() - start < intf.timeout
    finally:
        intf.close()


def test_forwarded_frame(broker, path):
    # two raw clients: the frame arrives unchanged, the sender gets OK
    sender = raw_client(path, 0x24)
    receiver = raw_client(path, 0x26)
    frame = b'\x26\x18\xc2\x24\x04\x01\xd7'
    sender.sendall(encode_msg(MSG_FRAME, frame))
    assert receive(sender) == (MSG_STATUS, bytes((STATUS_OK,)))
    assert receive(receiver) == (MSG_FRAME, frame)
    # not to itself, and not without registration
    sender.sendall(encode_msg(MSG_FRAME, b'\x24\x18'))
    assert receive(sender) == (MSG_STATUS, bytes((STATUS_NAK,)))
    unregistered = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    unregistered.settimeout(1.0)
    unregistered.connect(path)
    unregistered.sendall(encode_msg(MSG_FRAME, frame))
    assert receive(unregistered) == (MSG_STATUS, bytes((STATUS_NAK,)))
    for sock in (sender, receiver, unregistered):
        sock.close()


def test_registered_once(broker, path):
    sock = raw_client(path, 0x24)
    sock.sendall(encode_msg(MSG_REGISTER, b'\x01\x26'))
    assert receive(sock) != (MSG_REGISTERED, bytes((STATUS_OK,)))
    other = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    other.settimeout(1.0)
    other.connect(path)
    other.sendall(encode_msg(MSG_REGISTER, b'\x01\x24'))
    assert receive(other) == (MSG_REGISTERED,
                              bytes((STATUS_ADDRESS_IN_USE,)))
    sock.close()
    other.close()


def test_one_broker_per_socket(broker, path):
    with pytest.raises(OSError, match='running on'):
        IpmbSimBroker(path).listen()


def test_stale_socket_replaced(path):
    # a socket file without a broker, e.g. of a broker that was killed
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(path)
    stale.close()
    broker = IpmbSimBroker(path)
    broker.start()
    broker.close()


def test_broker_close_disconnects(path):
    broker = IpmbSimBroker(path)
    broker.start()
    sock = raw_client(path, 0x24)
    broker.close()
    assert sock.recv(10) == b''
    sock.close()


def test_cli_broker(path, capsys):
    import pyipmi.cli
    broker = IpmbSimBroker(path)
    broker.start()
    try:
        # a broker is running on the socket already; without the log
        # handler of the CLI, which would stay on the pyipmi logger and
        # write to the closed output of this test
        with (patch('pyipmi.cli.setup_logging'),
              pytest.raises(SystemExit)):
            pyipmi.cli.main(['ipmbsim', 'broker', '--socket', path])
        assert 'cannot start the broker' in capsys.readouterr().out
    finally:
        broker.close()


def test_serve_forever_cleans_up(path):
    # Ctrl-C in serve_forever(): the socket is removed
    broker = IpmbSimBroker(path)
    broker.listen()

    def interrupted(timeout):
        raise KeyboardInterrupt

    broker._selector.select = interrupted
    with pytest.raises(KeyboardInterrupt):
        broker.serve_forever()
    assert not os.path.exists(path)
