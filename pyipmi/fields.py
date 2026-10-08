#!/usr/bin/env python


from __future__ import annotations

import array
from collections.abc import Sequence

from .errors import DecodingError
from .utils import py3_array_tobytes


class VersionField:
    """This class represent the Version fields defines by IPMI.

    Introduced with HPM the version field can hold additional auxiliary bytes.
    """

    VERSION_FIELD_LEN = 2
    VERSION_WITH_AUX_FIELD_LEN = 6

    def __init__(self, data: str | Sequence[int] | None = None) -> None:
        self.major: int | None = None
        self.minor: int | None = None
        if data:
            self._from_data(data)

    def _from_data(self, data: str | Sequence[int]) -> None:
        if isinstance(data, str):
            data = [ord(c) for c in data]

        buf = array.array('B', data)
        self._decode_data(buf[0:2])
        if len(buf) == self.VERSION_WITH_AUX_FIELD_LEN:
            self.auxiliary = buf[2:6]

    def __str__(self) -> str:
        return self.version_to_string()

    def _decode_data(self, data: array.array) -> None:
        """`data` is array.array."""
        self.major = data[0]

        if data[1] == 0xff:
            self.minor = data[1]
        elif data[1] <= 0x99:
            self.minor = int(py3_array_tobytes(data[1:2]).decode('bcd+'))
        else:
            raise DecodingError()

    def version_to_string(self) -> str:
        return ''.join(f"{self.major}.{self.minor}")


def _unpack6bitascii(data: Sequence[int]) -> str:
    """Unpack the 6bit ascii encoded string.

    The characters are packed in groups of 3 bytes, the last group can be
    shorter, e.g. 5 characters take 4 bytes.
    """
    count = len(data) * 8 // 6
    data = list(data) + [0] * (-len(data) % 3)
    string = ''
    for i in range(0, len(data), 3):
        d = data[i:i+3]
        string += chr(0x20 + (d[0] & 0x3f))
        string += chr(0x20 + (((d[0] & 0xc0) >> 6) | ((d[1] & 0xf) << 2)))
        string += chr(0x20 + (((d[1] & 0xf0) >> 4) | ((d[2] & 0x3) << 4)))
        string += chr(0x20 + ((d[2] & 0xfc) >> 2))
    return string[:count]


class TypeLengthString:
    """A field in the TYPE/LENGTH BYTE FORMAT.

    The format is specified by the Platform Management FRU Information
    Storage Definition v1.0.

    In addition the difference to the 'FRU Information Storage Definition' to
    the variant used in Type/Length for the Device ID String used in the SDR.
    """

    TYPE_FRU_BINARY = 0
    TYPE_SDR_UNICODE = 0
    TYPE_BCD_PLUS = 1
    TYPE_6BIT_ASCII = 2
    TYPE_ASCII_OR_UTF16 = 3

    def __init__(self, data: Sequence[int] | None = None, offset: int = 0,
                 force_lang_eng: bool = False, sdr: bool = False) -> None:
        if data:
            self._from_data(data, offset, force_lang_eng)

    def __str__(self) -> str:
        if self.field_type is self.TYPE_FRU_BINARY:
            return ' '.join(f'{b:02x}' for b in self.raw)
        else:
            return self.string.replace('\x00', '')

    def _from_data(self, data: Sequence[int], offset: int = 0,
                   force_lang_eng: bool = False) -> None:
        self.offset = offset
        self.field_type = data[offset] >> 6 & 0x3
        self.length = data[offset] & 0x3f

        self.raw = data[offset+1:offset+1+self.length]

        if self.field_type == self.TYPE_BCD_PLUS:
            self.string = bytes(self.raw).decode('bcd+')
        elif self.field_type == self.TYPE_6BIT_ASCII:
            self.string = _unpack6bitascii(self.raw)
        else:
            chr_data = ''.join([chr(c) for c in self.raw])
            self.string = chr_data


class FruTypeLengthString(TypeLengthString):

    def __init__(self, data: Sequence[int] | None = None, offset: int = 0,
                 force_lang_eng: bool = False) -> None:
        super().__init__(data, offset, force_lang_eng, sdr=False)


class SdrTypeLengthString(TypeLengthString):

    def __init__(self, data: Sequence[int] | None = None, offset: int = 0,
                 force_lang_eng: bool = False) -> None:
        super().__init__(data, sdr=True)
