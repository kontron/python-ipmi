#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from pyipmi.errors import DecodingError, CompletionCodeError, RetryError
from pyipmi.utils import check_completion_code, ByteBuffer
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import constants

EVENT_ASSERTION = 0
EVENT_DEASSERTION = 1

class Event:
    def set_event_receiver(self, ipmb_address, lun):
        req = create_request_by_name('SetEventReceiver')
        req.event_receiver.ipmb_i2c_slave_address = ipmb_address
        req.event_receiver.lun = lun
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def get_event_receiver(self):
        req = create_request_by_name('GetEventReceiver')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        ipmb_address = rsp.event_receiver.ipmb_i2c_slave_address
        lun = rsp.event_receiver.lun
        return (ipmb_address, lun)
