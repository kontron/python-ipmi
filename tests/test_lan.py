#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from array import array

from pyipmi.lan import (data_to_ip_address, data_to_ip_source,
                        data_to_mac_address, data_to_vlan, ip_address_to_data,
                        ip_source_to_data, vlan_to_data)


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
