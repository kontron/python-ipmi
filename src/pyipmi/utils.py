#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import codecs
import pyipmi.msgs.constants
import pyipmi.errors

def check_completion_code(cc):
    if cc != pyipmi.msgs.constants.CC_OK:
        raise pyipmi.errors.CompletionCodeError(cc)

def push_unsigned_int(data, value, length):
    for i in xrange(length):
        data.append(chr((value >> (8*i)) & 0xff))

def pop_unsigned_int(data, length):
    value = 0
    for i in xrange(length):
        try:
            value |= ord(data.pop(0)) << (8*i)
        except IndexError:
            raise pyipmi.errors.DecodingError('Data too short for message')
    return value


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
