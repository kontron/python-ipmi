# Copyright (c) 2014  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import RemainingBytes


@register_message_class
class GetSelInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SEL_INFO
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSelInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SEL_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('version', 1, default=0x51),
            UnsignedInt('entries', 2),
            UnsignedInt('free_bytes', 2),
            Timestamp('most_recent_addition'),
            Timestamp('most_recent_erase'),
            Bitfield('operation_support', 1,
                     Bitfield.Bit('get_sel_allocation_info', 1),
                     Bitfield.Bit('reserve_sel', 1),
                     Bitfield.Bit('partial_add_sel_entry', 1),
                     Bitfield.Bit('delete_sel', 1),
                     Bitfield.ReservedBit(3),
                     Bitfield.Bit('overflow_flag', 1)),
    )


@register_message_class
class GetSelAllocationInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SEL_ALLOCATION_INFO
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSelAllocationInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SEL_ALLOCATION_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('possible_alloc_units', 2),
            UnsignedInt('alloc_unit_size', 2),
            UnsignedInt('free_alloc_units', 2),
            UnsignedInt('largest_free_block', 2),
            UnsignedInt('max_record_size', 1)
    )


@register_message_class
class ReserveSelReq(Message):
    __cmdid__ = constants.CMDID_RESERVE_SEL
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class ReserveSelRsp(Message):
    __cmdid__ = constants.CMDID_RESERVE_SEL
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2)
    )


@register_message_class
class GetSelEntryReq(Message):
    __cmdid__ = constants.CMDID_GET_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('length', 1),
    )


@register_message_class
class GetSelEntryRsp(Message):
    __cmdid__ = constants.CMDID_GET_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('next_record_id', 2),
            RemainingBytes('record_data'),
    )


@register_message_class
class AddSelEntryReq(Message):
    __cmdid__ = constants.CMDID_ADD_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            ByteArray('record_data', 16),
    )


@register_message_class
class AddSelEntryRsp(Message):
    __cmdid__ = constants.CMDID_ADD_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2)
    )


@register_message_class
class PartialAddSelEntryReq(Message):
    __cmdid__ = constants.CMDID_PARTIAL_ADD_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            # 0 for the first part of a record
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            Bitfield('progress', 1,
                     # 0 partial add in progress, 1 last part of the record
                     Bitfield.Bit('in_progress', 4),
                     Bitfield.ReservedBit(4, 0),),
            RemainingBytes('record_data'),
    )


@register_message_class
class PartialAddSelEntryRsp(Message):
    __cmdid__ = constants.CMDID_PARTIAL_ADD_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2)
    )


@register_message_class
class DeleteSelEntryReq(Message):
    __cmdid__ = constants.CMDID_DELETE_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2)
    )


@register_message_class
class DeleteSelEntryRsp(Message):
    __cmdid__ = constants.CMDID_DELETE_SEL_ENTRY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2)
    )


@register_message_class
class ClearSelReq(Message):
    __cmdid__ = constants.CMDID_CLEAR_SEL
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            ByteArray('key', 3, default=b'CLR'),
            UnsignedInt('cmd', 1)
    )


@register_message_class
class ClearSelRsp(Message):
    __cmdid__ = constants.CMDID_CLEAR_SEL
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            Bitfield('status', 1,
                     Bitfield.Bit('erase_in_progress', 4),
                     Bitfield.ReservedBit(4),),
    )


@register_message_class
class GetSelTimeReq(Message):
    __cmdid__ = constants.CMDID_GET_SEL_TIME
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSelTimeRsp(Message):
    __cmdid__ = constants.CMDID_GET_SEL_TIME
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            Timestamp('timestamp'),
    )


@register_message_class
class SetSelTimeReq(Message):
    __cmdid__ = constants.CMDID_SET_SEL_TIME
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            Timestamp('timestamp'),
    )


@register_message_class
class SetSelTimeRsp(Message):
    __cmdid__ = constants.CMDID_SET_SEL_TIME
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetAuxiliaryLogStatusReq(Message):
    __cmdid__ = constants.CMDID_GET_AUXILIARY_LOG_STATUS
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            Bitfield('log', 1,
                     # 0 MCA log, 1 OEM 1, 2 OEM 2
                     Bitfield.Bit('type', 4),
                     Bitfield.ReservedBit(4, 0),),
    )


@register_message_class
class GetAuxiliaryLogStatusRsp(Message):
    __cmdid__ = constants.CMDID_GET_AUXILIARY_LOG_STATUS
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            # the log-specific status, not decoded
            RemainingBytes('log_data'),
    )


@register_message_class
class SetAuxiliaryLogStatusReq(Message):
    __cmdid__ = constants.CMDID_SET_AUXILIARY_LOG_STATUS
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            Bitfield('log', 1,
                     Bitfield.Bit('type', 4),
                     Bitfield.ReservedBit(4, 0),),
            RemainingBytes('log_data'),
    )


@register_message_class
class SetAuxiliaryLogStatusRsp(Message):
    __cmdid__ = constants.CMDID_SET_AUXILIARY_LOG_STATUS
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetSelTimeUtcOffsetReq(Message):
    __cmdid__ = constants.CMDID_GET_SEL_TIME_UTC_OFFSET
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSelTimeUtcOffsetRsp(Message):
    __cmdid__ = constants.CMDID_GET_SEL_TIME_UTC_OFFSET
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            # minutes, 2's complement, 0x07ff for unspecified
            UnsignedInt('offset', 2),
    )


@register_message_class
class SetSelTimeUtcOffsetReq(Message):
    __cmdid__ = constants.CMDID_SET_SEL_TIME_UTC_OFFSET
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('offset', 2),
    )


@register_message_class
class SetSelTimeUtcOffsetRsp(Message):
    __cmdid__ = constants.CMDID_SET_SEL_TIME_UTC_OFFSET
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
    )
