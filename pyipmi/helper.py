# Copyright (c) 2014  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

from __future__ import annotations

import time
from array import array
from collections.abc import Callable

from .errors import CompletionCodeError, RetryError
from .utils import check_completion_code, ByteBuffer
from .msgs import constants, Message


# bytes per read request (Get SDR, Read FRU Data), like ipmitool
DEFAULT_READ_LENGTH = 32


def get_sdr_chunk_helper(send_fn: Callable[[Message], Message], req: Message,
                         retry: int = 5) -> Message:
    """Send a request for a chunk of a record and return the response.

    The request is sent again if the device is busy.

    Raises:
        CompletionCodeError: The request failed, e.g. with
            ``CC_RES_CANCELED`` if the reservation was canceled. The record
            has to be read again from the start then, see
            :func:`get_sdr_data_helper`.
        RetryError: The device is still busy after `retry` tries.
    """
    while True:
        retry -= 1
        if retry == 0:
            raise RetryError()
        rsp = send_fn(req)
        if rsp.completion_code == constants.CC_OK:
            break
        elif rsp.completion_code == constants.CC_TIMEOUT:
            time.sleep(0.1)
            continue
        elif rsp.completion_code == constants.CC_RESP_COULD_NOT_BE_PRV:
            time.sleep(0.1 * retry)
            continue
        else:
            check_completion_code(rsp.completion_code)

    return rsp


class ReadLength:
    """Number of bytes requested per read command (Get SDR, Read FRU Data).

    Starts with `DEFAULT_READ_LENGTH` and is reduced if the device cannot
    return that many bytes. Use the same instance for all reads from a device,
    so the reduced length has to be found only once.
    """

    def __init__(self, length: int = DEFAULT_READ_LENGTH) -> None:
        self.length = length

    def reduce(self, failed_length: int, step: int) -> None:
        """Reduce the length after a request of `failed_length` bytes failed.

        Raises RetryError if no bytes are left.
        """
        self.length = min(self.length, failed_length - step)
        if self.length <= 0:
            raise RetryError()


def get_sdr_data_helper(reserve_fn: Callable[[], int],
                        get_fn: Callable[[int, int, int, int],
                                         tuple[int, array]],
                        record_id: int,
                        reservation_id: int | None = None,
                        read_length: ReadLength | None = None,
                        retry: int = 5) -> tuple[int, ByteBuffer, int]:
    """Helper function to retrieve the sdr data.

    A specified helper function is used to retrieve the chunks.

    This can be used for SDRs from the Sensor Device or form the SDR
    repository.

    If the reservation is canceled, e.g. because the repository changed, the
    repository is reserved again and the record is read again from the
    start, so the record data is never mixed from before and after a change.

    Returns:
        The next record ID, the record data and the reservation ID, which is
        a new one if the reservation was canceled. Use it for the next
        records.

    Raises:
        RetryError: The reservation was canceled `retry` times.
    """
    if reservation_id is None:
        reservation_id = reserve_fn()
    if read_length is None:
        read_length = ReadLength()

    while True:
        try:
            (next_id, record_data) = _get_sdr_data(get_fn, record_id,
                                                   reservation_id,
                                                   read_length)
            return (next_id, record_data, reservation_id)
        except CompletionCodeError as e:
            if e.cc != constants.CC_RES_CANCELED:
                raise
            retry -= 1
            if retry <= 0:
                raise RetryError() from e
            time.sleep(1)
            reservation_id = reserve_fn()


def _get_sdr_data(get_fn: Callable[[int, int, int, int], tuple[int, array]],
                  record_id: int, reservation_id: int,
                  read_length: ReadLength) -> tuple[int, ByteBuffer]:
    (next_id, data) = get_fn(reservation_id, record_id, 0, 5)

    header = ByteBuffer(data)
    record_id = header.pop_unsigned_int(2)
    record_version = header.pop_unsigned_int(1)  # noqa:F841
    record_type = header.pop_unsigned_int(1)  # noqa:F841
    record_payload_length = header.pop_unsigned_int(1)
    record_length = record_payload_length + 5
    record_data = ByteBuffer(data)

    offset = len(record_data)
    retry = 20

    # now get the other record data
    while True:
        retry -= 1
        if retry == 0:
            raise RetryError()

        length = min(read_length.length, record_length - offset)

        try:
            (next_id, data) = get_fn(reservation_id, record_id, offset, length)
        except CompletionCodeError as e:
            if e.cc != constants.CC_CANT_RET_NUM_REQ_BYTES:
                raise
            # reduce the length and retry this chunk
            read_length.reduce(length, 4)
            continue

        record_data.extend(data[:])
        offset = len(record_data)
        if len(record_data) >= record_length:
            break

    return (next_id, record_data)


def _clear_repository(reserve_fn: Callable[[], int], clear_fn: Callable,
                      ctrl: int, retry: int, reservation: int) -> int:
    while True:
        retry -= 1
        if retry <= 0:
            raise RetryError()

        try:
            in_progress = clear_fn(ctrl, reservation)
        except CompletionCodeError as e:
            if e.cc == constants.CC_RES_CANCELED:
                time.sleep(0.2)
                reservation = reserve_fn()
                continue
            else:
                check_completion_code(e.cc)

        if in_progress == constants.REPOSITORY_ERASURE_IN_PROGRESS:
            time.sleep(0.5)
            continue

        break
    return reservation


def clear_repository_helper(reserve_fn: Callable[[], int], clear_fn: Callable,
                            retry: int = 5,
                            reservation: int | None = None) -> None:
    """Helper function to start repository erasure and wait until finish.

    This helper is used by clear_sel and clear_sdr_repository.
    """
    if reservation is None:
        reservation = reserve_fn()

    # start erasure
    reservation = _clear_repository(reserve_fn, clear_fn,
                                    constants.REPOSITORY_INITIATE_ERASE,
                                    retry, reservation)

    # give some time to clear
    time.sleep(0.5)

    # wait until finish
    reservation = _clear_repository(reserve_fn, clear_fn,
                                    constants.REPOSITORY_GET_ERASE_STATUS,
                                    retry, reservation)
