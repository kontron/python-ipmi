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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from builtins import object

#from .errors import DecodingError, CompletionCodeError, RetryError
from .utils import check_completion_code, ByteBuffer
from .msgs import create_request_by_name
#from .msgs import constants

EVENT_ASSERTION = 0
EVENT_DEASSERTION = 1

class Event(object):
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
