from __future__ import absolute_import
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import Optional
from . import RemainingBytes
from . import VariableByteArray

@register_message_class
class GetSdrRepositoryInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_INFO
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSdrRepositoryInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('sdr_version', 1),
            UnsignedInt('record_count', 2),
            UnsignedInt('free_space', 2),
            Timestamp('most_recent_addition'),
            Timestamp('most_recent_erase'),
            Bitfield('support', 1,
                Bitfield.Bit('get_allocation_info', 1),
                Bitfield.Bit('reserve', 1),
                Bitfield.Bit('partial_add', 1),
                Bitfield.Bit('delete', 1),
                Bitfield.ReservedBit(1, 0),
                Bitfield.Bit('update_type', 2),
                Bitfield.Bit('overflow_flag', 1)
            ),
    )


@register_message_class
class GetSdrRepositoryAllocationInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_ALLOCATION_INFO
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class GetSdrRepositoryAllocationInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_ALLOCATION_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('number_of_units', 2),
            UnsignedInt('unit_size', 2),
            UnsignedInt('free_units', 2),
            UnsignedInt('largest_free_block', 2),
            UnsignedInt('maximum_record_size', 1)
    )


@register_message_class
class ReserveSdrRepositoryReq(Message):
    __cmdid__ = constants.CMDID_RESERVE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_STORAGE


@register_message_class
class ReserveSdrRepositoryRsp(Message):
    __cmdid__ = constants.CMDID_RESERVE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2),
    )


@register_message_class
class GetSdrReq(Message):
    __cmdid__ = constants.CMDID_GET_SDR
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('bytes_to_read', 1),
    )


@register_message_class
class GetSdrRsp(Message):
    __cmdid__ = constants.CMDID_GET_SDR
    __netfn__ = constants.NETFN_STORAGE | 1

    __fields__ = (
            CompletionCode(),
            UnsignedInt('next_record_id', 2),
            RemainingBytes('record_data'),
    )


@register_message_class
class AddSdrReq(Message):
    __cmdid__ = constants.CMDID_ADD_SDR
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            RemainingBytes('record_data'),
    )


@register_message_class
class AddSdrRsp(Message):
    __cmdid__ = constants.CMDID_ADD_SDR
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2),
    )


@register_message_class
class PartialAddSdrReq(Message):
    __cmdid__ = constants.CMDID_PARTIAL_ADD_SDR
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            Bitfield('status', 1,
                Bitfield.Bit('in_progress', 4),
                Bitfield.ReservedBit(4, 0),
            ),
            RemainingBytes('record_data'),
    )


@register_message_class
class PartialAddSdrRsp(Message):
    __cmdid__ = constants.CMDID_PARTIAL_ADD_SDR
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2),
    )


@register_message_class
class DeleteSdrReq(Message):
    __cmdid__ = constants.CMDID_DELETE_SDR
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
    )


@register_message_class
class DeleteSdrRsp(Message):
    __cmdid__ = constants.CMDID_DELETE_SDR
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('record_id', 2),
    )


@register_message_class
class ClearSdrRepositoryReq(Message):
    __cmdid__ = constants.CMDID_CLEAR_SDR_REPOSITORY
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('reservation_id', 2),
            ByteArray('key', 3, default='CLR'),
            UnsignedInt('cmd', 1)
    )


@register_message_class
class ClearSdrRepositoryRsp(Message):
    __cmdid__ = constants.CMDID_CLEAR_SDR_REPOSITORY
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            Bitfield('status', 1,
                Bitfield.Bit('erase_in_progress', 4),
                Bitfield.ReservedBit(4, 0),
            ),
    )


@register_message_class
class RunInitializationAgentReq(Message):
    __cmdid__ = constants.CMDID_RUN_INITIALIZATION_AGENT
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('cmd', 1),
    )


@register_message_class
class RunInitializationAgentRsp(Message):
    __cmdid__ = constants.CMDID_RUN_INITIALIZATION_AGENT
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
            CompletionCode(),
            Bitfield('status', 1,
                Bitfield.Bit('initialization_completed', 1),
                Bitfield.ReservedBit(7, 0),
            ),
    )

