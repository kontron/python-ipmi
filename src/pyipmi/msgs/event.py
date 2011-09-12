import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import DecodingError, EncodingError

@register_message_class
class SetEventReceiverReq(Message):
    __cmdid__ = constants.CMDID_SET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
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
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetEventReceiverReq(Message):
    __cmdid__ = constants.CMDID_GET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetEventReceiverRsp(Message):
    __cmdid__ = constants.CMDID_GET_EVENT_RECEIVER
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('event_receiver', 2,
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('ipmb_i2c_slave_address', 7, 0),
            Bitfield.Bit('lun', 2, 0),
            Bitfield.ReservedBit(6, 0),
        ),
    )
