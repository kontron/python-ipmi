from array import array

import constants
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import CompletionCodeError, EncodingError, DecodingError, \
        DescriptionError

class BaseField:
    def __init__(self, name, length, default=None):
        self.name = name
        self.length = length
        self.default = default

    def decode(self, obj, data):
        raise NotImplementedError()

    def encode(self, obj, data):
        raise NotImplementedError()

    def create(self):
        raise NotImplementedError()


class ByteArray(BaseField):
    def __init__(self, name, length, default=None):
        BaseField.__init__(self, name, length)
        if default is not None:
            self.default = array('B', default)
        else:
            self.default = None

    def encode(self, obj, data):
        a = getattr(obj, self.name)
        if len(a) != self.length:
            raise EncodingError('Array must be exaclty %d bytes long '
                    '(but is %d long)' % (self.length, len(a)))
        for i in xrange(self.length):
            push_unsigned_int(data, a[i], 1)

    def decode(self, obj, data):
        a = getattr(obj, self.name)
        bytes = []
        for i in xrange(self.length):
            bytes.append(pop_unsigned_int(data, 1))
        setattr(obj, self.name, array('B', bytes))

    def create(self):
        if self.default is not None:
            return array('B', self.default)
        else:
            return array('B', self.length * '\x00')


class UnsignedInt(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        push_unsigned_int(data, value, self.length)

    def decode(self, obj, data):
        value = pop_unsigned_int(data, self.length)
        setattr(obj, self.name, value)

    def create(self):
        if self.default is not None:
            return self.default
        else:
            return 0


class String(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        data.fromstring(value)

    def decode(self, obj, data):
        setattr(obj, self.name, data[0:self.length])
        del data[0:self.length]

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


class Conditional:
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

class Optional:
    def __init__(self, field):
        self._field = field

    def __getattr__(self, name):
        return getattr(self._field, name)

    def decode(self, obj, data):
        if len(data) > 0:
            self._field.decode(obj,data)

    def encode(self, obj, data):
        self._field.encode(obj, data)

class Bitfield(BaseField):
    class Bit:
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


    class BitWrapper:
        def __init__(self, bits):
            self._bits = bits
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

    reserved_bit_counter = 0

    def __init__(self, name, length, *bits):
        BaseField.__init__(self, name, length)
        self._bits = bits
        self._precalc_offsets()

    def _precalc_offsets(self):
        offset = 0
        for b in self._bits:
            b._offset = offset
            offset += b._width
        if offset != 8 * self.length:
            raise DescriptionError('Bit description does not match bitfield '
                    'length')

    def encode(self, obj, data):
        value = 0
        for bit in self._bits:
            wrapper = getattr(obj, self.name)
            bit_value = getattr(wrapper, bit.name)
            if bit_value is None:
                bit_value = bit.default
            if bit_value == None:
                raise EncodingError('Bitfield "%s" not set.' % bit.name)

            value |= (bit_value & (2**bit._width - 1)) << bit._offset
        for i in xrange(self.length):
            data.append(chr((value >> (8*i)) & 0xff))

    def decode(self, obj, data):
        value = 0
        for i in xrange(self.length):
            try:
                value |= ord(data.pop(0)) << (8*i)
            except IndexError:
                raise DecodingError('Data too short for message')
        for bit in self._bits:
            tmp = (value >> bit._offset) & (2**bit._width - 1)
            wrapper = getattr(obj, self.name)
            setattr(wrapper, bit.name, tmp)

    def create(self):
        return Bitfield.BitWrapper(self._bits)

class Message:
    RESERVED_FIELD_NAMES = ['cmdid', 'netfn', 'lun']

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
            for (name, value) in kwargs.iteritems():
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
            raise NotImplementedError('You have to overwrite this method')

        data = array('c')
        for field in self.__fields__:
            if getattr(self, field.name) == None:
                raise EncodingError('Field "%s" not set.' % field.name)
            field.encode(self, data)
        return data.tostring()

    def _decode(self, data):
        if not hasattr(self, '__fields__'):
            raise NotImplementedError('You have to overwrite this method')

        data = array('c', data)
        cc = None
        for field in self.__fields__:
            try:
                field.decode(self, data)
            except CompletionCodeError, e:
                # stop decoding on completion code != 0
                cc = e.cc
                break

        if (cc == None or cc == 0) and len(data) > 0:
            raise DecodingError('Data has extra bytes')

    def _is_request(self):
        return self.__netfn__ & 1 == 0

    def _is_response(self):
        return self.__netfn__ & 1 == 1

    netfn = property(lambda s: s.__netfn__)
    cmdid = property(lambda s: s.__cmdid__)

encode_message = lambda m: m._encode()
decode_message = lambda m,d: m._decode(d)

