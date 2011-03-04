import constants
from pyipmi.msgs import Message
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import UnsignedIntMask
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional


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
            Bitfield('firmware_revision', 1,
                Bitfield.Bit('major_revision', 7),
                Bitfield.Bit('device_available', 1)
            ),
            UnsignedInt('minor_firmware_revision', 1),
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
            UnsignedInt('auxiliary_0', 1),
            UnsignedInt('auxiliary_1', 1),
            UnsignedInt('auxiliary_2', 1),
            UnsignedInt('auxiliary_3', 1),
            
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
