from __future__ import absolute_import
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

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional

@register_message_class
class SetEventReceiverReq(Message):
    __cmdid__ = constants.CMDID_SET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
        Bitfield('event_receiver', 2,
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('ipmb_i2c_slave_address', 7, 0),
            Bitfield.Bit('lun', 2, 0),
            Bitfield.ReservedBit(6, 0),
        ),
    )


@register_message_class
class SetEventReceiverRsp(Message):
    __cmdid__ = constants.CMDID_SET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetEventReceiverReq(Message):
    __cmdid__ = constants.CMDID_GET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT


@register_message_class
class GetEventReceiverRsp(Message):
    __cmdid__ = constants.CMDID_GET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
        Bitfield('event_receiver', 2,
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('ipmb_i2c_slave_address', 7, 0),
            Bitfield.Bit('lun', 2, 0),
            Bitfield.ReservedBit(6, 0),
        ),
    )
