from unittest.mock import MagicMock

from pyipmi import interfaces, create_connection
from pyipmi.msgs.event import (SetEventReceiverRsp, GetEventReceiverRsp)


class TestEvent(object):

    def setup_method(self):
        self.mock_send_recv = MagicMock()

        interface = interfaces.create_interface('mock')
        self.ipmi = create_connection(interface)
        self.ipmi.send_message = self.mock_send_recv

    def test_set_event_receiver(self):

        rsp = SetEventReceiverRsp()
        rsp.completion_code = 0
        self.mock_send_recv.return_value = rsp

        self.ipmi.set_event_receiver(ipmb_address=0xb0, lun=1)
        args, _ = self.mock_send_recv.call_args
        req = args[0]
        assert req.event_receiver.ipmb_i2c_slave_address == 0xb0
        assert req.event_receiver.lun == 1

    def test_get_event_receiver(self):

        rsp = GetEventReceiverRsp()
        rsp.completion_code = 0
        rsp.event_receiver.ipmb_i2c_slave_address = 0xc0
        rsp.event_receiver.lun = 2
        self.mock_send_recv.return_value = rsp

        (addr, lun) = self.ipmi.get_event_receiver()
        assert addr == 0xc0
        assert lun == 2
