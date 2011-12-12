import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional

CONTROL_POWER_DOWN = 0
CONTROL_POWER_UP = 1
CONTROL_POWER_CYCLE = 2
CONTROL_HARD_RESET = 3
CONTROL_DIAGNOSTIC_INTERRUPT = 4
CONTROL_SOFT_SHUTDOWN = 5

@register_message_class
class ChassisControlReq(Message):
    __cmdid__ = constants.CMDID_CHASSIS_CONTROL
    __netfn__ = constants.NETFN_CHASSIS
    __default_lun__ = 0
    __fields__ = (
        Bitfield('control', 1,
            Bitfield.Bit('option', 4),
            Bitfield.ReservedBit(4, 0)
        ),
    )


@register_message_class
class ChassisControlRsp(Message):
    __cmdid__ = constants.CMDID_CHASSIS_CONTROL
    __netfn__ = constants.NETFN_CHASSIS | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )
