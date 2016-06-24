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
from . import UnsignedInt
from . import UnsignedIntMask
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import RemainingBytes
from . import VariableByteArray

@register_message_class
class GetFruInventoryAreaInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_FRU_INVENTORY_AREA_INFO
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
        UnsignedInt('fru_id', 1, 0),
    )


@register_message_class
class GetFruInventoryAreaInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_FRU_INVENTORY_AREA_INFO
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('area_size', 2),
        Bitfield('area_info', 1,
            Bitfield.Bit('access', 1),
            Bitfield.ReservedBit(7,0)
        ),
    )


@register_message_class
class ReadFruDataReq(Message):
    __cmdid__ = constants.CMDID_READ_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
            UnsignedInt('fru_id', 1),
            UnsignedInt('offset', 2),
            UnsignedInt('count', 1),
    )


@register_message_class
class ReadFruDataRsp(Message):
    __cmdid__ = constants.CMDID_READ_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE | 1

    def _length_count(obj):
        return obj.count

    __fields__ = (
            CompletionCode(),
            UnsignedInt('count', 1),
            VariableByteArray('data', _length_count),
    )


@register_message_class
class WriteFruDataReq(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE
    __fields__ = (
        UnsignedInt('fru_id', 1),
        UnsignedInt('offset', 2),
        RemainingBytes('data'),
    )


@register_message_class
class WriteFruDataRsp(Message):
    __cmdid__ = constants.CMDID_WRITE_FRU_DATA
    __netfn__ = constants.NETFN_STORAGE | 1
    __fields__ = (
        CompletionCode(),
        UnsignedInt('count_written', 1)
    )
