#!/usr/bin/env python

import pytest
from array import array

from pyipmi.lan import (data_to_ip_address, data_to_ip_source,
                        data_to_mac_address, data_to_vlan, ip_address_to_data,
                        ip_source_to_data, vlan_to_data)

from pyipmi.errors import DataNotFound
from pyipmi.msgs.constants import CHANNEL_MEDIUM_IPMB, CHANNEL_MEDIUM_LAN_802_3

from .ipmi_helper import create_ipmi


def test_datatoipaddress():
    assert data_to_ip_address(array('B', [192, 168, 1, 1])) == "192.168.1.1"


def test_ipaddresstodata():
    assert ip_address_to_data("192.168.1.1").array == array('B', [192, 168, 1, 1])


def test_datatoipsource():
    assert data_to_ip_source(array('B', [0])) == "unknown"
    assert data_to_ip_source(array('B', [1])) == "static"
    assert data_to_ip_source(array('B', [2])) == "dhcp"
    assert data_to_ip_source(array('B', [3])) == "bios"
    assert data_to_ip_source(array('B', [4])) == "other"


def test_ipsourcetodata():
    assert ip_source_to_data("static").array == array('B', [1])
    assert ip_source_to_data("dhcp").array == array('B', [2])


def test_ipsourcetodata_raise_valueerror():
    with pytest.raises(ValueError):
        ip_source_to_data("does not exist")


def test_datatomacaddress():
    assert data_to_mac_address(array('B', [0xab, 0xcd, 0xef, 0x12, 0x34, 0x56])) == "ab:cd:ef:12:34:56"


def test_datatovlan():
    assert data_to_vlan(array('B', [138, 129])) == 394
    assert data_to_vlan(array('B', [0, 0])) == 0
    assert data_to_vlan(array('B', [19, 128])) == 19


def test_datatovlan_deactivated():
    # Check if the data_to_vlan method returns 0 when a vlan data contains
    # non-null vlan ID but the "vlan activate" bit is set to 0
    assert data_to_vlan(array('B', [138, 1])) == 0


def test_vlantodata():
    assert vlan_to_data(394).array == array('B', [138, 129])
    assert vlan_to_data(0).array == array('B', [0, 0])
    assert vlan_to_data(19).array == array('B', [19, 128])


def test_vlantodata_raise_typeerror():
    with pytest.raises(TypeError):
        vlan_to_data("wrong type of argument")


def test_vlantodata_raise_valueerror():
    with pytest.raises(ValueError):
        vlan_to_data(4096)


def lan_rsp(data):
    # completion code, parameter revision, data
    return b'\x00\x11' + bytes(data)


def test_get_lan_config_param():
    ipmi = create_ipmi(lan_rsp([1, 2]))
    data = ipmi.get_lan_config_param(channel=1, parameter_selector=3)
    assert ipmi.requests == [
        ('GetLanConfigurationParametersReq', b'\x01\x03\x00\x00')]
    assert list(data) == [1, 2]


def test_get_lan_config_param_revision_only():
    ipmi = create_ipmi(lan_rsp([]))
    ipmi.get_lan_config_param(channel=1, parameter_selector=3,
                              revision_only=1)
    assert ipmi.requests == [
        ('GetLanConfigurationParametersReq', b'\x80\x00\x00\x00')]


def test_get_ip_address():
    ipmi = create_ipmi(lan_rsp([10, 0, 1, 224]))
    assert ipmi.get_ip_address(channel=1) == '10.0.1.224'
    assert ipmi.requests[0][1][:2] == b'\x01\x03'


def test_set_ip_address():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_ip_address('10.0.1.224', channel=1)
    assert ipmi.requests == [
        ('SetLanConfigurationParametersReq', b'\x01\x03\x0a\x00\x01\xe0')]


def test_get_ip_source():
    ipmi = create_ipmi(lan_rsp([2]))
    assert ipmi.get_ip_source(channel=1) == 'dhcp'


def test_set_ip_source():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_ip_source('static', channel=1)
    assert ipmi.requests == [
        ('SetLanConfigurationParametersReq', b'\x01\x04\x01')]


def test_get_mac_address():
    ipmi = create_ipmi(lan_rsp([0x00, 0x25, 0x90, 0xab, 0xcd, 0xef]))
    assert ipmi.get_mac_address(channel=1) == '00:25:90:ab:cd:ef'


def test_get_vlan_id():
    ipmi = create_ipmi(lan_rsp(vlan_to_data(100)))
    assert ipmi.get_vlan_id(channel=1) == 100


def test_set_vlan_id():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_vlan_id(100, channel=1)
    assert ipmi.requests == [
        ('SetLanConfigurationParametersReq',
         b'\x01\x14' + bytes(vlan_to_data(100)))]


def channel_info_rsp(channel, medium):
    # completion code, channel, medium, protocol, session, vendor, aux info
    return bytes([0, channel, medium, 0x01, 0x82, 0xf2, 0x1b, 0x00, 0, 0])


def test_get_lan_channel():
    ipmi = create_ipmi({
        'GetChannelInfo': [
            b'\xcc',                                  # channel 1 missing
            channel_info_rsp(2, CHANNEL_MEDIUM_IPMB),
            channel_info_rsp(3, CHANNEL_MEDIUM_LAN_802_3),
        ],
        'GetLanConfigurationParameters': [lan_rsp([10, 0, 1, 224]),
                                          lan_rsp([10, 0, 1, 224])],
    })
    assert ipmi.get_ip_address() == '10.0.1.224'
    assert [data for (name, data) in ipmi.requests
            if name == 'GetChannelInfoReq'] == [b'\x01', b'\x02', b'\x03']
    assert ipmi.requests[-1] == ('GetLanConfigurationParametersReq',
                                 b'\x03\x03\x00\x00')

    # the channel is looked up only once
    ipmi.requests = []
    ipmi.get_ip_address()
    assert [name for (name, _) in ipmi.requests] == [
        'GetLanConfigurationParametersReq']


def test_get_lan_channel_not_found():
    ipmi = create_ipmi({'GetChannelInfo': channel_info_rsp(
        1, CHANNEL_MEDIUM_IPMB)})
    with pytest.raises(DataNotFound):
        ipmi.get_lan_channel()


def test_explicit_channel_no_lookup():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_ip_address('10.0.1.224', channel=0)
    assert [name for (name, _) in ipmi.requests] == [
        'SetLanConfigurationParametersReq']


def test_get_channel_info():
    ipmi = create_ipmi(channel_info_rsp(1, CHANNEL_MEDIUM_LAN_802_3))
    info = ipmi.get_channel_info(1)
    assert ipmi.requests == [('GetChannelInfoReq', b'\x01')]
    assert info.channel == 1
    assert info.medium_type == CHANNEL_MEDIUM_LAN_802_3
    assert info.protocol_type == 1
    assert info.session_support == 2
    assert info.active_session_count == 2
    assert info.vendor_id == 0x1bf2
    assert str(info) == 'Channel 1: medium 0x04 protocol 0x01'
