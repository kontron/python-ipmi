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


from __future__ import absolute_import
from builtins import range
from builtins import object

from array import array

from . import constants
from ..utils import ByteBuffer,  py3enc_unic_bytes_fix
from ..errors import CompletionCodeError, EncodingError, DecodingError, \
        DescriptionError

class BaseField(object):
    def __init__(self, name, length, default=None):
        self.name = name
        self.length = length
        self.default = default

    def decode(self, obj, data):
        raise NotImplementedError()

    def encode(self, obj, data):
        if getattr(obj, self.name) == None:
            raise EncodingError('Field "%s" not set.' % self.name)
        raise NotImplementedError()

    def create(self):
        raise NotImplementedError()


class ByteArray(BaseField):
    def __init__(self, name, length, default=None):
        BaseField.__init__(self, name, length)
        if default is not None:
            default = py3enc_unic_bytes_fix(default)
            self.default = array('B', default)
        else:
            self.default = None

    def _length(self, obj):
        return self.length

    def encode(self, obj, data):
        a = getattr(obj, self.name)
        if len(a) != self._length(obj):
            raise EncodingError('Array must be exaclty %d bytes long '
                    '(but is %d long)' % (self._length(obj), len(a)))
        for i in range(self._length(obj)):
            data.push_unsigned_int(a[i], 1)

    def decode(self, obj, data):
        a = getattr(obj, self.name)
        bytes = []
        for i in range(self._length(obj)):
            bytes.append(data.pop_unsigned_int(1))
        setattr(obj, self.name, array('B', bytes))

    def create(self):
        if self.default is not None:
            return array('B', self.default)
        else:
            return array('B', self.length * '\x00')


class VariableByteArray(ByteArray):
    """Array of bytes with variable length.

    The length is dynamically computed by a function.
    """

    def __init__(self, name, length_func):
        ByteArray.__init__(self, name, None, None)
        self._length_func = length_func

    def _length(self, obj):
        return self._length_func(obj)

    def create(self):
        return None


class UnsignedInt(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        data.push_unsigned_int(value, self.length)

    def decode(self, obj, data):
        value = data.pop_unsigned_int(self.length)
        setattr(obj, self.name, value)

    def create(self):
        if self.default is not None:
            return self.default
        else:
            return 0


class String(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        data.push_string(value)
        data.from_string(value)

    def decode(self, obj, data):
        value = data.pop_string(self.length)
        setattr(obj, self.name, value)

    def create(self):
        if self.default is not None:
            return self.default
        else:
            return ''


class CompletionCode(UnsignedInt):
    def __init__(self, name='completion_code'):
        UnsignedInt.__init__(self, name, 1, None)

    def decode(self, obj, data):
        UnsignedInt.decode(self, obj, data)
        cc = getattr(obj, self.name)
        if cc != constants.CC_OK:
            raise CompletionCodeError(cc)


class UnsignedIntMask(UnsignedInt):
    def __init__(self, name, length, mask, default=None):
        UnsignedInt.__init__(self, name, length, default)


class Timestamp(UnsignedInt):
    def __init__(self, name):
        UnsignedInt.__init__(self, name, 4, None)


class Conditional(object):
    def __init__(self, cond_fn, field):
        self._condition_fn = cond_fn
        self._field = field

    def __getattr__(self, name):
        return getattr(self._field, name)

    def encode(self, obj, data):
        if self._condition_fn(obj):
            self._field.encode(obj, data)

    def decode(self, obj, data):
        if self._condition_fn(obj):
            self._field.decode(obj, data)

    def create(self):
        return self._field.create()


class Optional(object):
    def __init__(self, field):
        self._field = field

    def __getattr__(self, name):
        return getattr(self._field, name)

    def decode(self, obj, data):
        if len(data) > 0:
            self._field.decode(obj,data)
        else:
            setattr(obj, self._field.name, None)

    def encode(self, obj, data):
        if getattr(obj, self._field.name) is not None:
            self._field.encode(obj, data)

    def create(self):
        return None


class RemainingBytes(BaseField):
    def __init__(self, name):
        BaseField.__init__(self, name, None)

    def encode(self, obj, data):
        a = getattr(obj, self.name)
        data.push_string(a)

    def decode(self, obj, data):
        setattr(obj, self.name, array('B', data[:]))
        del data.array[:]

    def create(self):
        return array('B')


class Bitfield(BaseField):
    class Bit(object):
        def __init__(self, name, width=1, default=None):
            self.name = name
            self._width = width
            self.default = default


    class ReservedBit(Bit):
        counter = 0
        def __init__(self, width, default=0):
            Bitfield.Bit.__init__(self, 'reserved_bit_%d' %
                    Bitfield.reserved_bit_counter, width, default)
            Bitfield.reserved_bit_counter += 1


    class BitWrapper(object):
        def __init__(self, bits, length):
            self._bits = bits
            self._length = length
            for bit in bits:
                if hasattr(self, bit.name):
                    raise DescriptionError('Bit with name "%s" already added' %
                            bit.name)
                if bit.default is not None:
                    setattr(self, bit.name, bit.default)
                else:
                    setattr(self, bit.name, 0)

        def __str__(self):
            s = '['
            for attr in dir(self):
                if attr.startswith('_'):
                    continue
                s += '%s=%s ' % (attr, getattr(self, attr))
            s += ']'
            return s

        def __int__(self):
            return self._value

        def _get_value(self):
            value = 0
            for bit in self._bits:
                bit_value = getattr(self, bit.name)
                if bit_value is None:
                    bit_value = bit.default
                if bit_value == None:
                    raise EncodingError('Bitfield "%s" not set.' % bit.name)

                value |= (bit_value & (2**bit._width - 1)) << bit.offset
            return value

        def _set_value(self, value):
            for bit in self._bits:
                tmp = (value >> bit.offset) & (2**bit._width - 1)
                setattr(self, bit.name, tmp)

        _value = property(_get_value, _set_value)

    reserved_bit_counter = 0

    def __init__(self, name, length, *bits):
        BaseField.__init__(self, name, length)
        self._bits = bits
        self._precalc_offsets()

    def _precalc_offsets(self):
        offset = 0
        for b in self._bits:
            b.offset = offset
            offset += b._width
        if offset != 8 * self.length:
            raise DescriptionError('Bit description does not match bitfield '
                    'length')

    def encode(self, obj, data):
        wrapper = getattr(obj, self.name)
        value = wrapper._value
        for i in range(self.length):
            data.push_unsigned_int((value >> (8*i)) & 0xff, 1)

    def decode(self, obj, data):
        value = 0
        for i in range(self.length):
            try:
                value |= data.pop_unsigned_int(1) << (8*i)
            except IndexError:
                raise DecodingError('Data too short for message')
        wrapper = getattr(obj, self.name)
        wrapper._value = value

    def create(self):
        return Bitfield.BitWrapper(self._bits, self.length)

class Message(object):
    RESERVED_FIELD_NAMES = ['cmdid', 'netfn', 'lun']

    __default_lun__ = 0

    def __init__(self, *args, **kwargs):
        """Message constructor with ([buf], [field=val,...]) prototype.

        Arguments:

        buf -- option message buffer to decode

        Optional keyword arguments corresponts to members to set (matching
        fields in self.__fields__, or 'data').
        """

        # create message fields
        if hasattr(self, '__fields__'):
            self._create_fields()

        # set default lun
        self.lun = self.__default_lun__

        self.data = ''
        if args:
            self._decode(args[0])
        else:
            for (name, value) in kwargs.items():
                self._set_field(name, value)

    def _set_field(self, name, value):
        raise NotImplementedError()
        # TODO walk along the properties..
        setattr(self, name, value)

    def _create_fields(self):
        for field in self.__fields__:
            if field.name in self.RESERVED_FIELD_NAMES:
                raise DescriptionError('Field name "%s" is reserved' %
                        field.name)
            if hasattr(self, field.name):
                raise DescriptionError('Field "%s" already added',
                        field.name)
            setattr(self, field.name, field.create())

    def _encode(self):
        if not hasattr(self, '__fields__'):
            return ''

        data = ByteBuffer()
        for field in self.__fields__:
            field.encode(self, data)
        return data.tostring()

    def _decode(self, data):
        if not hasattr(self, '__fields__'):
            raise NotImplementedError('You have to overwrite this method')

        data = ByteBuffer(data)
        cc = None
        for field in self.__fields__:
            try:
                field.decode(self, data)
            except CompletionCodeError as e:
                # stop decoding on completion code != 0
                cc = e.cc
                break

        if (cc is None or cc == 0) and len(data) > 0:
            raise DecodingError('Data has extra bytes')

    def _is_request(self):
        return self.__netfn__ & 1 == 0

    def _is_response(self):
        return self.__netfn__ & 1 == 1

    netfn = property(lambda s: s.__netfn__)
    cmdid = property(lambda s: s.__cmdid__)


encode_message = lambda m: m._encode()
decode_message = lambda m,d: m._decode(d)
