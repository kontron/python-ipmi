#!/usr/bin/env python

from array import array
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from pyipmi.errors import CompletionCodeError, RetryError
from pyipmi.helper import (clear_repository_helper, get_sdr_chunk_helper,
                           get_sdr_data_helper, ReadLength)
from pyipmi.msgs.constants import (REPOSITORY_ERASURE_COMPLETED,
                                   REPOSITORY_ERASURE_IN_PROGRESS,
                                   REPOSITORY_INITIATE_ERASE,
                                   REPOSITORY_GET_ERASE_STATUS,
                                   CC_CANT_RET_NUM_REQ_BYTES, CC_INV_CMD,
                                   CC_OK, CC_RES_CANCELED,
                                   CC_RESP_COULD_NOT_BE_PRV, CC_TIMEOUT)


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
    (next_id, data, reservation_id) = get_sdr_data_helper(lambda: 1,
                                                          device.get, 4, 1)
    assert bytes(data) == SDR_RECORD
    assert next_id == 0xffff
    assert reservation_id == 1
    assert device.requests == [(0, 5), (5, 32), (37, 19)]


def test_get_sdr_data_helper_reduce_read_length():
    device = FakeSdrDevice(SDR_RECORD, max_length=22)
    read_length = ReadLength()
    (_, data, _) = get_sdr_data_helper(lambda: 1, device.get, 4, 1,
                                       read_length)
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


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr('pyipmi.helper.time.sleep', lambda t: None)


def chunk_rsp(cc):
    # the command of a Get SDR response, for the error description
    return SimpleNamespace(completion_code=cc, cmdid=0x23, netfn=0x0b,
                           group_extension=None)


@pytest.mark.parametrize('cc', [CC_TIMEOUT, CC_RESP_COULD_NOT_BE_PRV])
def test_get_sdr_chunk_helper_retry(no_sleep, cc):
    send_fn = MagicMock(side_effect=[chunk_rsp(cc), chunk_rsp(CC_OK)])
    rsp = get_sdr_chunk_helper(send_fn, SimpleNamespace())
    assert rsp.completion_code == CC_OK
    assert send_fn.call_count == 2


def test_get_sdr_chunk_helper_reservation_canceled(no_sleep):
    # the record has to be read again from the start, see
    # get_sdr_data_helper()
    send_fn = MagicMock(return_value=chunk_rsp(CC_RES_CANCELED))
    with pytest.raises(CompletionCodeError) as e:
        get_sdr_chunk_helper(send_fn, SimpleNamespace(reservation_id=1))
    assert e.value.cc == CC_RES_CANCELED
    assert send_fn.call_count == 1


def test_get_sdr_chunk_helper_error():
    send_fn = MagicMock(return_value=chunk_rsp(CC_INV_CMD))
    with pytest.raises(CompletionCodeError):
        get_sdr_chunk_helper(send_fn, SimpleNamespace())


def test_get_sdr_chunk_helper_retry_exhausted(no_sleep):
    send_fn = MagicMock(return_value=chunk_rsp(CC_TIMEOUT))
    with pytest.raises(RetryError):
        get_sdr_chunk_helper(send_fn, SimpleNamespace())
    assert send_fn.call_count == 4


class CancelingSdrDevice(FakeSdrDevice):
    """Cancels the reservation once, before the chunk at `cancel_offset`."""

    def __init__(self, record, cancel_offset):
        super().__init__(record)
        self.cancel_offset = cancel_offset
        self.reservation_id = 1
        self.reservations = []

    def reserve(self):
        self.reservation_id += 1
        return self.reservation_id

    def get(self, reservation_id, record_id, offset, length):
        if offset == self.cancel_offset:
            self.cancel_offset = None
            self.reservation_id += 1
        self.reservations.append(reservation_id)
        if reservation_id != self.reservation_id:
            self.requests.append((offset, length))
            raise CompletionCodeError(CC_RES_CANCELED)
        return super().get(reservation_id, record_id, offset, length)


@pytest.mark.parametrize('cancel_offset', [0, 5, 37])
def test_get_sdr_data_helper_reservation_canceled(no_sleep, cancel_offset):
    device = CancelingSdrDevice(SDR_RECORD, cancel_offset)
    (_, data, reservation_id) = get_sdr_data_helper(device.reserve,
                                                    device.get, 4, 1)
    assert bytes(data) == SDR_RECORD
    # reserved once again, the new reservation is returned for the next
    # records
    assert reservation_id == 3
    assert set(device.reservations) == {1, 3}
    # the record is read again from the start, not only the failed chunk
    assert device.requests[-3:] == [(0, 5), (5, 32), (37, 19)]


def test_get_sdr_data_helper_reservation_canceled_retry_exhausted(no_sleep):
    def get_fn(reservation_id, record_id, offset, length):
        raise CompletionCodeError(CC_RES_CANCELED)
    reserve_fn = MagicMock(return_value=2)
    with pytest.raises(RetryError):
        get_sdr_data_helper(reserve_fn, get_fn, 4, 1)
    assert reserve_fn.call_count == 4


def test_get_sdr_data_helper_other_error():
    def get_fn(reservation_id, record_id, offset, length):
        if offset:
            raise CompletionCodeError(CC_INV_CMD)
        return (0xffff, array('B', SDR_RECORD[:5]))
    with pytest.raises(CompletionCodeError):
        get_sdr_data_helper(lambda: 1, get_fn, 4)


def test_clear_repository_helper_reservation_canceled(no_sleep):
    reserve_fn = MagicMock(side_effect=[0x1234, 0x5678])
    clear_fn = MagicMock(side_effect=[
        CompletionCodeError(CC_RES_CANCELED),
        REPOSITORY_ERASURE_COMPLETED,
        REPOSITORY_ERASURE_COMPLETED,
    ])
    clear_repository_helper(reserve_fn, clear_fn)
    assert clear_fn.call_args_list[-1] == call(REPOSITORY_GET_ERASE_STATUS,
                                               0x5678)


def test_clear_repository_helper_error():
    clear_fn = MagicMock(side_effect=CompletionCodeError(CC_INV_CMD))
    with pytest.raises(CompletionCodeError):
        clear_repository_helper(lambda: 1, clear_fn)


def test_clear_repository_helper_retry_exhausted(no_sleep):
    clear_fn = MagicMock(return_value=REPOSITORY_ERASURE_IN_PROGRESS)
    with pytest.raises(RetryError):
        clear_repository_helper(lambda: 1, clear_fn)
