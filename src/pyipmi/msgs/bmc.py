import constants
from pyipmi.msgs import Message
from pyipmi.msgs import ByteArray
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional
from pyipmi.msgs import Optional


class GetDeviceId(Message):
    CMDID = constants.CMDID_GET_DEVICE_ID
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('device_id', 1),
            Bitfield('device_revision', 1,
                Bitfield.Bit('device_revision',4),
                Bitfield.ReservedBit(3,0),
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


class ColdReset(Message):
    CMDID = constants.CMDID_COLD_RESET
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
        CompletionCode(),
    )


class WarmReset(Message):
    CMDID = constants.CMDID_WARM_RESET
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
        CompletionCode(),
    )


class ManufacturingTestOn(Message):
    CMDID = constants.CMDID_MANUFACTURING_TEST_ON
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
        CompletionCode(),
    )


class ResetWatchdogTimer(Message):
    CMDID = constants.CMDID_RESET_WATCHDOG_TIMER
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = (
    )
    _RSP_DESC = (
        CompletionCode(),
    )


class SetWatchdogTimer(Message):
    CMDID = constants.CMDID_SET_WATCHDOG_TIMER
    NETFN = constants.NETFN_APP
    LUN = 0
    _REQ_DESC = (
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
    _RSP_DESC = (
        CompletionCode(),
    )


class GetWatchdogTimer(Message):
    CMDID = constants.CMDID_GET_WATCHDOG_TIMER
    NETFN = constants.NETFN_APP
    LUN = 0

    _REQ_DESC = (
    )
    _RSP_DESC = (
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
