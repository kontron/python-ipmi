import constants
from pyipmi.msgs import Message
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional

CONTROL_POWER_DOWN = 0
CONTROL_POWER_UP = 1
CONTROL_POWER_CYCLE = 2
CONTROL_HARD_RESET = 3
CONTROL_DIAGNOSTIC_INTERRUPT = 4
CONTROL_SOFT_SHUTDOWN = 5

class ChassisControl(Message):
    CMDID = constants.CMDID_CHASSIS_CONTROL
    NETFN = constants.NETFN_CHASSIS
    LUN = 0
    _REQ_DESC = (
        Bitfield('control', 1,
            Bitfield.Bit('option', 4),
            Bitfield.ReservedBit(4, 0)
        ),
    )
    _RSP_DESC = (
        CompletionCode(),
    )
