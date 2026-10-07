#!/usr/bin/env python

from array import array
from unittest.mock import MagicMock

import pytest

from pyipmi import dcmi, interfaces, create_connection
from pyipmi.errors import CompletionCodeError
from pyipmi.msgs import create_response_by_name, encode_message


def create_rsp(total, record_ids):
    rsp = MagicMock()
    rsp.total_number_of_instances = total
    rsp.record_ids = record_ids
    return rsp


def record_ids_to_bytes(ids):
    data = []
    for record_id in ids:
        data.extend([record_id & 0xff, record_id >> 8])
    return data


class TestDcmi:

    def setup_method(self):
        interface = interfaces.create_interface('mock')
        self.ipmi = create_connection(interface)

    def test_get_dcmi_sensor_record_ids(self):
        rsps = [
            create_rsp(2, [0x01, 0x00, 0x02, 0x00]),
            create_rsp(1, [0x34, 0x12]),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_by_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == [0x0001, 0x0002,
                                                           0x1234]
        assert self.ipmi.send_message_by_name.call_count == 3

    def test_get_dcmi_sensor_record_ids_more_than_8_instances(self):
        rsps = [
            # air inlet: 10 instances, need two requests
            create_rsp(10, record_ids_to_bytes(range(0x10, 0x18))),
            create_rsp(10, record_ids_to_bytes(range(0x18, 0x1a))),
            # cpu and baseboard
            create_rsp(0, []),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_by_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == \
            list(range(0x10, 0x1a))

        calls = self.ipmi.send_message_by_name.call_args_list
        assert len(calls) == 4
        assert calls[0].kwargs['entity_instance_start'] == 0
        assert calls[1].kwargs['entity_instance_start'] == 8

    def test_get_dcmi_sensor_record_ids_overlapping_responses(self):
        # BMC counts the instance start 1 based, the second response
        # repeats the last record ID of the first response
        rsps = [
            create_rsp(9, record_ids_to_bytes(range(1, 9))),
            create_rsp(9, record_ids_to_bytes(range(8, 10))),
            create_rsp(0, []),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_by_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == list(range(1, 10))

    def test_get_dcmi_sensor_record_ids_stops_without_new_ids(self):
        # BMC reports more instances than it returns record IDs for
        rsps = [
            create_rsp(5, record_ids_to_bytes([1, 2])),
            create_rsp(5, record_ids_to_bytes([1, 2])),
            create_rsp(0, []),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_by_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == [1, 2]

    def test_get_temperature_readings(self):
        rsps = [
            # 9 instances, second instance is negative (-5 degree)
            create_rsp(9, [0x2d, 1, 0x85, 2, 0x20, 3, 0x21, 4,
                           0x22, 5, 0x23, 6, 0x24, 7, 0x25, 8]),
            create_rsp(9, [0x26, 9]),
        ]
        for rsp in rsps:
            rsp.readings = rsp.record_ids
        self.ipmi.send_message_by_name = MagicMock(side_effect=rsps)

        readings = self.ipmi.get_temperature_readings(0x40)

        assert readings[:2] == [(1, 45), (2, -5)]
        assert readings[-1] == (9, 38)
        assert len(readings) == 9
        calls = self.ipmi.send_message_by_name.call_args_list
        assert calls[0].args == ('GetTemperatureReadings',)
        assert calls[0].kwargs['entity_id'] == 0x40
        assert calls[1].kwargs['entity_instance_start'] == 8

    def test_set_power_limit(self):
        self.ipmi.send_message_by_name = MagicMock()
        self.ipmi.set_power_limit(300, 1000, 5,
                                  dcmi.POWER_LIMIT_EXCEPTION_HARD_POWER_OFF)
        self.ipmi.send_message_by_name.assert_called_once_with(
            'SetPowerLimit', exception_actions=1, power_limit=300,
            correction_time_limit=1000, statistics_sampling_period=5)

    def test_activate_deactivate_power_limit(self):
        self.ipmi.send_message_by_name = MagicMock()
        self.ipmi.activate_power_limit()
        self.ipmi.send_message_by_name.assert_called_with(
            'ActivateDeactivatePowerLimit', activation=1)
        self.ipmi.deactivate_power_limit()
        self.ipmi.send_message_by_name.assert_called_with(
            'ActivateDeactivatePowerLimit', activation=0)

    def test_set_thermal_limit(self):
        rsp = create_response_by_name('SetThermalLimit')
        self.ipmi.send_message = MagicMock(return_value=rsp)

        self.ipmi.set_thermal_limit(0x40, 1, 45, 300, hard_power_off=True)

        req = self.ipmi.send_message.call_args.args[0]
        assert encode_message(req) == b'\xdc\x40\x01\xc0\x2d\x2c\x01'

    def test_set_thermal_limit_error(self):
        rsp = create_response_by_name('SetThermalLimit')
        rsp.completion_code = 0x84
        self.ipmi.send_message = MagicMock(return_value=rsp)

        with pytest.raises(CompletionCodeError) as e:
            self.ipmi.set_thermal_limit(0x40, 1, 200, 300)
        assert e.value.cc_desc == 'temperature limit out of range'

    def test_set_dcmi_configuration_parameters(self):
        self.ipmi.send_message_by_name = MagicMock()
        self.ipmi.set_dcmi_configuration_parameters(
            dcmi.CONF_PARAM_DHCP_TIMING_1, b'\x40')
        self.ipmi.send_message_by_name.assert_called_once_with(
            'SetDcmiConfigurationParameters', parameter_selector=3,
            set_selector=0, parameter_data=b'\x40')


class FakeStringBmc:
    """Serves the get/set string commands from a buffer."""

    def __init__(self, data=b''):
        self.data = bytearray(data)
        self.requests = []

    def __call__(self, name, offset, number_of_bytes, data=None):
        self.requests.append((name, offset, number_of_bytes))
        rsp = MagicMock()
        if name.startswith('Set'):
            assert len(data) == number_of_bytes <= 16
            self.data[offset:offset + number_of_bytes] = data
        else:
            rsp.data = array('B', self.data[offset:offset + number_of_bytes])
        rsp.total_length = len(self.data)
        return rsp


class TestDcmiStrings:

    def setup_method(self):
        interface = interfaces.create_interface('mock')
        self.ipmi = create_connection(interface)

    def test_get_asset_tag(self):
        bmc = FakeStringBmc(b'asset tag with more than 16 chars')
        self.ipmi.send_message_by_name = bmc

        assert self.ipmi.get_asset_tag() == 'asset tag with more than 16 chars'
        assert bmc.requests == [('GetAssetTag', 0, 0),
                                ('GetAssetTag', 0, 16),
                                ('GetAssetTag', 16, 16),
                                ('GetAssetTag', 32, 1)]

    def test_get_asset_tag_empty(self):
        bmc = FakeStringBmc()
        self.ipmi.send_message_by_name = bmc

        assert self.ipmi.get_asset_tag() == ''
        assert len(bmc.requests) == 1

    def test_set_asset_tag(self):
        bmc = FakeStringBmc()
        self.ipmi.send_message_by_name = bmc

        self.ipmi.set_asset_tag('a' * 20)

        assert bytes(bmc.data) == b'a' * 20
        assert bmc.requests == [('SetAssetTag', 0, 16),
                                ('SetAssetTag', 16, 4)]

    def test_set_asset_tag_too_long(self):
        with pytest.raises(ValueError):
            self.ipmi.set_asset_tag('a' * 65)

    def test_get_management_controller_id_string(self):
        bmc = FakeStringBmc(b'my-bmc\x00')
        self.ipmi.send_message_by_name = bmc

        assert self.ipmi.get_management_controller_id_string() == 'my-bmc'
        assert bmc.requests[0] == ('GetManagementControllerIdString', 0, 1)

    def test_set_management_controller_id_string(self):
        bmc = FakeStringBmc()
        self.ipmi.send_message_by_name = bmc

        self.ipmi.set_management_controller_id_string('my-bmc')

        # the string is written null terminated
        assert bytes(bmc.data) == b'my-bmc\x00'

    def test_set_management_controller_id_string_too_long(self):
        with pytest.raises(ValueError):
            self.ipmi.set_management_controller_id_string('a' * 64)
