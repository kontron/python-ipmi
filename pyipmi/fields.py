#!/usr/bin/env python
#-*- coding: utf-8 -*-

#from builtins import object

import array

from .errors import DecodingError

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
        """`data` is array.array"""
        self.major = data[0]

        if data[1] is 0xff:
            self.minor = data[1]
        elif data[1] <= 0x99:
            self.minor = int(data[1:2].tostring().decode('bcd+'))
        else:
            raise DecodingError()

    def version_to_string(self):
        return ''.join("%s.%s" % (self.major, self.minor))
