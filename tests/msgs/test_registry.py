from nose.tools import eq_, raises

import pyipmi.msgs
from pyipmi.msgs import create_message, create_response_message, create_response_by_name, create_request_by_name


def test_create_message():
    req = create_message(6, 1, None)
    eq_(type(req), pyipmi.msgs.bmc.GetDeviceIdReq)
    req = create_message(7, 1, None)
    eq_(type(req), pyipmi.msgs.bmc.GetDeviceIdRsp)


def test_create_response():
    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    rsp = create_response_message(req)
    eq_(type(rsp), pyipmi.msgs.bmc.GetDeviceIdRsp)


def test_create_request_by_name():
    req = create_request_by_name('GetDeviceId')
    eq_(type(req), pyipmi.msgs.bmc.GetDeviceIdReq)


def test_create_response_by_name():
    rsp = create_response_by_name('GetDeviceId')
    eq_(type(rsp), pyipmi.msgs.bmc.GetDeviceIdRsp)
