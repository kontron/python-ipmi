"""Helpers for testing the high level Ipmi functions."""

from unittest.mock import MagicMock

import pyipmi
from pyipmi.msgs import create_response_message, decode_message, encode_message


def create_ipmi(rsp_data):
    """Create an Ipmi object answering requests with canned responses.

    `rsp_data` is either the encoded response for every request, or a dict
    mapping the command name (e.g. 'ReserveSel') to the encoded response or
    a list of encoded responses, which are returned in order.

    The sent requests are collected in `ipmi.requests` as
    (message name, encoded data) tuples.
    """
    ipmi = pyipmi.create_connection(MagicMock())
    ipmi.target = pyipmi.Target(0x20)
    ipmi.requests = []

    def send_and_receive(req):
        name = type(req).__name__
        ipmi.requests.append((name, encode_message(req)))
        data = rsp_data
        if isinstance(rsp_data, dict):
            data = rsp_data[name[:-3]]
            if isinstance(data, list):
                data = data.pop(0)
        rsp = create_response_message(req)
        decode_message(rsp, data)
        return rsp

    ipmi.interface.send_and_receive.side_effect = send_and_receive
    return ipmi
