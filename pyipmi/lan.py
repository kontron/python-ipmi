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

"""LAN configuration commands.

The LAN configuration parameters of the BMC configure its LAN channel,
e.g. the IP address, the IP address source and the VLAN. The commands are
the methods of :class:`Lan`, which are available on :class:`pyipmi.Ipmi`.
The ``LAN_PARAMETER_*`` constants are the parameter selectors and the
values of the IP address source parameter.

If no channel is given, the commands use the first LAN channel of the BMC,
see :meth:`Lan.get_lan_channel`.

Example:
    Print the network configuration of the BMC::

        print(ipmi.get_ip_address(), ipmi.get_ip_source(),
              ipmi.get_mac_address(), ipmi.get_vlan_id())
"""

from __future__ import annotations

from array import array

from .errors import CompletionCodeError, DataNotFound
from .msgs import constants, create_request_by_name
from .utils import check_rsp_completion_code, ByteBuffer
from .mixin import IpmiMixin

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

CONVERT_RAW_TO_IP_SRC = {
    0: "unknown",
    1: "static",
    2: "dhcp",
    3: "bios",
    4: "other"
}


def data_to_ip_address(data: array) -> str:
    """Convert the IP address response data to a string.

    Args:
        data: The parameter data of
            `GetLanConfigurationParameters(LAN_PARAMETER_IP_ADDRESS)`.

    Returns:
        The IP address in the format xxx.xxx.xxx.xxx.
    """
    return '.'.join(map(str, data))


def ip_address_to_data(ip_address: str) -> ByteBuffer:
    """Convert an IP address string to request data.

    Args:
        ip_address: The IP address in the format xxx.xxx.xxx.xxx.

    Returns:
        The parameter data of
        `SetLanConfigurationParameters(LAN_PARAMETER_IP_ADDRESS)`.

    Raises:
        ValueError: A part of the IP address is not a number.
    """
    return ByteBuffer(map(int, ip_address.split('.')))


def data_to_ip_source(data: array) -> str:
    """Convert the IP address source response data to a string.

    Args:
        data: The parameter data of
            `GetLanConfigurationParameters(LAN_PARAMETER_IP_ADDRESS_SOURCE)`.

    Returns:
        The IP address source, one of the values of
        ``CONVERT_RAW_TO_IP_SRC``: ``'unknown'``, ``'static'``, ``'dhcp'``,
        ``'bios'`` or ``'other'``.

    Raises:
        KeyError: The IP address source is reserved.
    """
    # The ip source is encoded in the last 4 bits of the response
    return CONVERT_RAW_TO_IP_SRC[data[0] & 0b1111]


def ip_source_to_data(ip_source: str) -> ByteBuffer:
    """Convert an IP address source string to request data.

    Args:
        ip_source: ``'static'`` or ``'dhcp'``.

    Returns:
        The parameter data of
        `SetLanConfigurationParameters(LAN_PARAMETER_IP_ADDRESS_SOURCE)`.

    Raises:
        ValueError: The IP address source is not ``'static'`` or
            ``'dhcp'``.
    """
    if ip_source == "dhcp":
        data = ByteBuffer([2])
    elif ip_source == "static":
        data = ByteBuffer([1])
    else:
        raise ValueError(f"Unknown value for ip_source argument: {ip_source}. Possible values are: dhcp, static.")
    return data


def data_to_mac_address(data: array) -> str:
    """Convert the MAC address response data to a string.

    Args:
        data: The parameter data of
            `GetLanConfigurationParameters(LAN_PARAMETER_MAC_ADDRESS)`.

    Returns:
        The MAC address in the format aa:bb:cc:dd:ee:ff.
    """
    return ':'.join([f"{i:02x}" for i in data])


def data_to_vlan(data: array) -> int:
    """Convert the VLAN ID response data to an integer.

    Args:
        data: The parameter data of
            `GetLanConfigurationParameters(LAN_PARAMETER_802_1Q_VLAN_ID)`.

    Returns:
        The VLAN ID, 0 if the VLAN is disabled.
    """
    # Check if the vlan is enabled. We return vlan = 0 for a disabled vlan as a
    # convention.
    if data[1] >> 7 == 0:
        return 0

    # The vlan ID must be extracted from the response, according to IPMI
    # specification.
    #
    #   Example with VLAN ID = 394
    #   The raw response to `get_lan_config_param` will be [138, 129]
    #   The binary representation will be :
    #
    #       |    data[0]   |  |    data[1]   |
    # Rsp : 1 0 0 0  1 0 1 0  1 0 0 0  0 0 0 1
    #       ^              ^           ^     ^
    #       |--------------|           |-----|
    #       |least sign. bits          |most sign. bits
    #
    # By rearranging the bits order, we get the VLAN value :
    #       0 0 0 0  0 0 0 1  1 0 0 0  1 0 1 0 = 394
    return ((data[1] & 0b1111) << 8) | data[0]


def vlan_to_data(vlan: int) -> ByteBuffer:
    """Convert a VLAN ID to request data.

    Args:
        vlan: The VLAN ID (1 - 4095), 0 to disable the VLAN.

    Returns:
        The parameter data of
        `SetLanConfigurationParameters(LAN_PARAMETER_802_1Q_VLAN_ID)`.

    Raises:
        TypeError: The VLAN ID is not an int.
        ValueError: The VLAN ID is greater than 4095.
    """
    if not isinstance(vlan, int):
        raise TypeError(f"Wrong type for vlan argument: {type(vlan)}, expected int.")
    elif vlan > 4095:
        raise ValueError(f"Wrong value for vlan argument: {vlan}. It cannot be greater than 4095.")

    if vlan == 0:
        # We want to deactivate the vlan (no vlan)
        data = ByteBuffer([0, 0])
    else:
        # We want to set the vlan ID
        # first separate the two bytes of the vlan
        least_sign_byte = vlan & 0b11111111
        most_sign_byte = (vlan >> 8) & 0b1111
        # then create the vlan enabled bit
        vlan_enable = 0b10000000
        # finally we concatenate every byte together
        data = ByteBuffer([least_sign_byte, vlan_enable | most_sign_byte])
    return data


# channels to look for the LAN channel, 0 is the primary IPMB channel
LAN_CHANNEL_SEARCH_RANGE = range(1, 0x0c)


class Lan(IpmiMixin):
    """LAN configuration commands, available on :class:`pyipmi.Ipmi`."""

    def __init__(self) -> None:
        """Initialize the LAN command group."""
        self._lan_channel: int | None = None

    def get_lan_channel(self) -> int:
        """Return the number of the first 802.3 LAN channel.

        The channel is looked up with Get Channel Info once per connection,
        the channels 1 - 11 are searched.

        Returns:
            The channel number.

        Raises:
            DataNotFound: The BMC has no LAN channel.
        """
        if self._lan_channel is None:
            for channel in LAN_CHANNEL_SEARCH_RANGE:
                try:
                    info = self.get_channel_info(channel)
                except CompletionCodeError:
                    # channel not implemented
                    continue
                if info.medium_type == constants.CHANNEL_MEDIUM_LAN_802_3:
                    self._lan_channel = channel
                    break
            else:
                raise DataNotFound('no LAN channel found')
        return self._lan_channel

    def _channel(self, channel: int | None) -> int:
        return self.get_lan_channel() if channel is None else channel

    def get_lan_config_param(self, channel: int | None = None,
                             parameter_selector: int = 0,
                             set_selector: int = 0, block_selector: int = 0,
                             revision_only: int = 0) -> array:
        """Get a LAN configuration parameter.

        Args:
            channel: The channel number, the LAN channel if None.
            parameter_selector: The parameter, one of the
                ``LAN_PARAMETER_*`` constants.
            set_selector: The set selector of the parameter.
            block_selector: The block selector of the parameter.
            revision_only: 1 to get only the parameter revision, the other
                arguments are not used then.

        Returns:
            The parameter data.

        Raises:
            CompletionCodeError: The BMC rejected the request, e.g. for an
                unsupported parameter.
        """
        req = create_request_by_name('GetLanConfigurationParameters')
        req.command.get_parameter_revision_only = revision_only
        if revision_only != 1:
            req.command.channel_number = self._channel(channel)
            req.parameter_selector = parameter_selector
            req.set_selector = set_selector
            req.block_selector = block_selector
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)
        return rsp.data

    def set_lan_config_param(self, channel: int | None,
                             parameter_selector: int, data: ByteBuffer) -> None:
        """Set a LAN configuration parameter.

        Args:
            channel: The channel number, the LAN channel if None.
            parameter_selector: The parameter, one of the
                ``LAN_PARAMETER_*`` constants.
            data: The parameter data.

        Raises:
            CompletionCodeError: The BMC rejected the request, e.g. for a
                read-only parameter.
        """
        req = create_request_by_name('SetLanConfigurationParameters')
        req.command.channel_number = self._channel(channel)
        req.parameter_selector = parameter_selector
        req.data = data
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def get_ip_address(self, channel: int | None = None) -> str:
        """Return the IP address of the BMC.

        Args:
            channel: The channel number, the LAN channel if None.

        Returns:
            The IP address in the format xxx.xxx.xxx.xxx.
        """
        ip_address_raw = self.get_lan_config_param(channel, LAN_PARAMETER_IP_ADDRESS)
        return data_to_ip_address(ip_address_raw)

    def set_ip_address(self, ip_address: str,
                       channel: int | None = None) -> None:
        """Set the IP address of the BMC.

        Args:
            ip_address: The IP address in the format xxx.xxx.xxx.xxx.
            channel: The channel number, the LAN channel if None.

        Warning:
            Changing the IP address of the BMC makes a current LAN session
            unusable, because it still uses the former IP address. Open a
            new session with the new IP address for the following calls if
            a LAN interface is used.
        """
        data = ip_address_to_data(ip_address)
        self.set_lan_config_param(channel, LAN_PARAMETER_IP_ADDRESS, data)

    def get_ip_source(self, channel: int | None = None) -> str:
        """Return the IP address source of the BMC.

        Args:
            channel: The channel number, the LAN channel if None.

        Returns:
            ``'unknown'``, ``'static'``, ``'dhcp'``, ``'bios'`` or
            ``'other'``.
        """
        ip_source_raw = self.get_lan_config_param(channel, LAN_PARAMETER_IP_ADDRESS_SOURCE)
        return data_to_ip_source(ip_source_raw)

    def set_ip_source(self, ip_source: str,
                      channel: int | None = None) -> None:
        """Set the IP address source of the BMC.

        Args:
            ip_source: ``'static'`` or ``'dhcp'``.
            channel: The channel number, the LAN channel if None.

        Warning:
            Changing the IP address source may change the IP address of the
            BMC, which makes a current LAN session unusable, because it
            still uses the former IP address. Open a new session with the new
            IP address for the following calls if a LAN interface is used.
        """
        data = ip_source_to_data(ip_source)
        self.set_lan_config_param(channel, LAN_PARAMETER_IP_ADDRESS_SOURCE, data)

    def get_mac_address(self, channel: int | None = None) -> str:
        """Return the MAC address of the BMC.

        Args:
            channel: The channel number, the LAN channel if None.

        Returns:
            The MAC address in the format aa:bb:cc:dd:ee:ff.
        """
        mac_address_raw = self.get_lan_config_param(channel, LAN_PARAMETER_MAC_ADDRESS)
        return data_to_mac_address(mac_address_raw)

    def get_vlan_id(self, channel: int | None = None) -> int:
        """Return the 802.1q VLAN ID of the BMC.

        Args:
            channel: The channel number, the LAN channel if None.

        Returns:
            The VLAN ID, 0 if the VLAN is disabled.
        """
        vlan_id_raw = self.get_lan_config_param(channel, LAN_PARAMETER_802_1Q_VLAN_ID)
        return data_to_vlan(vlan_id_raw)

    def set_vlan_id(self, vlan: int, channel: int | None = None) -> None:
        """Set the 802.1q VLAN ID of the BMC.

        Args:
            vlan: The VLAN ID (1 - 4095), 0 to disable the VLAN.
            channel: The channel number, the LAN channel if None.

        Warning:
            Changing the VLAN ID may change the IP address of the BMC,
            depending on the network configuration. This makes a current LAN
            session unusable, because it still uses the former IP address.
            Open a new session with the new IP address for the following
            calls if a LAN interface is used.
        """
        data = vlan_to_data(vlan)
        self.set_lan_config_param(channel, LAN_PARAMETER_802_1Q_VLAN_ID, data)


class LanParameter:
    """Placeholder for a LAN configuration parameter, it is not used."""
