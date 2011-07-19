from array import array
from copy import deepcopy
import constants
from pyipmi.errors import CompletionCodeError, EncodingError, DecodingError
from pyipmi.utils import push_unsigned_int, pop_unsigned_int

class BaseField:
    def __init__(self, name, length, default=None):
        self.name = name
        self.length = length
        self.default = default

    def decode(self, obj, data):
        raise NotImplementedError()

    def encode(self, obj, data):
        raise NotImplementedError()


class ByteArray(BaseField):
    def __init__(self, name, length, default=None):
        BaseField.__init__(self, name, length)
        if default is not None:
            self.default = array('B', default)
        else:
            self.default = array('B')

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


class UnsignedInt(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        push_unsigned_int(data, value, self.length)

    def decode(self, obj, data):
        value = pop_unsigned_int(data, self.length)
        setattr(obj, self.name, value)


class String(BaseField):
    def encode(self, obj, data):
        value = getattr(obj, self.name)
        data.fromstring(value)

    def decode(self, obj, data):
        setattr(obj, self.name, data[0:self.length])
        del data[0:self.length]


class CompletionCode(UnsignedInt):
    def __init__(self, name='completion_code'):
        UnsignedInt.__init__(self, name, 1, None)

    def decode(self, obj, data):
        UnsignedInt.decode(self, obj, data)
        cc = getattr(obj, self.name)
        if cc != 0x00:
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
        self._set_offsets()
        self._wrapper = self.BitWrapper()
        self.default = self._wrapper
        self._create_fields()

    def _create_fields(self):
        for bit in self._bits:
            if hasattr(self._wrapper, bit.name):
                raise DescriptionError('Bit with name "%s" already added' %
                        bit.name)
            setattr(self._wrapper, bit.name, bit.default)

    def _set_offsets(self):
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


class Message:
    _REQ_DESC = ()
    _RSP_DESC = ()

    class _Req:
        def __init__(self, parent):
            self._parent = parent
        def encode(self):
            return self._parent._encode_req()
        def decode(self, data):
            self._parent._decode_req(data)
        def __str__(self):
            s = '%sReq(' % self._parent.__class__.__name__
            if not hasattr(self._parent, '_REQ_DESC'):
                raise NotImplementedError('You have to overwrite this method')
            for field in self._parent._REQ_DESC:
                s += '%s=%s ' % (field.name, getattr(self, field.name))
            s += ")"
            return s

    class _Rsp:
        def __init__(self, parent):
            self._parent = parent
        def encode(self):
            return self._parent._encode_rsp()
        def decode(self, data):
            self._parent._decode_rsp(data)
        def encode_cmd(self):
            return self._parent._cmd_encode_rsp()
        def decode_cmd(self, data):
            self._parent._decode_cmd_rsp(data)
        def __str__(self):
            s = '%sRsp(' % self._parent.__class__.__name__
            if not hasattr(self._parent, '_RSP_DESC'):
                raise NotImplementedError('You have to overwrite this method')
            for field in self._parent._RSP_DESC:
                s += '%s=%s ' % (field.name, getattr(self, field.name))
            s += ")"
            return s

    def __init__(self):
        self.req = self._Req(self)
        self.rsp = self._Rsp(self)
        self._create_fields()

    def _create_fields(self):
        if hasattr(self, '_REQ_DESC'):
            for field in self._REQ_DESC:
                if hasattr(self.req, field.name):
                    raise DescriptionError('Field "%s" already added',
                            field.name)
                # make a deep copy, default may be a mutable object
                setattr(self.req, field.name, deepcopy(field.default))
        if hasattr(self, '_RSP_DESC'):
            for field in self._RSP_DESC:
                if hasattr(self.rsp, field.name):
                    raise DescriptionError('Field "%s" already added',
                            field.name)
                # make a deep copy, default may be a mutable object
                setattr(self.rsp, field.name, deepcopy(field.default))

    def _csum(self, data):
        csum = 0
        for b in data:
            csum += b
        return -csum % 256

    def _encode_req(self):
        # messages can extend this class and provide their own encoding
        # and decoding functions
        if not hasattr(self, '_REQ_DESC'):
            raise NotImplementedError('You have to overwrite this method')

        data = array('c')
        for field in self._REQ_DESC:
            if getattr(self.req, field.name) == None:
                raise EncodingError('Field "%s" not set.' % field.name)
            field.encode(self.req, data)
        return data.tostring()

    def _decode_req(self, data):
        if not hasattr(self, '_REQ_DESC'):
            raise NotImplementedError('You have to overwrite this method')

        data = array('c', data)
        for field in self._REQ_DESC:
            field.decode(self.req, data)
        if len(data) > 0:
            raise DecodingError('Data has extra bytes')

    def _encode_rsp(self):
        if not hasattr(self, '_RSP_DESC'):
            raise NotImplementedError('You have to overwrite this method')

        data = array('c')
        for field in self._RSP_DESC:
            if getattr(self.rsp, field.name) == None:
                raise EncodingError('Field "%s" not set.' % field.name)
            field.encode(self.rsp, data)
        return data.tostring()

    def _decode_rsp(self, data):
        if not hasattr(self, '_RSP_DESC'):
            raise NotImplementedError('You have to overwrite this method')

        data = array('c', data)
        cc = 0
        for field in self._RSP_DESC:
            try:
                field.decode(self.rsp, data)
            except CompletionCodeError, e:
                # stop decoding on completion code != 0
                cc = e.cc
                break
        if cc == 0 and len(data) > 0:
            raise DecodingError('Data has extra bytes')
