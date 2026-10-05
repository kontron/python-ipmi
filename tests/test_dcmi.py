#!/usr/bin/env python

from unittest.mock import MagicMock

from pyipmi import interfaces, create_connection


class TestDcmi:

    def test_get_dcmi_sensor_record_ids(self):
        rsps = []
        for record_ids in ([0x01, 0x00, 0x02, 0x00], [0x34, 0x12], []):
            rsp = MagicMock()
            rsp.record_ids = record_ids
            rsps.append(rsp)

        interface = interfaces.create_interface('mock')
        ipmi = create_connection(interface)
        ipmi.send_message_with_name = MagicMock(side_effect=rsps)

        assert ipmi.get_dcmi_sensor_record_ids() == [0x0001, 0x0002, 0x1234]
