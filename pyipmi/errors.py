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

class DecodingError(Exception):
    """Error on message decoding."""
    pass


class EncodingError(Exception):
    """Error on message encoding."""
    pass


class TimeoutError(Exception):
    """Timeout occurred."""
    pass


class CompletionCodeError(Exception):
    """IPMI completion code not OK."""
    def __init__(self, cc):
        self.cc = cc

    def __str__(self):
        return "%s cc=0x%02x" % (self.__class__.__name__, self.cc)

class NotSupportedError(Exception):
    """Not supported yet."""
    pass


class DescriptionError(Exception):
    """Message description incorrect."""
    pass


class RetryError(Exception):
    """Maxium number of retries exceeded."""
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        if self.msg:
            return "%s msg=%s" % (self.__class__.__name__, self.msg)
        else:
            return "%s" % (self.__class__.__name__)

class DataNotFound(Exception):
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        if self.msg:
            return "%s msg=%s" % (self.__class__.__name__, self.msg)
        else:
            return "%s" % (self.__class__.__name__)

class HpmError(Exception):
    """HPM.1 error"""
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if self.msg:
            return "%s msg=%s" % (self.__class__.__name__, self.msg)
        else:
            return "%s" % (self.__class__.__name__)
