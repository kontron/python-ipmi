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

# from builtins import object

from .msgs import create_request_by_name
# from .errors import DecodingError, CompletionCodeError
from .utils import check_completion_code, ByteBuffer

LAN_PARAMETER_SET_IN_PROGRESS = 0
LAN_PARAMETER_AUTHENTICATION_TYPE_SUPPORT = 1
LAN_PARAMETER_AUTHENTICATION_TYPE_ENABLE = 2
LAN_PARAMETER_IP_ADDRESS = 3
LAN_PARAMETER_IP_ADDRESS_SOURCE = 4
LAN_PARAMETER_MAC_ADDRESS = 5
LAN_PARAMETER_SUBNET_MASK = 6
LAN_PARAMETER_IPV4_HEADER_PARAMETERS = 7
LAN_PARAMETER_PRIMARY_RMCP_PORT = 8
LAN_PARAMETER_SECONDARY_RMCP_PORT = 9
LAN_PARAMETER_BMC_GENERATED_ARP_CONTROL = 10
LAN_PARAMETER_GRATUITOUS_ARP_INTERVAL = 11
LAN_PARAMETER_DEFAULT_GATEWAY_ADDRESS = 12
LAN_PARAMETER_DEFAULT_GATEWAY_MAC_ADDRESS = 13
LAN_PARAMETER_BACKUP_GATEWAY_ADDRESS = 14
LAN_PARAMETER_BACKUP_GATEWAY_MAC_ADDRESS = 15
LAN_PARAMETER_COMMUNITY_STRING = 16
LAN_PARAMETER_NUMBER_OF_DESTINATIONS = 17
LAN_PARAMETER_DESTINATION_TYPE = 18
LAN_PARAMETER_DESTINATION_ADDRESSES = 19
# following parameters are introduced with IPMI v2.0/RMCP+
LAN_PARAMETER_802_1Q_VLAN_ID = 20
LAN_PARAMETER_802_1Q_VLAN_PRIORITY = 21
LAN_PARAMETER_RMCP_PLUS_MESSAGING_CIPHER_SUITE_ENTRY_SUPPORT = 22
LAN_PARAMETER_RMCP_PLUS__MESSAGING_CIPHER_SUITE_ENTRIES = 23
LAN_PARAMETER_RMCP_PLUS_MESSAGING_CIPHER_SUITE_PRIVILEGE_LEVES = 24
LAN_PARAMETER_DESTINATION_ADDRESS_VLAN_TAGS = 25

LAN_PARAMETER_IP_ADDRESS_SOURCE_UNSPECIFIED = 0
LAN_PARAMETER_IP_ADDRESS_SOURCE_STATIC = 1
LAN_PARAMETER_IP_ADDRESS_SOURCE_DHCP = 2
LAN_PARAMETER_IP_ADDRESS_SOURCE_BIOS_OR_SYSTEM_SOFTWARE = 3
LAN_PARAMETER_IP_ADDRESS_SOURCE_BMC_OTHER_PROTOCOL = 4

class Lan(object):
    def get_lan_configuration_parameters(self, channel=0, parameter_selector=0,
            set_selector=0, block_selector=0, revision_only=0):
        req = create_request_by_name('GetLanConfigurationParameters')
        req.command.get_parameter_revision_only = revision_only
        if revision_only is not 1:
            req.command.channel_number = channel
            req.parameter_selector = parameter_selector
            req.set_selector = set_selector
            req.block_selector = block_selector
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.data

    def set_lan_configuration_parameters(self, channel, parameter_selector, data):
        req = create_request_by_name('SetLanConfigurationParameters')
        req.command.channel_number = channel
        req.parameter_selector = parameter_selector
        req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)


class LanParameter(object):
    pass
