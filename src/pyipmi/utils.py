#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import codecs
from array import array
import pyipmi.msgs.constants
import pyipmi.errors

def check_completion_code(cc):
    if cc != pyipmi.msgs.constants.CC_OK:
        raise pyipmi.errors.CompletionCodeError(cc)

def chunks(d, n):
    for i in xrange(0, len(d), n):
        yield d[i:i+n]

class ByteBuffer:
    def __init__(self, data=None):
        if data is not None:
            self.array = array('B', data)
        else:
            self.array = array('B')

    def push_unsigned_int(self, value, length):
        for i in xrange(length):
            self.array.append((value >> (8*i) & 0xff))

    def pop_unsigned_int(self, length):
        value = 0
        for i in xrange(length):
            try:
                value |= self.array.pop(0) << (8*i)
            except IndexError:
                raise pyipmi.errors.DecodingError('Data too short for message')
        return value

    def push_string(self, value):
        self.array.fromstring(value)

    def pop_string(self, length):
        s = self.array[0:length]
        del self.array[0:length]
        return s.tostring()

    def to_string(self):
        return self.array.tostring()

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
