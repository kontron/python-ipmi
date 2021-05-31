# Copyright (c) 2021  Kontron Europe GmbH
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

from __future__ import absolute_import

from . import constants
from . import register_message_class
from . import Message
from . import UnsignedInt
from . import UnsignedIntMask
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import RemainingBytes
from . import Optional
from . import GroupExtensionIdentifier


VITA_IDENTIFIER = 0x03


#class VitaIdentifier(UnsignedInt):
#    def __init__(self, name='picmg_identifier'):
#        super(PicmgIdentifier, self).__init__(name, 1, VITA_IDENTIFIER)


class VitaMessage(Message):
    __group_extension__ = VITA_IDENTIFIER


@register_message_class
class GetVsoCapabilitiesReq(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_VSO_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION
    __fields__ = (
        GroupExtensionIdentifier('vita_identifier', VITA_IDENTIFIER),
    )


@register_message_class
class GetVsoCapabilitiesRsp(VitaMessage):
    __cmdid__ = constants.CMDID_VITA_GET_VSO_CAPABILITIES
    __netfn__ = constants.NETFN_GROUP_EXTENSION | 1
    __fields__ = (
        CompletionCode(),
        GroupExtensionIdentifier('vita_identifier', VITA_IDENTIFIER),
#        UnsignedInt('unknown', 1),
#        UnsignedInt('unknown', 1),
#        UnsignedInt('vso_standard_revision', 1),
#        UnsignedInt('vita_spec_revision', 1),
    )
