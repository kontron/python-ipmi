import array

import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import Optional
from . import RemainingBytes

from pyipmi.utils import ByteBuffer

@register_message_class
class SetLanConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_SET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT
    __default_lun__ = 0
    __fields__ = (
            Bitfield('command', 1,
                Bitfield.Bit('channel_number', 4, 0),
                Bitfield.ReservedBit(4, 0),
            ),
            UnsignedInt('parameter_selector', 1),
            RemainingBytes('data'),
    )


@register_message_class
class SetLanConfigurationParametersRsp(Message):
    __cmdid__ = constants.CMDID_SET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            Optional(ByteArray('auxiliary', 4))
    )


@register_message_class
class GetLanConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_GET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT
    __default_lun__ = 0
    __fields__ = (
            Bitfield('command', 1,
                Bitfield.Bit('channel_number', 4),
                Bitfield.ReservedBit(3, 0),
                Bitfield.Bit('get_parameter_revision_only', 1, 0),
            ),
            UnsignedInt('parameter_selector', 1, 0),
            UnsignedInt('set_selector', 1, 0),
            UnsignedInt('block_selector', 1, 0),
    )


@register_message_class
class GetLanConfigurationParametersRsp(Message):
    __cmdid__ = constants.CMDID_GET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            UnsignedInt('parameter_revision', 1, 0),
            RemainingBytes('data'),
    )

