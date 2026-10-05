#!/usr/bin/env python

from unittest.mock import MagicMock

from pyipmi import interfaces, create_connection


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
        self.ipmi.send_message_with_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == [0x0001, 0x0002,
                                                           0x1234]
        assert self.ipmi.send_message_with_name.call_count == 3

    def test_get_dcmi_sensor_record_ids_more_than_8_instances(self):
        rsps = [
            # air inlet: 10 instances, need two requests
            create_rsp(10, record_ids_to_bytes(range(0x10, 0x18))),
            create_rsp(10, record_ids_to_bytes(range(0x18, 0x1a))),
            # cpu and baseboard
            create_rsp(0, []),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_with_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == \
            list(range(0x10, 0x1a))

        calls = self.ipmi.send_message_with_name.call_args_list
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
        self.ipmi.send_message_with_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == list(range(1, 10))

    def test_get_dcmi_sensor_record_ids_stops_without_new_ids(self):
        # BMC reports more instances than it returns record IDs for
        rsps = [
            create_rsp(5, record_ids_to_bytes([1, 2])),
            create_rsp(5, record_ids_to_bytes([1, 2])),
            create_rsp(0, []),
            create_rsp(0, []),
        ]
        self.ipmi.send_message_with_name = MagicMock(side_effect=rsps)

        assert self.ipmi.get_dcmi_sensor_record_ids() == [1, 2]
