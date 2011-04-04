import constants
from pyipmi.msgs import Message
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional

PICMG_IDENTIFIER = 0x00

LINK_INTERFACE_BASE = 0x0
LINK_INTERFACE_FABRIC = 0x1
LINK_INTERFACE_UPDATE_CHANNEL = 0x2

LINK_TYPE_BASE = 0x01
LINK_TYPE_ETHERNET_FABRIC = 0x02
LINK_TYPE_INFINIBAND_FABRIC = 0x03
LINK_TYPE_STARFABRIC_FABRIC = 0x04
LINK_TYPE_PCIEXPRESS_FABRIC = 0x05
LINK_TYPE_OEM0 = 0xf0
LINK_TYPE_OEM1 = 0xf1
LINK_TYPE_OEM2 = 0xf2
LINK_TYPE_OEM3 = 0xf3

LINK_TYPE_EXT_BASE0 = 0x00
LINK_TYPE_EXT_BASE1 = 0x01

LINK_TYPE_EXT_ETHERNET_FIX1000BX = 0x00
LINK_TYPE_EXT_ETHERNET_FIX10GBX4 = 0x01
LINK_TYPE_EXT_ETHERNET_FCPI = 0x02
LINK_TYPE_EXT_ETHERNET_FIX1000KX_10GKR = 0x03
LINK_TYPE_EXT_ETHERNET_FIX10GKX4 = 0x04
LINK_TYPE_EXT_ETHERNET_FIX40GKR4 = 0x05

LINK_TYPE_EXT_OEM_LINK_TYPE_EXT_0 = 0x00

LINK_FLAGS_LANE0 = 0x01
LINK_FLAGS_LANE0123 = 0x0f

LINK_STATE_DISABLE = 0
LINK_STATE_ENABLE = 1

CHANNEL_SIGNALING_CLASS_BASIC = 0
CHANNEL_SIGNALING_CLASS_10_3125GBD = 4

FRU_CONTROL_COLD_RESET = 0x00
FRU_CONTROL_WARM_RESET = 0x01
FRU_CONTROL_GRACEFUL_REBOOT = 0x02
FRU_CONTROL_ISSUE_DIAGNOSTIC_INTERRUPT = 0x03
FRU_CONTROL_QUIESCED = 0x04

LED_COLOR_BLUE = 0x01
LED_COLOR_RED = 0x02
LED_COLOR_GREEN = 0x03
LED_COLOR_AMBER = 0x04
LED_COLOR_ORANGE = 0x05
LED_COLOR_WHITE = 0x06

LED_FUNCTION_OFF = 0x00
LED_FUNCTION_BLINKING_RANGE = range(0x01, 0xfa)
LED_FUNCTION_ON = 0xff

class PicmgIdentifier(UnsignedInt):
    def __init__(self, name='picmg_identifier'):
        UnsignedInt.__init__(self, name, 1, PICMG_IDENTIFIER)


class FruControl(Message):
    CMDID = constants.CMDID_FRU_CONTROL
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('option', 1),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class SetFruActivationPolicy(Message):
    CMDID = constants.CMDID_SET_FRU_ACTIVATION_POLICY
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            Bitfield('mask', 1,
                Bitfield.Bit('activation_locked', 1, default=0),
                Bitfield.Bit('deactivation_locked', 1, default=0),
                Bitfield.ReservedBit(6),
            ),
            Bitfield('set', 1,
                Bitfield.Bit('activation_locked', 1, default=0),
                Bitfield.Bit('deactivation_locked', 1, default=0),
                Bitfield.ReservedBit(6),
            ),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class GetFruLedColorCapabilities(Message):
    CMDID = constants.CMDID_GET_FRU_LED_COLOR_CAPABILITIES
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('color_capabilities', 1,
                Bitfield.ReservedBit(1),
                Bitfield.Bit('blue', 1),
                Bitfield.Bit('red', 1),
                Bitfield.Bit('green', 1),
                Bitfield.Bit('amber', 1),
                Bitfield.Bit('orange', 1),
                Bitfield.Bit('white', 1),
                Bitfield.ReservedBit(1)
            ),
            UnsignedIntMask('local_def_color', 1, 0x0f),
            UnsignedIntMask('override_def_color', 1, 0x0f),
    )

class SetFruLedState(Message):
    CMDID = constants.CMDID_SET_FRU_LED_STATE
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0
    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
            UnsignedInt('led_function', 1),
            UnsignedInt('on_duration', 1),
            UnsignedIntMask('color', 1, 0x0f),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )


class GetFruLedState(Message):
    CMDID = constants.CMDID_GET_FRU_LED_STATE
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    def _cond_override(obj):
        return obj.led_states.override_en == 1

    def _cond_lamp_test(obj):
        return obj.led_states.lamp_test_en == 1

    _REQ_DESC = (
            PicmgIdentifier(),
            UnsignedInt('fru_id', 1),
            UnsignedInt('led_id', 1),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
            Bitfield('led_states', 1,
                Bitfield.Bit('local_avail', 1),
                Bitfield.Bit('override_en', 1),
                Bitfield.Bit('lamp_test_en', 1),
                Bitfield.ReservedBit(5)
            ),
            UnsignedInt('local_function', 1),
            UnsignedInt('local_on_duration', 1),
            UnsignedIntMask('local_color', 1, 0x0f),
            Conditional(_cond_override, UnsignedInt('override_function',
                1)),
            Conditional(_cond_override,
                UnsignedInt('override_on_duration', 1)),
            Conditional(_cond_override, UnsignedIntMask('override_color',
                1, 0x0f)),
            Conditional(_cond_lamp_test, UnsignedIntMask('lamp_test_duration',
                1, 0x7f)),
    )

class SetPortState(Message):
    CMDID = constants.CMDID_SET_PORT_STATE
    NETFN = constants.NETFN_GROUP_EXTENSION
    LUN = 0

    _REQ_DESC = (
            PicmgIdentifier(),
            Bitfield('link_info', 4,
                Bitfield.Bit('channel', 6),
                Bitfield.Bit('interface', 2),
                Bitfield.Bit('port_0', 1),
                Bitfield.Bit('port_1', 1),
                Bitfield.Bit('port_2', 1),
                Bitfield.Bit('port_3', 1),
                Bitfield.Bit('type', 8),
                Bitfield.Bit('type_extension', 4),
                Bitfield.Bit('grouping_id', 8, 0),
            ),
            UnsignedInt('state', 1),
    )
    _RSP_DESC = (
            CompletionCode(),
            PicmgIdentifier(),
    )
