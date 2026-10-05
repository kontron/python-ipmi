#!/usr/bin/env python

from array import array
from unittest.mock import MagicMock, call

import pytest

from pyipmi.errors import CompletionCodeError, RetryError
from pyipmi.helper import (clear_repository_helper, get_sdr_data_helper,
                           ReadLength)
from pyipmi.msgs.constants import (REPOSITORY_ERASURE_COMPLETED,
                                   REPOSITORY_ERASURE_IN_PROGRESS,
                                   REPOSITORY_INITIATE_ERASE,
                                   REPOSITORY_GET_ERASE_STATUS,
                                   CC_CANT_RET_NUM_REQ_BYTES)


def test_clear_repository_helper():
    reserve_fn = MagicMock()
    reserve_fn.return_value = (0x1234)

    clear_fn = MagicMock()
    clear_fn.side_effect = [
        REPOSITORY_ERASURE_COMPLETED,
        REPOSITORY_ERASURE_IN_PROGRESS,
        REPOSITORY_ERASURE_COMPLETED,
    ]

    clear_repository_helper(reserve_fn, clear_fn)

    clear_calls = [
        call(REPOSITORY_INITIATE_ERASE, 0x1234),
        call(REPOSITORY_GET_ERASE_STATUS, 0x1234),
        call(REPOSITORY_GET_ERASE_STATUS, 0x1234),
    ]
    clear_fn.assert_has_calls(clear_calls)
    assert clear_fn.call_count == 3


class FakeSdrDevice:
    """Returns the chunks of one SDR, like the Get SDR command."""

    def __init__(self, record, max_length=32):
        self.record = record
        self.max_length = max_length
        self.requests = []

    def get(self, reservation_id, record_id, offset, length):
        self.requests.append((offset, length))
        # the 5 byte header can always be read
        if offset > 0 and length > self.max_length:
            raise CompletionCodeError(CC_CANT_RET_NUM_REQ_BYTES)
        return (0xffff, array('B', self.record[offset:offset + length]))


# 56 byte record: 5 byte header with a payload length of 51
SDR_RECORD = bytes([0x04, 0x00, 0x51, 0x01, 51]) + bytes(range(51))


def test_get_sdr_data_helper():
    device = FakeSdrDevice(SDR_RECORD)
    (next_id, data) = get_sdr_data_helper(lambda: 1, device.get, 4, 1)
    assert bytes(data) == SDR_RECORD
    assert next_id == 0xffff
    assert device.requests == [(0, 5), (5, 32), (37, 19)]


def test_get_sdr_data_helper_reduce_read_length():
    device = FakeSdrDevice(SDR_RECORD, max_length=22)
    read_length = ReadLength()
    (_, data) = get_sdr_data_helper(lambda: 1, device.get, 4, 1, read_length)
    # the rejected requests must not corrupt the record data
    assert bytes(data) == SDR_RECORD
    assert read_length.length == 20
    assert device.requests == [(0, 5), (5, 32), (5, 28), (5, 24), (5, 20),
                               (25, 20), (45, 11)]

    # the reduced length is used for the next record right away
    device.requests = []
    get_sdr_data_helper(lambda: 1, device.get, 4, 1, read_length)
    assert device.requests == [(0, 5), (5, 20), (25, 20), (45, 11)]


def test_get_sdr_data_helper_read_length_exhausted():
    device = FakeSdrDevice(SDR_RECORD, max_length=0)
    with pytest.raises(RetryError):
        get_sdr_data_helper(lambda: 1, device.get, 4, 1)
