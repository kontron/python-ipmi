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

from pyipmi.errors import DecodingError, CompletionCodeError, RetryError
from pyipmi.utils import check_completion_code, ByteBuffer
from pyipmi.msgs import constants

import sdr

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
        except CompletionCodeError, e:
            if e.cc == constants.CC_CANT_RET_NUM_REQ_BYTES:
                # reduce max lenght
                max_req_len -= 4
                if max_req_len <= 0:
                    retry = 0
            else:
                Assert

        record_data.append_array(data[:])
        offset = len(record_data)
        if len(record_data) >= record_length:
            break

    return (next_id, record_data)


INITIATE_ERASE = 0xaa
GET_ERASE_STATUS = 0x00
ERASURE_IN_PROGRESS = 0x0
ERASURE_COMPLETED = 0x1

def clear_repository_helper(reserve_fn, clear_fn, retry=5, reservation=None):
    """Helper function to start repository erasure and wait until finish.
    This helper is used by clear_sel and clear_sdr_repository.
    """

    reservation = reserve_fn()

    # start erasure
    while True:
        retry -= 1
        if retry <= 0:
            raise RetryError()

        try:
            clear_fn(INITIATE_ERASE, reservation)
        except CompletionCodeError, e:
            if e.cc == constants.CC_RES_CANCELED:
                time.sleep(0.2)
                reservation = reserve_fn()
                continue
            else:
                check_completion_code(e.cc)

        break

    # give some time to clear
    time.sleep(0.5)

    # wait until finish
    while True:
        retry -= 1
        if retry <= 0:
            raise RetryError()

        try:
            in_progress = clear_fn(GET_ERASE_STATUS, reservation)
        except CompletionCodeError, e:
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
