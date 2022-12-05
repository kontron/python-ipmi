#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, raises
from array import array

from pyipmi.lan import (data_to_ip_address, data_to_ip_source,
                        data_to_mac_address, data_to_vlan, ip_address_to_data,
                        ip_source_to_data, vlan_to_data)


def test_datatoipaddress():
    eq_(data_to_ip_address(array('B', [192, 168, 1, 1])), "192.168.1.1")

def test_ipaddresstodata():
    eq_(ip_address_to_data("192.168.1.1").array, array('B', [192, 168, 1, 1]))

def test_datatoipsource():
    eq_(data_to_ip_source(array('B', [0])), "unknown")
    eq_(data_to_ip_source(array('B', [1])), "static")
    eq_(data_to_ip_source(array('B', [2])), "dhcp")
    eq_(data_to_ip_source(array('B', [3])), "bios")
    eq_(data_to_ip_source(array('B', [4])), "other")

def test_ipsourcetodata():
    eq_(ip_source_to_data("static").array, array('B', [1]))
    eq_(ip_source_to_data("dhcp").array, array('B', [2]))

@raises(ValueError)
def test_ipsourcetodata_raise_valueerror():
    ip_source_to_data("does not exist")

def test_datatomacaddress():
    eq_(data_to_mac_address(array('B', [0xab, 0xcd, 0xef, 0x12, 0x34, 0x56])), "ab:cd:ef:12:34:56")

def test_datatovlan():
    eq_(data_to_vlan(array('B', [138, 129])), 394)
    eq_(data_to_vlan(array('B', [0, 0])), 0)
    eq_(data_to_vlan(array('B', [19, 128])), 19)

def test_vlantodata():
    eq_(vlan_to_data(394).array, array('B', [138, 129]))
    eq_(vlan_to_data(0).array, array('B', [0, 0]))
    eq_(vlan_to_data(19).array, array('B', [19, 128]))

@raises(TypeError)
def test_vlantodata_raise_typeerror():
    vlan_to_data("wrong type of argument")

@raises(ValueError)
def test_vlantodata_raise_valueerror():
    vlan_to_data(4096)
