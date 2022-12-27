#!/usr/bin/env python
# -*- coding: utf-8 -*-


import array

from .errors import DecodingError
from .utils import py3_array_tobytes


class VersionField(object):
    """This class represent the Version fields defines by IPMI.

    Introduced with HPM the version field can hold additional auxiliary bytes.
    """

    VERSION_FIELD_LEN = 2
    VERSION_WITH_AUX_FIELD_LEN = 6

    def __init__(self, data=None):
        self.major = None
        self.minor = None
        if data:
            self._from_data(data)

    def _from_data(self, data):
        if isinstance(data, str):
            data = [ord(c) for c in data]

        data = array.array('B', data)
        self.version = self._decode_data(data[0:2])
        if len(data) == self.VERSION_WITH_AUX_FIELD_LEN:
            self.auxiliary = data[2:6]

    def __str__(self):
        return self.version_to_string()

    def _decode_data(self, data):
        """`data` is array.array."""
        self.major = data[0]

        if data[1] == 0xff:
            self.minor = data[1]
        elif data[1] <= 0x99:
            self.minor = int(py3_array_tobytes(data[1:2]).decode('bcd+'))
        else:
            raise DecodingError()

    def version_to_string(self):
        return ''.join("%s.%s" % (self.major, self.minor))


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
                                                  force_lang_eng,
                                                  sdr=False)


class SdrTypeLengthString(TypeLengthString):

    def __init__(self, data=None, offset=0, force_lang_eng=False):
        super(SdrTypeLengthString, self).__init__(data, sdr=True)
