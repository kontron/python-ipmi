import constants
from msgs import Message
from msgs import UnsignedInt
from msgs import Timestamp
from msgs import Bitfield
from msgs import CompletionCode

class GetSDRRepositoryInfo(Message):
    CMDID = constants.CMDID_GET_SDR_REPOSITORY_INFO
    NETFN = constants.NETFN_STORAGE
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('sdr_version', 1),
            UnsignedInt('record_count', 2),
            UnsignedInt('free_space', 2),
            Timestamp('most_recent_addtion'),
            Timestamp('most_recent_erase'),
            Bitfield('operation_support', 1,
                Bitfield.Bit('get_sdr_repository_allocation_command', 1),
                Bitfield.Bit('reverse_sdr_repository_command', 1),
                Bitfield.Bit('partial_add_sdr_command', 1),
                Bitfield.Bit('delete_sdr_command', 1),
                Bitfield.ReservedBit(1, 0),
                Bitfield.Bit('sdr_repository_update_type', 2),
                Bitfield.Bit('overflow_flag', 1)
            ),
    )


