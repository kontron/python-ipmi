from unittest.mock import MagicMock

import pytest

from pyipmi import interfaces, create_connection
from pyipmi.msgs.event import (SetEventReceiverRsp, GetEventReceiverRsp)

from .ipmi_helper import create_ipmi


class TestEvent:

    def setup_method(self):
        self.mock_send_recv = MagicMock()

        interface = interfaces.create_interface('mock')
        self.ipmi = create_connection(interface)
        self.ipmi.send_message = self.mock_send_recv

    def test_set_event_receiver(self):

        rsp = SetEventReceiverRsp()
        rsp.completion_code = 0
        self.mock_send_recv.return_value = rsp

        # the 7-bit address of the 8-bit address 0xb0
        self.ipmi.set_event_receiver(ipmb_address=0x58, lun=1)
        args, _ = self.mock_send_recv.call_args
        req = args[0]
        assert req.event_receiver.ipmb_i2c_slave_address == 0x58
        assert req.event_receiver.lun == 1

    def test_get_event_receiver(self):

        rsp = GetEventReceiverRsp()
        rsp.completion_code = 0
        rsp.event_receiver.ipmb_i2c_slave_address = 0x60
        rsp.event_receiver.lun = 2
        self.mock_send_recv.return_value = rsp

        (addr, lun) = self.ipmi.get_event_receiver()
        assert addr == 0x60
        assert lun == 2


def test_set_event_receiver_encoding():
    ipmi = create_ipmi(b'\x00')
    # the BMC at the 8-bit address 0x20, LUN 1
    ipmi.set_event_receiver(0x10, 1)
    assert ipmi.requests == [('SetEventReceiverReq', b'\x20\x01')]


@pytest.mark.parametrize('ipmb_address, lun', [
    # an 8-bit address
    (0x80, 0),
    (-1, 0),
    (0x10, 4),
])
def test_set_event_receiver_invalid(ipmb_address, lun):
    ipmi = create_ipmi(b'\x00')
    with pytest.raises(ValueError):
        ipmi.set_event_receiver(ipmb_address, lun)
    assert ipmi.requests == []


def test_disable_event_message_generation():
    ipmi = create_ipmi(b'\x00')
    ipmi.disable_event_message_generation()
    assert ipmi.requests == [('SetEventReceiverReq', b'\xff\x00')]
