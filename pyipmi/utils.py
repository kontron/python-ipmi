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

import sys
import codecs
from array import array
from .msgs import constants
from .errors import DecodingError, CompletionCodeError


_PY3 = (sys.version_info >= (3,))


def py3enc_unic_bytes_fix(dat):
    # python 3 unicode fix
    if isinstance(dat, str) and _PY3:
        dat = dat.encode('raw_unicode_escape')
    return dat


def py3dec_unic_bytes_fix(dat):
    # python 3 unicode fix
    if _PY3:
        return dat.decode('raw_unicode_escape')
    return dat


def py3_array_frombytes(msg, data):
    if _PY3:
        return msg.frombytes(data)
    else:
        return msg.fromstring(data)


def py3_array_tobytes(msg):
    if _PY3:
        return msg.tobytes()
    else:
        return msg.tostring()


def check_completion_code(cc):
    if cc != constants.CC_OK:
        raise CompletionCodeError(cc)


def chunks(data, count):
    for i in range(0, len(data), count):
        yield data[i:i+count]


class ByteBuffer(object):
    def __init__(self, data=None):

        if data is not None:
            self.array = array('B', data)
        else:
            self.array = array('B')

    def push_unsigned_int(self, value, length):
        for i in range(length):
            self.array.append((value >> (8*i) & 0xff))

    def pop_unsigned_int(self, length):
        value = 0
        for i in range(length):
            try:
                value |= self.array.pop(0) << (8*i)
            except IndexError:
                raise DecodingError('Data too short for message')
        return value

    def push_string(self, value):
        if _PY3 and isinstance(value, str):
            # Encode Unicode to UTF-8
            value = value.encode()
        py3_array_frombytes(self.array, value)

    def pop_string(self, length):
        string = self.array[0:length]
        del self.array[0:length]
        return py3_array_tobytes(string)
        # return py3dec_unic_bytes_fix(string.tostring())

    def pop_slice(self, length):
        if len(self.array) < length:
            raise DecodingError('Data too short for message')

        c = ByteBuffer(self.array[0:length])
        self.__delslice__(0, length)
        return c

    def tobytes(self):
        return self.array.tobytes()

    def tostring(self):
        return py3_array_tobytes(self.array)

    def extend(self, data):
        self.array.extend(data)

    def append_array(self, a):
        self.array.extend(a)

    def __getslice__(self, a, b):
        return self.array[a:b]

    def __delslice__(self, a, b):
        del self.array[a:b]

    def __len__(self):
        return len(self.array)

    def __getitem__(self, idx):
        return self.array[idx]


BCD_MAP = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '.']


def bcd_encode(input, errors='strict'):
    raise NotImplementedError()


def bcd_decode(encoded_input):
    chars = list()
    try:
        for data in encoded_input:
            if not _PY3:
                data = ord(data)
            chars.append(BCD_MAP[data >> 4 & 0xf] + BCD_MAP[data & 0xf])
        return (''.join(chars), len(encoded_input) * 2)
    except IndexError:
        raise ValueError()


def bcd_search(name):
    # Python 3.9 normalizes 'bcd+' as 'bcd_'
    if name not in ('bcd+', 'bcd'):
        return None
    return codecs.CodecInfo(name='bcd+', encode=bcd_encode, decode=bcd_decode)


def is_string(string):
    if _PY3:
        return isinstance(string, str)
    return isinstance(string, basestring)


class TypeLengthString(object):
    """
    This is the TYPE/LENGTH BYTE FORMAT field represenation according the
    Platform Management FRU Information Storage Definition v1.0.

    In addition the difference to the 'FRU Information Storage Definition' to
    the variant used in Type/Length for the Device ID String used in the SDR.
    """

    TYPE_FRU_BINARY = 0
    TYPE_SDR_UNICODE = 0
    TYPE_BCD_PLUS = 1
    TYPE_6BIT_ASCII = 2
    TYPE_ASCII_OR_UTF16 = 3

    def __init__(self, data=None, offset=0, force_lang_eng=False, sdr=False):
        if data:
            self._from_data(data, offset, force_lang_eng)

    def __str__(self):
        if self.field_type is self.TYPE_FRU_BINARY:
            return ' '.join('%02x' % b for b in self.raw)
        else:
            return self.string.replace('\x00', '')

    def _from_data(self, data, offset=0, force_lang_eng=False):
        self.offset = offset
        self.field_type = data[offset] >> 6 & 0x3
        self.length = data[offset] & 0x3f

        self.raw = data[offset+1:offset+1+self.length]

        chr_data = ''.join([chr(c) for c in self.raw])
        if self.field_type == self.TYPE_BCD_PLUS:
            self.string = chr_data.decode('bcd+')
        elif self.field_type == self.TYPE_6BIT_ASCII:
            self.string = chr_data.decode('6bitascii')
        else:
            self.string = chr_data


class FruTypeLengthString(TypeLengthString):

    def __init__(self, data=None, offset=0, force_lang_eng=False):
        super(FruTypeLengthString, self).__init__(data, offset,
                                               force_lang_eng, sdr=False)


class SdrTypeLengthString(TypeLengthString):

    def __init__(self, data=None, offset=0, force_lang_eng=False):
        super(SdrTypeLengthString, self).__init__(data, sdr=True)
