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

@register_message_class
class GetDeviceIdReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_ID
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()

@register_message_class
class GetDeviceIdRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_ID
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            UnsignedInt('device_id', 1),
            Bitfield('device_revision', 1,
                Bitfield.Bit('device_revision', 4),
                Bitfield.ReservedBit(3, 0),
                Bitfield.Bit('provides_device_sdrs', 1)
            ),
            Bitfield('firmware_revision', 2,
                Bitfield.Bit('major', 7),
                Bitfield.Bit('device_available', 1),
                Bitfield.Bit('minor', 8)
            ),
            UnsignedInt('ipmi_version', 1),
            Bitfield('additional_support', 1,
                Bitfield.Bit('sensor', 1),
                Bitfield.Bit('sdr_repository', 1),
                Bitfield.Bit('sel', 1),
                Bitfield.Bit('fru_inventory', 1),
                Bitfield.Bit('ipmb_event_receiver', 1),
                Bitfield.Bit('ipmb_event_generator', 1),
                Bitfield.Bit('bridge', 1),
                Bitfield.Bit('chassis', 1)
            ),
            UnsignedInt('manufacturer_id', 3),
            UnsignedInt('product_id', 2),
            Optional(ByteArray('auxiliary', 4))
    )


@register_message_class
class ColdResetReq(Message):
    __cmdid__ = constants.CMDID_COLD_RESET
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class ColdResetRsp(Message):
    __cmdid__ = constants.CMDID_COLD_RESET
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class WarmResetReq(Message):
    __cmdid__ = constants.CMDID_WARM_RESET
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class WarmResetRsp(Message):
    __cmdid__ = constants.CMDID_WARM_RESET
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class ManufacturingTestOnReq(Message):
    __cmdid__ = constants.CMDID_MANUFACTURING_TEST_ON
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class ManufacturingTestOnRsp(Message):
    __cmdid__ = constants.CMDID_MANUFACTURING_TEST_ON
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class ResetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_RESET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class ResetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_RESET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_SET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = (
            Bitfield('timer_use', 1,
                Bitfield.Bit('timer_use', 3),
                Bitfield.ReservedBit(3, 0),
                Bitfield.Bit('dont_stop', 1, 0),
                Bitfield.Bit('dont_log', 1, 0),
            ),
            Bitfield('timer_actions', 1,
                Bitfield.Bit('timeout_action', 3),
                Bitfield.ReservedBit(1, 0),
                Bitfield.Bit('pre_timeout_interrupt', 3),
                Bitfield.ReservedBit(1, 0),
            ),
            UnsignedInt('pre_timeout_interval', 1),
            UnsignedInt('timer_use_expiration_flags', 1),
            UnsignedInt('initial_countdown', 2),
    )


@register_message_class
class SetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_SET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetWatchdogTimerReq(Message):
    __cmdid__ = constants.CMDID_GET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetWatchdogTimerRsp(Message):
    __cmdid__ = constants.CMDID_GET_WATCHDOG_TIMER
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('timer_use', 1,
            Bitfield.Bit('timer_use', 3),
            Bitfield.ReservedBit(3, 0),
            Bitfield.Bit('is_running', 1, 0),
            Bitfield.Bit('dont_log', 1, 0),
        ),
        Bitfield('timer_actions', 1,
            Bitfield.Bit('timeout_action', 3),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('pre_timeout_interrupt', 3),
            Bitfield.ReservedBit(1, 0),
        ),
        UnsignedInt('pre_timeout_interval', 1),
        UnsignedInt('timer_use_expiration_flags', 1),
        UnsignedInt('initial_countdown', 2),
        UnsignedInt('present_countdown', 2),
    )
