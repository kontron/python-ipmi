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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

from __future__ import annotations

from array import array
from typing import Any, TYPE_CHECKING
from collections.abc import Callable

from . import constants
from ..utils import ByteBuffer
from ..errors import (CompletionCodeError, EncodingError, DecodingError,
                      DescriptionError)


class BaseField:
    def __init__(self, name: str, length: int | None,
                 default: Any = None) -> None:
        self.name = name
        self.length = length
        self.default = default

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        raise NotImplementedError()

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        if getattr(obj, self.name) is None:
            raise EncodingError(f'Field "{self.name}" not set.')
        raise NotImplementedError()

    def create(self) -> Any:
        raise NotImplementedError()


class ByteArray(BaseField):
    def __init__(self, name: str, length: int | None,
                 default: bytes | None = None) -> None:
        BaseField.__init__(self, name, length)
        if default is not None:
            self.default = array('B', default)
        else:
            self.default = None

    def _length(self, obj: Message) -> int:
        assert self.length is not None
        return self.length

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        a = getattr(obj, self.name)
        if len(a) != self._length(obj):
            raise EncodingError(f'Array must be exactly {self._length(obj):d} '
                                'bytes long '
                                f'(but is {len(a):d} long)')
        for i in range(self._length(obj)):
            data.push_unsigned_int(a[i], 1)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        bytes = []
        for _ in range(self._length(obj)):
            bytes.append(data.pop_unsigned_int(1))
        setattr(obj, self.name, array('B', bytes))

    def create(self) -> array | None:
        assert self.length is not None
        if self.default is not None:
            return array('B', self.default)
        else:
            return array('B', self.length * b'\x00')


class VariableByteArray(ByteArray):
    """Array of bytes with variable length.

    The length is dynamically computed by a function.
    """

    def __init__(self, name: str, length_func: Callable[[Message], int]) -> None:
        ByteArray.__init__(self, name, None, None)
        self._length_func = length_func

    def _length(self, obj: Message) -> int:
        return self._length_func(obj)

    def create(self) -> None:
        return None


class UnsignedInt(BaseField):
    length: int

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        value = getattr(obj, self.name)
        data.push_unsigned_int(value, self.length)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        value = data.pop_unsigned_int(self.length)
        setattr(obj, self.name, value)

    def create(self) -> int:
        if self.default is not None:
            return self.default
        else:
            return 0


class String(BaseField):
    """A string of a fixed length.

    A shorter string is padded with NUL bytes on encoding.
    """

    length: int

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        value = getattr(obj, self.name)
        if isinstance(value, str):
            value = value.encode()
        if len(value) > self.length:
            raise EncodingError(f'String "{self.name}" is longer than '
                                f'{self.length:d} bytes')
        data.push_string(value.ljust(self.length, b'\x00'))

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        if len(data) < self.length:
            raise DecodingError(f'String "{self.name}" is shorter than '
                                f'{self.length:d} bytes')
        value = data.pop_string(self.length)
        setattr(obj, self.name, value)

    def create(self) -> str | bytes:
        if self.default is not None:
            return self.default
        else:
            return ''


class CompletionCode(UnsignedInt):
    def __init__(self, name: str = 'completion_code') -> None:
        UnsignedInt.__init__(self, name, 1, None)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        UnsignedInt.decode(self, obj, data)
        cc = getattr(obj, self.name)
        if cc != constants.CC_OK:
            raise CompletionCodeError(cc)


class UnsignedIntMask(UnsignedInt):
    """An unsigned integer of the bits of a mask, the other bits are reserved.

    The reserved bits are ignored on decoding and must not be set on
    encoding.
    """

    def __init__(self, name: str, length: int, mask: int,
                 default: int | None = None) -> None:
        UnsignedInt.__init__(self, name, length, default)
        self.mask = mask

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        value = getattr(obj, self.name)
        if value & ~self.mask:
            raise EncodingError(f'Field "{self.name}": value 0x{value:x} '
                                f'has bits outside of 0x{self.mask:x}')
        UnsignedInt.encode(self, obj, data)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        UnsignedInt.decode(self, obj, data)
        setattr(obj, self.name, getattr(obj, self.name) & self.mask)


class Timestamp(UnsignedInt):
    def __init__(self, name: str) -> None:
        UnsignedInt.__init__(self, name, 4, None)


class Conditional:
    def __init__(self, cond_fn: Callable[[Message], bool],
                 field: BaseField) -> None:
        self._condition_fn = cond_fn
        self._field = field

    def __getattr__(self, name: str) -> Any:
        return getattr(self._field, name)

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        if self._condition_fn(obj):
            self._field.encode(obj, data)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        if self._condition_fn(obj):
            self._field.decode(obj, data)

    def create(self) -> Any:
        return self._field.create()


class Optional:
    def __init__(self, field: BaseField) -> None:
        self._field = field

    def __getattr__(self, name: str) -> Any:
        return getattr(self._field, name)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        if len(data) > 0:
            self._field.decode(obj, data)
        else:
            setattr(obj, self._field.name, None)

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        if getattr(obj, self._field.name) is not None:
            self._field.encode(obj, data)

    def create(self) -> None:
        return None


class RemainingBytes(BaseField):
    def __init__(self, name: str) -> None:
        BaseField.__init__(self, name, None)

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        a = getattr(obj, self.name)
        data.extend(a)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        setattr(obj, self.name, array('B', data.array))
        del data.array[:]

    def create(self) -> array:
        return array('B')


class Bitfield(BaseField):
    class Bit:
        def __init__(self, name: str, width: int = 1,
                     default: int | None = None) -> None:
            self.name = name
            self._width = width
            self.default = default
            # set by the Bitfield the bit is added to
            self.offset = 0

    class ReservedBit(Bit):
        counter = 0

        def __init__(self, width: int, default: int = 0) -> None:
            name = f'reserved_bit_{Bitfield.reserved_bit_counter:d}'
            Bitfield.Bit.__init__(self, name, width, default)
            Bitfield.reserved_bit_counter += 1

    class BitWrapper:
        def __init__(self, bits: tuple[Bitfield.Bit, ...],
                     length: int) -> None:
            self._bits = bits
            self._length = length
            for bit in bits:
                if hasattr(self, bit.name):
                    raise DescriptionError(f'Bit with name "{bit.name}" '
                                           'already added')
                if bit.default is not None:
                    setattr(self, bit.name, bit.default)
                else:
                    setattr(self, bit.name, 0)

        def __str__(self) -> str:
            s = '['
            for attr in dir(self):
                if attr.startswith('_'):
                    continue
                s += f'{attr}={getattr(self, attr)}, '
            s += ']'
            return s

        def __int__(self) -> int:
            return self._value

        def _get_value(self) -> int:
            value = 0
            for bit in self._bits:
                bit_value = getattr(self, bit.name)
                if bit_value is None:
                    bit_value = bit.default
                if bit_value is None:
                    raise EncodingError(f'Bitfield "{bit.name}" not set.')

                if bit_value < 0 or bit_value >= 1 << bit._width:
                    raise EncodingError(f'Bitfield "{bit.name}": value '
                                        f'{bit_value:d} does not '
                                        f'fit in {bit._width:d} bit(s)')
                value |= bit_value << bit.offset
            return value

        def _set_value(self, value: int) -> None:
            for bit in self._bits:
                tmp = (value >> bit.offset) & (2**bit._width - 1)
                setattr(self, bit.name, tmp)

        _value = property(_get_value, _set_value)

        if TYPE_CHECKING:
            # the bits are created as attributes at runtime
            def __getattr__(self, name: str) -> Any: ...
            def __setattr__(self, name: str, value: Any) -> None: ...

    reserved_bit_counter = 0
    length: int

    def __init__(self, name: str, length: int, *bits: Bit) -> None:
        BaseField.__init__(self, name, length)
        self._bits = bits
        self._precalc_offsets()

    def _precalc_offsets(self) -> None:
        offset = 0
        for b in self._bits:
            b.offset = offset
            offset += b._width
        if offset != 8 * self.length:
            raise DescriptionError('Bit description does not match bitfield '
                                   'length')

    def encode(self, obj: Message, data: ByteBuffer) -> None:
        wrapper = getattr(obj, self.name)
        value = wrapper._value
        for i in range(self.length):
            data.push_unsigned_int((value >> (8*i)) & 0xff, 1)

    def decode(self, obj: Message, data: ByteBuffer) -> None:
        value = 0
        for i in range(self.length):
            try:
                value |= data.pop_unsigned_int(1) << (8*i)
            except IndexError:
                raise DecodingError('Data too short for message') from None
        wrapper = getattr(obj, self.name)
        wrapper._value = value

    def create(self) -> Bitfield.BitWrapper:
        return Bitfield.BitWrapper(self._bits, self.length)


class GroupExtensionIdentifier(UnsignedInt):
    def __init__(self, name: str = 'picmg_identifier',
                 value: int | None = None) -> None:
        UnsignedInt.__init__(self, name, 1, value)


class EventMessageRevision(UnsignedInt):
    def __init__(self, value: int | None = None) -> None:
        UnsignedInt.__init__(self, 'event_message_rev', 1, value)


Field = BaseField | Conditional | Optional


class Message:
    RESERVED_FIELD_NAMES = ['cmdid', 'netfn', 'lun', 'group_extension']

    # set by the message definitions, intentionally without a default value
    __netfn__: int
    __cmdid__: int
    __fields__: tuple[Field, ...]

    __default_lun__ = 0
    __group_extension__: int | None = None
    __not_implemented__ = False

    if TYPE_CHECKING:
        # the message fields are created as attributes at runtime
        def __getattr__(self, name: str) -> Any: ...
        def __setattr__(self, name: str, value: Any) -> None: ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a message, optionally decoded from a buffer.

        Args:
            *args: An optional message buffer to decode.
            **kwargs: The values of the fields to set, matching the fields
                in `__fields__` or 'data'.
        """
        # create message fields
        if hasattr(self, '__fields__'):
            self._create_fields()

        # set default lun
        self.lun = self.__default_lun__

        # a message without a field 'data', the field must not be replaced
        if not hasattr(self, 'data'):
            self.data: Any = ''
        if args:
            self._decode(args[0])
        else:
            for (name, value) in kwargs.items():
                self._set_field(name, value)

    def _set_field(self, name: str, value: Any) -> None:
        """Set a field, a bitfield also from its value as integer.

        Raises:
            TypeError: The message has no field with this name.
        """
        names = [field.name for field in getattr(self, '__fields__', ())]
        if name not in names + ['data']:
            raise TypeError(f'{type(self).__name__} has no field {name!r}')
        current = getattr(self, name, None)
        if isinstance(current, Bitfield.BitWrapper) and isinstance(value, int):
            current._value = value
        else:
            setattr(self, name, value)

    def __str__(self) -> str:
        return f'{type(self).__name__} [netfn={self.netfn}, cmd={self.cmdid}, grp={self.group_extension}]'

    def _create_fields(self) -> None:
        for field in self.__fields__:
            if field.name in self.RESERVED_FIELD_NAMES:
                raise DescriptionError(f'Field name "{field.name}" is '
                                       'reserved')
            if hasattr(self, field.name):
                raise DescriptionError(f'Field "{field.name}" already added')
            setattr(self, field.name, field.create())

    def _pack(self) -> array:
        """Pack the message and return an array."""
        data = ByteBuffer()
        if not hasattr(self, '__fields__'):
            return data.array

        for field in self.__fields__:
            field.encode(self, data)
        return data.array

    def _encode(self) -> bytes:
        """Encode the message and return a bytestring."""
        data = ByteBuffer()
        if not hasattr(self, '__fields__'):
            return data.tostring()

        for field in self.__fields__:
            field.encode(self, data)
        return data.tostring()

    def _decode(self, data: bytes) -> None:
        """Decode the bytestring message."""
        if not hasattr(self, '__fields__'):
            return

        buf = ByteBuffer(data)
        cc = None
        for field in self.__fields__:
            try:
                field.decode(self, buf)
            except CompletionCodeError as e:
                # stop decoding on completion code != 0
                cc = e.cc
                break

        if (cc is None or cc == 0) and len(buf) > 0:
            raise DecodingError('Data has extra bytes')

    def _is_request(self) -> bool:
        return self.__netfn__ & 1 == 0

    def _is_response(self) -> bool:
        return self.__netfn__ & 1 == 1

    netfn = property(lambda s: s.__netfn__)
    cmdid = property(lambda s: s.__cmdid__)
    group_extension = property(lambda s: s.__group_extension__)


def encode_message(msg: Message) -> bytes:
    return msg._encode()


def decode_message(msg: Message, data: bytes) -> None:
    return msg._decode(data)


def pack_message(msg: Message) -> array:
    return msg._pack()
