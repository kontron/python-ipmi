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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


import array
import time

from .errors import DecodingError, CompletionCodeError, RetryError
from .utils import check_completion_code, ByteBuffer
from .msgs import constants

#from . import sdr #unused

def get_sdr_chunk_helper(send_fn, req, reserve_fn, retry=5):

    while True:
        retry -= 1
        if retry == 0:
            raise RetryError()
        rsp = send_fn(req)
        if rsp.completion_code == constants.CC_OK:
            break
        elif rsp.completion_code == constants.CC_RES_CANCELED:
            req.reservation_id = reserve_fn()
            time.sleep(0.1)
            continue
        elif rsp.completion_code == constants.CC_TIMEOUT:
            time.sleep(0.1)
            continue
        elif rsp.completion_code == constants.CC_RESP_COULD_NOT_BE_PRV:
            time.sleep(0.1 * retry)
            continue
        else:
            check_completion_code(rsp.completion_code)

    return rsp

def get_sdr_data_helper(reserve_fn, get_fn, record_id, reservation_id=None):
    """Helper function to retrieve the sdr data using the specified
    functions.

    This can be used for SDRs from the Sensor Device or form the SDR
    repository.
    """

    if reservation_id is None:
        reservation_id = reserve_fn()

    (next_id, data) = get_fn(reservation_id, record_id, 0, 5)

    header = ByteBuffer(data)
    record_id = header.pop_unsigned_int(2)
    record_version = header.pop_unsigned_int(1)
    record_type = header.pop_unsigned_int(1)
    record_payload_length = header.pop_unsigned_int(1)
    record_length = record_payload_length + 5
    record_data = ByteBuffer(data)

    offset = len(record_data)
    max_req_len = 20
    retry = 20

    # now get the other record data
    while True:
        retry -= 1
        if retry == 0:
            raise RetryError()

        length = max_req_len
        if (offset + length) > record_length:
            length = record_length - offset

        try:
            (next_id, data) = get_fn(reservation_id, record_id, offset, length)
        except CompletionCodeError as e:
            if e.cc == constants.CC_CANT_RET_NUM_REQ_BYTES:
                # reduce max lenght
                max_req_len -= 4
                if max_req_len <= 0:
                    retry = 0
            else:
                raise CompletionCodeError(e.cc)

        record_data.extend(data[:])
        offset = len(record_data)
        if len(record_data) >= record_length:
            break

    return (next_id, record_data)


INITIATE_ERASE = 0xaa
GET_ERASE_STATUS = 0x00

ERASURE_IN_PROGRESS = 0x0
ERASURE_COMPLETED = 0x1

def _clear_repository(reserve_fn, clear_fn, ctrl, retry, reservation):
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

        if in_progress == ERASURE_IN_PROGRESS:
            time.sleep(0.5)
            continue

        break
    return reservation

def clear_repository_helper(reserve_fn, clear_fn, retry=5, reservation=None):
    """Helper function to start repository erasure and wait until finish.
    This helper is used by clear_sel and clear_sdr_repository.
    """

    if reservation is None:
        reservation = reserve_fn()

    # start erasure
    reservation = _clear_repository(reserve_fn, clear_fn,
            INITIATE_ERASE, retry, reservation)

    # give some time to clear
    time.sleep(0.5)

    # wait until finish
    reservation = _clear_repository(reserve_fn, clear_fn,
            GET_ERASE_STATUS, retry, reservation)
