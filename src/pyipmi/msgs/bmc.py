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

SELFTEST_RESULT_CORRUPTED_DATA_OR_INACCESSIBLE_DEVICE = 0x57

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
class GetSelftestResultsReq(Message):
    __cmdid__ = constants.CMDID_GET_SELF_TEST_RESULTS
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetSelftestResultsRsp(Message):
    __cmdid__ = constants.CMDID_GET_SELF_TEST_RESULTS
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0

    def __init__(self, *args, **kwargs):
        self.completion_code = 0
        self.result = 0
        self.status = 0
        Message.__init__(self, *args, **kwargs)

    def _decode(self, data):
        data = ByteBuffer(data)
        self.completion_code = data.pop_unsigned_int(1)
        if (self.completion_code != constants.CC_OK):
            return
        self.result = data.pop_unsigned_int(1)
        self.status = data.pop_unsigned_int(1)

        if self.result == SELFTEST_RESULT_CORRUPTED_DATA_OR_INACCESSIBLE_DEVICE:
            tmp = self.status
            self.cannot_access_sel_device = (tmp & 0x80) >> 7
            self.cannot_access_sdr_device = (tmp & 0x40) >> 6
            self.cannot_access_bmc_fru_device = (tmp & 0x20) >> 5
            self.ipmb_signal_lines_do_not_respond = (tmp & 0x10) >> 4
            self.sdr_repository_empty = (tmp & 0x08) >> 3
            self.internal_use_area_corrupted = (tmp & 0x04) >> 2
            self.controller_bootblock_corrupted = (tmp & 0x02) >> 1
            self.controller_firmware_corrupted = (tmp & 0x01) >> 0


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


@register_message_class
class SetBmcGlobalEnablesReq(Message):
    __cmdid__ = constants.CMDID_SET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = (
        Bitfield('enables', 1,
            Bitfield.Bit('receive_message_queue_interrupt', 1, 0),
            Bitfield.Bit('event_message_buffer_full_interrupt', 1, 0),
            Bitfield.Bit('event_message_buffer', 1, 0),
            Bitfield.Bit('system_event_logging', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('oem_0', 1, 0),
            Bitfield.Bit('oem_1', 1, 0),
            Bitfield.Bit('oem_2', 1, 0),
        ),
    )


@register_message_class
class SetBmcGlobalEnablesRsp(Message):
    __cmdid__ = constants.CMDID_SET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetBmcGlobalEnablesReq(Message):
    __cmdid__ = constants.CMDID_GET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetBmcGlobalEnablesRsp(Message):
    __cmdid__ = constants.CMDID_GET_BMC_GLOBAL_ENABLES
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('enables', 1,
            Bitfield.Bit('receive_message_queue_interrupt', 1, 0),
            Bitfield.Bit('event_message_buffer_full_interrupt', 1, 0),
            Bitfield.Bit('event_message_buffer', 1, 0),
            Bitfield.Bit('system_event_logging', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('oem_0', 1, 0),
            Bitfield.Bit('oem_1', 1, 0),
            Bitfield.Bit('oem_2', 1, 0),
        ),
    )


@register_message_class
class ClearMessageFlagsReq(Message):
    __cmdid__ = constants.CMDID_CLEAR_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = (
        Bitfield('clear', 1,
            Bitfield.Bit('receive_message_queue', 1, 0),
            Bitfield.Bit('event_message_buffer', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('watchdog_pretimeout_interrupt_flag', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('oem_0', 1, 0),
            Bitfield.Bit('oem_1', 1, 0),
            Bitfield.Bit('oem_2', 1, 0),
        ),
    )


@register_message_class
class ClearMessageFlagsRsp(Message):
    __cmdid__ = constants.CMDID_CLEAR_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetMessageFlagsReq(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetMessageFlagsRsp(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE_FLAGS
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('flag', 1,
            Bitfield.Bit('receive_message_available', 1, 0),
            Bitfield.Bit('event_message_buffer_full', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('watchdog_pretimeout_interrupt_occurred', 1, 0),
            Bitfield.ReservedBit(1, 0),
            Bitfield.Bit('oem_0', 1, 0),
            Bitfield.Bit('oem_1', 1, 0),
            Bitfield.Bit('oem_2', 1, 0),
        ),
    )


@register_message_class
class EnableMessageChannelReceiveReq(Message):
    __cmdid__ = constants.CMDID_ENABLE_MESSAGE_CHANNEL_RECEIVE
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = (
        Bitfield('channel', 2,
            Bitfield.Bit('number', 4, 0),
            Bitfield.ReservedBit(4, 0),
            Bitfield.Bit('state', 2, 0),
            Bitfield.ReservedBit(6, 0),
        ),
    )


@register_message_class
class EnableMessageChannelReceiveRsp(Message):
    __cmdid__ = constants.CMDID_ENABLE_MESSAGE_CHANNEL_RECEIVE
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('channel', 2,
            Bitfield.Bit('number', 4, 0),
            Bitfield.ReservedBit(4, 0),
            Bitfield.Bit('state', 1, 0),
            Bitfield.ReservedBit(7, 0),
        ),
    )


@register_message_class
class GetMessageReq(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetMessageRsp(Message):
    __cmdid__ = constants.CMDID_GET_MESSAGE
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        Bitfield('channel_number', 1,
            Bitfield.Bit('channel_number', 4, 0),
            Bitfield.Bit('privilege_level', 4, 0),
        ),
        RemainingBytes('data'),
    )


@register_message_class
class ReadEventMessageBufferReq(Message):
    __cmdid__ = constants.CMDID_READ_EVENT_MESSAGE_BUFFER
    __netfn__ = constants.NETFN_APP
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class ReadEventMessageBufferRsp(Message):
    __cmdid__ = constants.CMDID_READ_EVENT_MESSAGE_BUFFER
    __netfn__ = constants.NETFN_APP | 1
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
        RemainingBytes('event_data'),
    )
