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

from builtins import range
import sys
import codecs
from array import array
from .msgs import constants
from .errors import DecodingError, CompletionCodeError
#from .msgs import create_request_by_name


def py3enc_unic_bytes_fix(dat):
    # python 3 unicode fix
    if isinstance(dat, str) and int(sys.version[0]) > 2:
        dat = dat.encode('raw_unicode_escape')
    return dat


def py3dec_unic_bytes_fix(dat):
    # python 3 unicode fix
    if int(sys.version[0]) > 2:
        return dat.decode('raw_unicode_escape')
    return dat


def bytes2(dat, enc):
    # python 2-3 workaround
    if int(sys.version[0]) > 2:
        return bytes(dat, enc)
    return dat


def check_completion_code(cc):
    if cc != constants.CC_OK:
        raise CompletionCodeError(cc)


def chunks(d, n):
    for i in range(0, len(d), n):
        yield d[i:i+n]


class ByteBuffer:
    def __init__(self, data=None):

        if data is not None:
            self.array = array('B', py3enc_unic_bytes_fix(data))

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
        self.array.fromstring(value)

    def pop_string(self, length):
        s = self.array[0:length]
        del self.array[0:length]
        return py3dec_unic_bytes_fix(s.tostring())

    def pop_slice(self, length):
        if len(self.array) < length:
            raise DecodingError('Data too short for message')

        c = ByteBuffer(self.array[0:length])
        self.__delslice__(0, length)
        return c

    def tostring(self):
        return py3dec_unic_bytes_fix(self.array.tostring())

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


bcd_map = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '.' ]


def bcd_encode(input, errors='strict'):
    raise NotImplementedError()


def bcd_decode(input, errors='strict'):
    chars = list()
    try:
        for b in input:
            if int(sys.version[0]) == 2:
                b = ord(b)
            chars.append(bcd_map[b >> 4 & 0xf] + bcd_map[b & 0xf])
        return (''.join(chars), len(input) * 2)
    except IndexError:
        raise ValueError()


def bcd_search(name):
    if name != 'bcd+':
        return None
    return codecs.CodecInfo(
            name = 'bcd+',
            encode = bcd_encode,
            decode = bcd_decode)
