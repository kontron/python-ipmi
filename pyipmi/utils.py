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

import codecs
from array import array
from typing import Any, Generator, TYPE_CHECKING
from .msgs import constants
from .errors import DecodingError, CompletionCodeError

if TYPE_CHECKING:
    # `pyipmi.msgs.message` imports `ByteBuffer` from this module, so the
    # `Message` type can only be imported here for static type checking,
    # not at runtime, without causing a circular import.
    from .msgs import Message


def py3enc_unic_bytes_fix(dat: Any) -> Any:
    if isinstance(dat, str):
        dat = dat.encode('raw_unicode_escape')
    return dat


def py3dec_unic_bytes_fix(dat: bytes) -> str:
    return dat.decode('raw_unicode_escape')


def py3_array_frombytes(msg: array, data: bytes) -> None:
    return msg.frombytes(data)


def py3_array_tobytes(msg: array) -> bytes:
    return msg.tobytes()


def check_completion_code(cc: int) -> None:
    if cc != constants.CC_OK:
        raise CompletionCodeError(cc)


def check_rsp_completion_code(rsp: Message) -> None:
    """
    Check the completion code of a specific response and raise
    CompletionCodeError in case there's an error.

    This method allows to pass more metadata than the `check_completion_code`
    method to try to interpret command-specific completion codes description in
    case there is an error.

    `rsp` should be a subclass of `Message` here.
    """
    if rsp.completion_code != constants.CC_OK:
        raise CompletionCodeError(
            rsp.completion_code,
            cmdid=rsp.cmdid,
            netfn=rsp.netfn & 0xfe,  # Get the request NetFn from response NetFn
            group_extension=rsp.group_extension)


def chunks(data: Any, count: int) -> Generator[Any, None, None]:
    for i in range(0, len(data), count):
        yield data[i:i+count]


class ByteBuffer(object):
    def __init__(self, data: Any = None) -> None:

        if data is not None:
            self.array = array('B', data)
        else:
            self.array = array('B')

    def push_unsigned_int(self, value: int, length: int) -> None:
        for i in range(length):
            self.array.append((value >> (8*i) & 0xff))

    def pop_unsigned_int(self, length: int) -> int:
        value = 0
        for i in range(length):
            try:
                value |= self.array.pop(0) << (8*i)
            except IndexError:
                raise DecodingError('Data too short for message')
        return value

    def push_string(self, value: str | bytes) -> None:
        if isinstance(value, str):
            # Encode Unicode to UTF-8
            value = value.encode()
        py3_array_frombytes(self.array, value)

    def pop_string(self, length: int) -> bytes:
        string = self.array[0:length]
        del self.array[0:length]
        return py3_array_tobytes(string)

    def pop_slice(self, length: int) -> ByteBuffer:
        if len(self.array) < length:
            raise DecodingError('Data too short for message')

        c = ByteBuffer(self.array[0:length])
        self.__delslice__(0, length)
        return c

    def tobytes(self) -> bytes:
        return self.array.tobytes()

    def tostring(self) -> bytes:
        return py3_array_tobytes(self.array)

    def extend(self, data: Any) -> None:
        self.array.extend(data)

    def append_array(self, a: Any) -> None:
        self.array.extend(a)

    def __getslice__(self, a: int, b: int) -> array:
        return self.array[a:b]

    def __delslice__(self, a: int, b: int) -> None:
        del self.array[a:b]

    def __len__(self) -> int:
        return len(self.array)

    def __getitem__(self, idx: int) -> int:
        return self.array[idx]


BCD_MAP = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '.']


def bcd_encode(input: str, errors: str = 'strict') -> None:
    raise NotImplementedError()


def bcd_decode(encoded_input: Any) -> tuple[str, int]:
    chars = list()
    try:
        for data in encoded_input:
            chars.append(BCD_MAP[data >> 4 & 0xf] + BCD_MAP[data & 0xf])
        return (''.join(chars), len(encoded_input) * 2)
    except IndexError:
        raise ValueError()


def bcd_search(name: str) -> codecs.CodecInfo | None:
    # Python 3.9 normalizes 'bcd+' as 'bcd_'
    if name not in ('bcd+', 'bcd'):
        return None
    return codecs.CodecInfo(name='bcd+', encode=bcd_encode, decode=bcd_decode)


def is_string(string: Any) -> bool:
    return isinstance(string, str)
