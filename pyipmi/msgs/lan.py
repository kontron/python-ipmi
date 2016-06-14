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

import array

from . import constants
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

#from pyipmi.utils import ByteBuffer

@register_message_class
class SetLanConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_SET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT
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
    __fields__ = (
            CompletionCode(),
            Optional(ByteArray('auxiliary', 4))
    )


@register_message_class
class GetLanConfigurationParametersReq(Message):
    __cmdid__ = constants.CMDID_GET_LAN_CONFIGURATION_PARAMETERS
    __netfn__ = constants.NETFN_TRANSPORT
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
    __fields__ = (
            CompletionCode(),
            UnsignedInt('parameter_revision', 1, 0),
            RemainingBytes('data'),
    )

