#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

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
