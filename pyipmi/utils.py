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

import codecs
import array
import pyipmi.msgs.constants
from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import create_request_by_name

def check_completion_code(cc):
    if cc != pyipmi.msgs.constants.CC_OK:
        raise pyipmi.errors.CompletionCodeError(cc)

def chunks(d, n):
    for i in xrange(0, len(d), n):
        yield d[i:i+n]


class ByteBuffer(array.array):
    def __new__(cls, data=None):
        args = (cls, 'B')
        if data is not None:
            args = args + (data,)
        return array.array.__new__(*args)

    def push_unsigned_int(self, value, length):
        for i in xrange(length):
            self.append((value >> (8*i) & 0xff))

    def pop_unsigned_int(self, length):
        value = 0
        for i in xrange(length):
            try:
                value |= self.pop(0) << (8*i)
            except IndexError:
                raise pyipmi.errors.DecodingError('Data too short for message')
        return value

    def push_string(self, value):
        self.fromstring(value)

    def pop_string(self, length):
        s = self[0:length]
        del self[0:length]
        return s.tostring()

    def pop_slice(self, length):
        if len(self) < length:
            raise pyipmi.errors.DecodingError('Data too short for message')

        c = ByteBuffer(self[0:length])
        self.__delslice__(0, length)
        return c


bcd_map = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '.' ]

def bcd_encode(input, errors='strict'):
    raise NotImplementedError()

def bcd_decode(input, errors='strict'):
    chars = list()
    try:
        for b in input:
            b = ord(b)
            chars.append(bcd_map[b>>4 & 0xf] + bcd_map[b & 0xf])
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
