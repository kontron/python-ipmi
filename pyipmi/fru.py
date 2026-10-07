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

"""FRU inventory commands and the decoding of the FRU inventory data.

The FRU (Field Replaceable Unit) inventory data is specified by the IPMI
Platform Management FRU Information Storage Definition v1.0. It consists
of a common header and the optional internal use, chassis info, board info,
product info and multirecord areas.

The FRU inventory of a device is read with the methods of :class:`Fru`,
which are available on :class:`pyipmi.Ipmi`. A FRU file is decoded with
:func:`get_fru_inventory_from_file`.

Example:
    Print the board serial number of a device::

        inventory = ipmi.get_fru_inventory()
        if inventory.board_info_area is not None:
            print(inventory.board_info_area.serial_number)
"""

from __future__ import annotations

import array
import codecs
import datetime
from collections.abc import Sequence

from .errors import DecodingError, CompletionCodeError, RetryError, DataNotFound
from .constants import manufacturer_name
from .helper import ReadLength
from .msgs import constants
from .utils import bcd_search, chunks, py3_array_tobytes
from .fields import FruTypeLengthString, _unpack6bitascii
from .mixin import IpmiMixin

codecs.register(bcd_search)

# areas are a multiple of 8 bytes
FRU_AREA_MIN_LENGTH = 8


class Fru(IpmiMixin):
    """FRU inventory commands, available on :class:`pyipmi.Ipmi`.

    The FRU data is read in chunks. If the device cannot return the
    requested number of bytes, the chunk size is reduced and kept for the
    following reads of the FRU device.

    Attributes:
        write_length: The number of bytes written per Write FRU Data
            request.
    """

    def __init__(self) -> None:
        """Initialize the FRU command group."""
        self.write_length = 16
        # read length per FRU device, a reduced length is kept for the
        # following reads
        self._fru_read_lengths: dict[int, ReadLength] = {}

    def get_fru_inventory_area_info(self, fru_id: int = 0) -> int:
        """Return the size of the FRU inventory area.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The size of the FRU inventory area in bytes.
        """
        rsp = self.send_message_with_name('GetFruInventoryAreaInfo',
                                          fru_id=fru_id)
        return rsp.area_size

    def write_fru_data(self, data: bytes, offset: int = 0,
                       fru_id: int = 0) -> None:
        """Write data to the FRU inventory area.

        The data is written in chunks of ``write_length`` bytes.

        Args:
            data: The data to write.
            offset: The offset in the FRU inventory area to write to.
            fru_id: The FRU device ID.

        Raises:
            Exception: The device wrote fewer bytes than were sent.
        """
        for chunk in chunks(data, self.write_length):
            write_rsp = self.send_message_with_name('WriteFruData',
                                                    fru_id=fru_id,
                                                    offset=offset,
                                                    data=chunk)

            # check if device wrote the same number of bytes sent
            if write_rsp.count_written != len(chunk):
                raise Exception(f'sent {len(chunk)} bytes but device wrote {write_rsp.count_written} bytes'
                                )

            offset += len(chunk)

    def read_fru_data(self, offset: int | None = None,
                      count: int | None = None, fru_id: int = 0) -> bytes:
        """Read data from the FRU inventory area.

        Args:
            offset: The offset in the FRU inventory area to read from. If
                None, the data is read from the start.
            count: The number of bytes to read. If None, or if ``offset``
                is None, the data is read up to the end of the FRU
                inventory area.
            fru_id: The FRU device ID.

        Returns:
            The data read.

        Raises:
            CompletionCodeError: The device rejected a read request, also
                with the smallest chunk size.
        """
        read_length = self._fru_read_lengths.setdefault(fru_id, ReadLength())
        data = array.array('B')

        # first check for maximum area size
        if offset is None or count is None:
            area_size = self.get_fru_inventory_area_info(fru_id)
            off = offset or 0
        else:
            area_size = offset + count
            off = offset

        while off < area_size:
            req_size = min(read_length.length, area_size - off)

            try:
                rsp = self.send_message_with_name('ReadFruData', fru_id=fru_id,
                                                  offset=off, count=req_size)
            except CompletionCodeError as ex:
                if ex.cc in (constants.CC_CANT_RET_NUM_REQ_BYTES,
                             constants.CC_REQ_DATA_FIELD_EXCEED,
                             constants.CC_PARAM_OUT_OF_RANGE):
                    try:
                        read_length.reduce(req_size, 2)
                    except RetryError:
                        raise ex from None
                    continue
                else:
                    raise

            data.extend(rsp.data)
            off += rsp.count

        return py3_array_tobytes(data)

    def read_fru_data_full(self, fru_id: int = 0) -> bytes:
        """Read the whole FRU inventory area.

        Args:
            fru_id: The FRU device ID.

        Returns:
            The data of the FRU inventory area.
        """
        return self.read_fru_data(fru_id=fru_id)

    def _get_fru_size(self, fru_id: int) -> int | None:
        """Return the size of the FRU data or None if it is not known."""
        try:
            return self.get_fru_inventory_area_info(fru_id)
        except CompletionCodeError:
            return None

    def get_fru_inventory_header(self, fru_id: int = 0,
                                 ignore_checksum: bool = False) -> InventoryCommonHeader:
        """Read the common header of the FRU inventory.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Returns:
            The common header, with ``fru_size`` set if the device reports
            the size of the FRU inventory area.

        Raises:
            DecodingError: The header is too short or its checksum is
                wrong.
        """
        data = self.read_fru_data(offset=0, count=8, fru_id=fru_id)
        header = InventoryCommonHeader(data, ignore_checksum=ignore_checksum)
        header.fru_size = self._get_fru_size(fru_id)
        return header

    @staticmethod
    def _check_fru_size(header: InventoryCommonHeader | None, name: str,
                        offset: int, length: int) -> None:
        # Reading beyond the end of the FRU data fails with a completion
        # code that does not tell what is wrong (e.g. 0xc9 or 0xcc).
        fru_size = header.fru_size if header is not None else None
        if fru_size is not None and offset + length > fru_size:
            raise DecodingError(f'{name} at offset 0x{offset:x} with '
                                f'{length} bytes exceeds the FRU size of '
                                f'{fru_size} bytes')

    def _read_fru_area(self, offset: int | None, fru_id: int = 0,
                       header: InventoryCommonHeader | None = None,
                       name: str = 'area') -> bytes:
        # The first read returns the area length and, if possible, all of the
        # area data: read up to the start of the next area. For the last area
        # only its minimal size of 8 bytes is known to be within the FRU data.
        if offset is None:
            raise DataNotFound(f'FRU has no {name}')
        count = FRU_AREA_MIN_LENGTH
        if header is not None:
            next_offsets = [o for o in header.area_offsets() if o > offset]
            if next_offsets:
                count = min(next_offsets) - offset

        self._check_fru_size(header, name, offset, FRU_AREA_MIN_LENGTH)
        if header is not None and header.fru_size is not None:
            count = min(count, header.fru_size - offset)

        data = self.read_fru_data(offset=offset, count=count, fru_id=fru_id)
        length = data[1] * 8
        self._check_fru_size(header, name, offset, length)
        if length > len(data):
            data += self.read_fru_data(offset=offset + len(data),
                                       count=length - len(data),
                                       fru_id=fru_id)
        return data[:length]

    def _get_header(self, fru_id: int, ignore_checksum: bool,
                    header: InventoryCommonHeader | None
                    ) -> InventoryCommonHeader:
        if header is None:
            header = self.get_fru_inventory_header(
                fru_id=fru_id, ignore_checksum=ignore_checksum)
        return header

    def get_fru_internal_use_area(self, fru_id: int = 0,
                                  ignore_checksum: bool = False,
                                  header: InventoryCommonHeader | None = None
                                  ) -> InventoryInternalUseArea:
        """Read and decode the internal use area.

        The area is read up to the next area, or up to the end of the FRU
        data if it is the last area.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum of the common header, the area has no checksum.
            header: The common header of the FRU inventory, it is read from
                the device if None. Pass the header to read several areas
                without reading it again.

        Returns:
            The decoded internal use area.

        Raises:
            DataNotFound: The FRU inventory has no internal use area.
            DecodingError: The area exceeds the size of the FRU inventory
                area.
        """
        header = self._get_header(fru_id, ignore_checksum, header)
        offset = header.internal_use_area_offset
        if offset is None:
            raise DataNotFound('FRU has no internal use area')
        end = header.next_area_offset(offset)
        if end is None:
            end = header.fru_size
        if end is None:
            # the last area and the FRU size is unknown: read to the end
            data = self.read_fru_data(offset=offset, fru_id=fru_id)
        else:
            self._check_fru_size(header, 'internal use area', offset,
                                 end - offset)
            data = self.read_fru_data(offset=offset, count=end - offset,
                                      fru_id=fru_id)
        return InventoryInternalUseArea(data)

    def get_fru_chassis_area(self, fru_id: int = 0,
                             ignore_checksum: bool = False,
                             header: InventoryCommonHeader | None = None
                             ) -> InventoryChassisInfoArea:
        """Read and decode the chassis info area.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.
            header: The common header of the FRU inventory, it is read from
                the device if None. Pass the header to read several areas
                without reading it again.

        Returns:
            The decoded chassis info area.

        Raises:
            DataNotFound: The FRU inventory has no chassis info area.
            DecodingError: The area is invalid, its checksum is wrong or it
                exceeds the size of the FRU inventory area.
        """
        header = self._get_header(fru_id, ignore_checksum, header)
        data = self._read_fru_area(offset=header.chassis_info_area_offset,
                                   fru_id=fru_id, header=header,
                                   name='chassis info area')
        return InventoryChassisInfoArea(data, ignore_checksum=ignore_checksum)

    def get_fru_board_area(self, fru_id: int = 0,
                           ignore_checksum: bool = False,
                           header: InventoryCommonHeader | None = None
                           ) -> InventoryBoardInfoArea:
        """Read and decode the board info area.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.
            header: The common header of the FRU inventory, it is read from
                the device if None. Pass the header to read several areas
                without reading it again.

        Returns:
            The decoded board info area.

        Raises:
            DataNotFound: The FRU inventory has no board info area.
            DecodingError: The area is invalid, its checksum is wrong or it
                exceeds the size of the FRU inventory area.
        """
        header = self._get_header(fru_id, ignore_checksum, header)
        data = self._read_fru_area(offset=header.board_info_area_offset,
                                   fru_id=fru_id, header=header,
                                   name='board info area')
        return InventoryBoardInfoArea(data, ignore_checksum=ignore_checksum)

    def get_fru_product_area(self, fru_id: int = 0,
                             ignore_checksum: bool = False,
                             header: InventoryCommonHeader | None = None
                             ) -> InventoryProductInfoArea:
        """Read and decode the product info area.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.
            header: The common header of the FRU inventory, it is read from
                the device if None. Pass the header to read several areas
                without reading it again.

        Returns:
            The decoded product info area.

        Raises:
            DataNotFound: The FRU inventory has no product info area.
            DecodingError: The area is invalid, its checksum is wrong or it
                exceeds the size of the FRU inventory area.
        """
        header = self._get_header(fru_id, ignore_checksum, header)
        data = self._read_fru_area(offset=header.product_info_area_offset,
                                   fru_id=fru_id, header=header,
                                   name='product info area')
        return InventoryProductInfoArea(data, ignore_checksum=ignore_checksum)

    def get_fru_multirecord_area(self, fru_id: int = 0,
                                 ignore_checksum: bool = False,
                                 header: InventoryCommonHeader | None = None
                                 ) -> InventoryMultiRecordArea:
        """Read and decode the multirecord area.

        The records are read up to the record with the end of list flag, or
        up to the next area or the end of the FRU data if the flag is
        missing.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.
            header: The common header of the FRU inventory, it is read from
                the device if None. Pass the header to read several areas
                without reading it again.

        Returns:
            The decoded multirecord area.

        Raises:
            DataNotFound: The FRU inventory has no multirecord area.
            DecodingError: The area is invalid, its checksum is wrong or it
                exceeds the size of the FRU inventory area.
        """
        header = self._get_header(fru_id, ignore_checksum, header)

        # we have to determine the length of the area first
        if header.multirecord_area_offset is None:
            raise DataNotFound('FRU has no multirecord area')
        offset = header.multirecord_area_offset
        count = 0
        # the area ends at the next area or at the end of the FRU data, if
        # the end of list flag is missing
        end = header.next_area_offset(offset)
        if end is None:
            end = header.fru_size

        while end is None or offset < end:
            # read the header
            self._check_fru_size(header, 'multirecord area', offset, 5)
            data = self.read_fru_data(offset=offset, count=5, fru_id=fru_id)
            end_of_list = bool(data[1] & 0x80)
            length = data[2]
            count += length + 5
            offset += length + 5
            if end_of_list:
                break

        # now read the full area
        offset = header.multirecord_area_offset
        if end is not None and offset + count > end:
            raise DecodingError(f'multirecord area at offset 0x{offset:x} '
                                f'with {count} bytes exceeds the next area '
                                f'or the FRU data at 0x{end:x}')
        self._check_fru_size(header, 'multirecord area', offset, count)
        data = self.read_fru_data(offset=offset, count=count, fru_id=fru_id)
        return InventoryMultiRecordArea(data, ignore_checksum=ignore_checksum)

    def get_fru_inventory(self, fru_id: int = 0,
                          ignore_checksum: bool = False) -> FruInventory:
        """Read and decode the whole FRU inventory.

        Args:
            fru_id: The FRU device ID.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Returns:
            The FRU inventory with all areas that are present.

        Raises:
            DecodingError: An area is invalid, its checksum is wrong or it
                exceeds the size of the FRU inventory area.
        """
        fru = FruInventory()

        header = self.get_fru_inventory_header(
            fru_id=fru_id,
            ignore_checksum=ignore_checksum
        )

        if header.internal_use_area_offset:
            fru.internal_use_area = self.get_fru_internal_use_area(
                fru_id=fru_id,
                ignore_checksum=ignore_checksum,
                header=header
            )

        if header.chassis_info_area_offset:
            fru.chassis_info_area = self.get_fru_chassis_area(
                fru_id=fru_id,
                ignore_checksum=ignore_checksum,
                header=header
            )

        if header.board_info_area_offset:
            fru.board_info_area = self.get_fru_board_area(
                fru_id=fru_id,
                ignore_checksum=ignore_checksum,
                header=header
            )

        if header.product_info_area_offset:
            fru.product_info_area = self.get_fru_product_area(
                fru_id=fru_id,
                ignore_checksum=ignore_checksum,
                header=header
            )

        if header.multirecord_area_offset:
            fru.multirecord_area = self.get_fru_multirecord_area(
                fru_id=fru_id,
                ignore_checksum=ignore_checksum,
                header=header
            )

        return fru


def get_fru_inventory_from_file(filename: str,
                                ignore_checksum: bool = False) -> FruInventory:
    """Decode the FRU inventory data of a file.

    Args:
        filename: The name of the file with the binary FRU inventory data.
        ignore_checksum: Don't raise a DecodingError on a wrong checksum.

    Returns:
        The decoded FRU inventory.

    Raises:
        OSError: The file cannot be read.
        DecodingError: An area is invalid or its checksum is wrong.
    """
    with open(filename, 'rb') as file:
        data = array.array('B', file.read())
    return FruInventory(data, ignore_checksum=ignore_checksum)


CUSTOM_FIELD_END = 0xc1


def _decode_custom_fields(data: Sequence[int]) -> list[FruTypeLengthString]:
    offset = 0
    fields = []
    while data[offset] != CUSTOM_FIELD_END:
        field = FruTypeLengthString(data, offset)
        fields.append(field)
        offset += field.length + 1
    return fields


class FruData:
    """Base class of the decoded parts of the FRU inventory data.

    Attributes:
        data: The data the object was decoded from.
    """

    def __init__(self, data: str | Sequence[int] | None = None,
                 ignore_checksum: bool = False) -> None:
        """Decode the data.

        Args:
            data: The data as bytes, a sequence of ints or a string of byte
                values. Nothing is decoded if it is None or empty.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Raises:
            DecodingError: The data is invalid or its checksum is wrong.
        """
        if data:
            if isinstance(data, str):
                data = [ord(c) for c in data]
            self.data = data
            if hasattr(self, '_from_data'):
                self._from_data(data, ignore_checksum=ignore_checksum)


class InventoryCommonHeader(FruData):
    """The common header of the FRU inventory.

    The area offsets are in bytes from the start of the FRU inventory data,
    they are None if the area is not present.

    Attributes:
        format_version: The format version of the common header.
        internal_use_area_offset: The offset of the internal use area.
        chassis_info_area_offset: The offset of the chassis info area.
        board_info_area_offset: The offset of the board info area.
        product_info_area_offset: The offset of the product info area.
        multirecord_area_offset: The offset of the multirecord area.
    """

    #: The size of the FRU data if it is read from a device that reports
    #: it, otherwise None.
    fru_size: int | None = None

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        if len(data) < 8:
            raise DecodingError('InventoryCommonHeader length != 8')
        self.format_version = data[0] & 0x0f
        self.internal_use_area_offset = data[1] * 8 or None
        self.chassis_info_area_offset = data[2] * 8 or None
        self.board_info_area_offset = data[3] * 8 or None
        self.product_info_area_offset = data[4] * 8 or None
        self.multirecord_area_offset = data[5] * 8 or None
        if sum(data[:8]) % 256 != 0 and ignore_checksum is False:
            raise DecodingError(f'InventoryCommonHeader checksum failed {sum(data) % 0x10}')

    def area_offsets(self) -> list[int]:
        """Return the offsets of all present areas."""
        offsets = (self.internal_use_area_offset,
                   self.chassis_info_area_offset,
                   self.board_info_area_offset,
                   self.product_info_area_offset,
                   self.multirecord_area_offset)
        return [o for o in offsets if o is not None]

    def next_area_offset(self, offset: int) -> int | None:
        """Return the offset of the area that follows an offset.

        Args:
            offset: The offset in the FRU inventory data.

        Returns:
            The lowest area offset greater than ``offset``, None if no area
            follows.
        """
        return min((o for o in self.area_offsets() if o > offset),
                   default=None)


class InventoryInternalUseArea(FruData):
    """The internal use area.

    The area has a format version and data defined by the manufacturer.
    It has neither a length nor a checksum, it ends at the next area or at
    the end of the FRU data. The format version is not checked, e.g. an
    erased area has the format version 0x0f.

    Attributes:
        format_version (int): The format version of the area, 1 for the
            IPMI FRU specification.
        internal_use_data (bytes): The data of the area after the format
            version.
    """

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        self.format_version = data[0] & 0x0f
        self.internal_use_data = bytes(data[1:])


class CommonInfoArea(FruData):
    """Base class of the chassis, board and product info areas.

    Attributes:
        format_version: The format version of the area, only version 1 is
            supported.
        length: The length of the area in bytes.
    """

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        self.format_version = data[0] & 0x0f
        if self.format_version != 1:
            raise DecodingError('unsupported format version (%d)' %
                                self.format_version)
        self.length = data[1] * 8
        if sum(data[:self.length]) % 256 != 0 and ignore_checksum is False:
            raise DecodingError('checksum failed')


class InventoryChassisInfoArea(CommonInfoArea):
    """The chassis info area.

    The ``TYPE_*`` constants are the chassis types of the SMBIOS
    specification.

    Attributes:
        type (int): The chassis type, one of the ``TYPE_*`` constants.
        part_number (FruTypeLengthString): The chassis part number.
        serial_number (FruTypeLengthString): The chassis serial number.
        custom_chassis_info (list[FruTypeLengthString]): The custom chassis
            info fields.
    """

    TYPE_OTHER = 1
    TYPE_UNKNOWN = 2
    TYPE_DESKTOP = 3
    TYPE_LOW_PROFILE_DESKTOP = 4
    TYPE_PIZZA_BOX = 5
    TYPE_MINI_TOWER = 6
    TYPE_TOWER = 7
    TYPE_PORTABLE = 8
    TYPE_LAPTOP = 9
    TYPE_NOTEBOOK = 10
    TYPE_HAND_HELD = 11
    TYPE_DOCKING_STATION = 12
    TYPE_ALL_IN_ONE = 13
    TYPE_SUB_NOTEBOOK = 14
    TYPE_SPACE_SAVING = 15
    TYPE_LUNCH_BOX = 16
    TYPE_MAIN_SERVER_CHASSIS = 17
    TYPE_EXPANSION_CHASSIS = 18
    TYPE_SUB_CHASSIS = 19
    TYPE_BUS_EXPANSION_CHASSIS = 20
    TYPE_PERIPHERAL_CHASSIS = 21
    TYPE_RAID_CHASSIS = 22
    TYPE_RACK_MOUNT_CHASSIS = 23

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        CommonInfoArea._from_data(self, data, ignore_checksum=ignore_checksum)
        self.type = data[2]
        offset = 3
        self.part_number = FruTypeLengthString(data, offset)
        offset += self.part_number.length + 1
        self.serial_number = FruTypeLengthString(data, offset, True)
        offset += self.serial_number.length + 1
        self.custom_chassis_info = _decode_custom_fields(data[offset:])


class InventoryBoardInfoArea(CommonInfoArea):
    """The board info area.

    Attributes:
        language_code (int): The language code of the strings.
        mfg_date (datetime.datetime): The manufacturing date and time.
        manufacturer (FruTypeLengthString): The board manufacturer.
        product_name (FruTypeLengthString): The board product name.
        serial_number (FruTypeLengthString): The board serial number.
        part_number (FruTypeLengthString): The board part number.
        fru_file_id (FruTypeLengthString): The FRU file ID.
        custom_mfg_info (list[FruTypeLengthString]): The custom board info
            fields.
    """

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        CommonInfoArea._from_data(self, data, ignore_checksum=ignore_checksum)
        self.language_code = data[2]
        minutes = data[5] << 16 | data[4] << 8 | data[3]
        self.mfg_date = (datetime.datetime(1996, 1, 1)
                         + datetime.timedelta(minutes=minutes))
        offset = 6
        self.manufacturer = FruTypeLengthString(data, offset)
        offset += self.manufacturer.length + 1
        self.product_name = FruTypeLengthString(data, offset)
        offset += self.product_name.length + 1
        self.serial_number = FruTypeLengthString(data, offset, True)
        offset += self.serial_number.length + 1
        self.part_number = FruTypeLengthString(data, offset)
        offset += self.part_number.length + 1
        self.fru_file_id = FruTypeLengthString(data, offset, True)
        offset += self.fru_file_id.length + 1
        self.custom_mfg_info = _decode_custom_fields(data[offset:])


class InventoryProductInfoArea(CommonInfoArea):
    """The product info area.

    Attributes:
        language_code (int): The language code of the strings.
        manufacturer (FruTypeLengthString): The product manufacturer.
        name (FruTypeLengthString): The product name.
        part_number (FruTypeLengthString): The product part or model
            number.
        version (FruTypeLengthString): The product version.
        serial_number (FruTypeLengthString): The product serial number.
        asset_tag (FruTypeLengthString): The asset tag.
        fru_file_id (FruTypeLengthString): The FRU file ID.
        custom_mfg_info (list[FruTypeLengthString]): The custom product
            info fields.
    """

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        CommonInfoArea._from_data(self, data, ignore_checksum=ignore_checksum)
        self.language_code = data[2]
        offset = 3
        self.manufacturer = FruTypeLengthString(data, offset)
        offset += self.manufacturer.length + 1
        self.name = FruTypeLengthString(data, offset)
        offset += self.name.length + 1
        self.part_number = FruTypeLengthString(data, offset)
        offset += self.part_number.length + 1
        self.version = FruTypeLengthString(data, offset)
        offset += self.version.length + 1
        self.serial_number = FruTypeLengthString(data, offset, True)
        offset += self.serial_number.length + 1
        self.asset_tag = FruTypeLengthString(data, offset)
        offset += self.asset_tag.length + 1
        self.fru_file_id = FruTypeLengthString(data, offset, True)
        offset += self.fru_file_id.length + 1
        self.custom_mfg_info = list()
        self.custom_mfg_info = _decode_custom_fields(data[offset:])


class FruDataMultiRecord(FruData):
    """A record of the multirecord area.

    The ``TYPE_*`` constants are the record type IDs.

    Attributes:
        record_type_id (int): The record type ID.
        format_version (int): The format version of the record.
        end_of_list (bool): True for the last record of the area.
        length (int): The length of the record data in bytes.
        raw (Sequence[int]): The record data, without the record header.
        manufacturer_id (int | None): The IANA manufacturer ID of an OEM
            record (``TYPE_OEM``), from the first three bytes of the
            record data. None for other records.
        manufacturer_name (str | None): The name of a well known
            manufacturer of an OEM record, see
            :func:`pyipmi.constants.manufacturer_name`. None for other
            manufacturers and records.
    """

    TYPE_POWER_SUPPLY_INFORMATION = 0
    TYPE_DC_OUTPUT = 1
    TYPE_DC_LOAD = 2
    TYPE_MANAGEMENT_ACCESS_RECORD = 3
    TYPE_BASE_COMPATIBILITY_RECORD = 4
    TYPE_EXTENDED_COMPATIBILITY_RECORD = 5
    TYPE_OEM = list(range(0xc0, 0x100))
    TYPE_OEM_PICMG = 0xc0
    TYPE_OEM_FMC = 0xfa

    def __str__(self) -> str:
        """Return the record type ID and the record data as hex string.

        The manufacturer ID of an OEM record is added to the record type.
        """
        return '%s: %s' % (self._type_string(),
                           ' '.join('%02x' % b for b in self.raw))

    def _type_string(self) -> str:
        """Return the record type ID and the manufacturer of an OEM record."""
        record_type = '%02x' % self.record_type_id
        if self.manufacturer_id is not None:
            manufacturer = '%d' % self.manufacturer_id
            if self.manufacturer_name is not None:
                manufacturer += ' = %s' % self.manufacturer_name
            record_type += ' (OEM, manufacturer ID %s)' % manufacturer
        return record_type

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        if len(data) < 5:
            raise DecodingError('data too short')
        self.record_type_id = data[0]
        self.format_version = data[1] & 0x0f
        self.end_of_list = bool(data[1] & 0x80)
        self.length = data[2]
        if sum(data[:5]) % 256 != 0 and ignore_checksum is False:
            raise DecodingError('FruDataMultiRecord header checksum failed')
        self.raw = data[5:5+self.length]
        if len(self.raw) < self.length:
            raise DecodingError('FruDataMultiRecord record data exceeds the '
                                'multirecord area')
        if (sum(self.raw) + data[3]) % 256 != 0 and ignore_checksum is False:
            raise DecodingError('FruDataMultiRecord record checksum failed')
        # an OEM record starts with the manufacturer ID, LS byte first
        self.manufacturer_id: int | None = None
        self.manufacturer_name: str | None = None
        if self.record_type_id in self.TYPE_OEM and len(self.raw) >= 3:
            self.manufacturer_id = \
                self.raw[0] | self.raw[1] << 8 | self.raw[2] << 16
            self.manufacturer_name = manufacturer_name(self.manufacturer_id)

    @staticmethod
    def create_from_record_id(data: Sequence[int],
                              ignore_checksum: bool = False
                              ) -> FruDataMultiRecord:
        """Decode a record with the class for its record type.

        DC Output and DC Load records are decoded by
        :class:`FruDcOutputRecord` and :class:`FruDcLoadRecord`, PICMG
        records by :class:`FruPicmgRecord`, the FMC records of VITA by
        :class:`FruFmcRecord` and the other records by
        :class:`FruDataUnknown`.

        Args:
            data: The data of the multirecord area, starting with the
                record.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Returns:
            The decoded record.
        """
        record_type = data[0]
        if record_type == FruDataMultiRecord.TYPE_OEM_PICMG:
            return FruPicmgRecord.create_from_record_id(
                data, ignore_checksum=ignore_checksum)
        if record_type == FruDataMultiRecord.TYPE_DC_OUTPUT:
            return FruDcOutputRecord(data, ignore_checksum=ignore_checksum)
        if record_type == FruDataMultiRecord.TYPE_DC_LOAD:
            return FruDcLoadRecord(data, ignore_checksum=ignore_checksum)
        # an FMC record starts with the manufacturer ID of VITA
        if (record_type == FruDataMultiRecord.TYPE_OEM_FMC
                and len(data) >= 8 and data[2] >= 3
                and data[5] | data[6] << 8 | data[7] << 16
                == VITA_MANUFACTURER_ID):
            return FruFmcRecord.create_from_record_id(
                data, ignore_checksum=ignore_checksum)
        return FruDataUnknown(data, ignore_checksum=ignore_checksum)


class FruDataUnknown(FruDataMultiRecord):
    """A record of a type that is not decoded, only its header is."""


class FruPicmgRecord(FruDataMultiRecord):
    """A PICMG record, an OEM record with the PICMG manufacturer ID.

    The ``PICMG_RECORD_ID_*`` constants are the PICMG record type IDs.

    Attributes:
        manufacturer_id (int): The manufacturer ID, 0x315A for PICMG.
        picmg_record_type_id (int): The PICMG record type ID, one of the
            ``PICMG_RECORD_ID_*`` constants.
        format_version (int): The format version of the PICMG record.
    """

    PICMG_RECORD_ID_BACKPLANE_PTP_CONNECTIVITY = 0x04
    PICMG_RECORD_ID_ADDRESS_TABLE = 0x10
    PICMG_RECORD_ID_SHELF_POWER_DISTRIBUTION = 0x11
    PICMG_RECORD_ID_SHMC_ACTIVATION_MANAGEMENT = 0x12
    PICMG_RECORD_ID_SHMC_IP_CONNECTION = 0x13
    PICMG_RECORD_ID_BOARD_PTP_CONNECTIVITY = 0x14
    PICMG_RECORD_ID_RADIAL_IPMB0_LINK_MAPPING = 0x15
    PICMG_RECORD_ID_MODULE_CURRENT_REQUIREMENTS = 0x16
    PICMG_RECORD_ID_CARRIER_ACTIVATION_MANAGEMENT = 0x17
    PICMG_RECORD_ID_CARRIER_PTP_CONNECTIVITY = 0x18
    PICMG_RECORD_ID_AMC_PTP_CONNECTIVITY = 0x19
    PICMG_RECORD_ID_CARRIER_INFORMATION = 0x1a
    PICMG_RECORD_ID_MTCA_FRU_INFORMATION_PARTITION = 0x20
    PICMG_RECORD_ID_MTCA_CARRIER_MANAGER_IP_LINK = 0x21
    PICMG_RECORD_ID_MTCA_CARRIER_INFORMATION = 0x22
    PICMG_RECORD_ID_MTCA_SHELF_INFORMATION = 0x23
    PICMG_RECORD_ID_MTCA_SHELF_MANAGER_IP_LINK = 0x24
    PICMG_RECORD_ID_MTCA_CARRIER_POWER_POLICY = 0x25
    PICMG_RECORD_ID_MTCA_CARRIER_ACTIVATION_AND_POWER = 0x26
    PICMG_RECORD_ID_MTCA_POWER_MODULE_CAPABILITY = 0x27
    PICMG_RECORD_ID_MTCA_FAN_GEOGRAPHY = 0x28
    PICMG_RECORD_ID_OEM_MODULE_DESCRIPTION = 0x29
    PICMG_RECORD_ID_CARRIER_CLOCK_PTP_CONNECTIVITY = 0x2C
    PICMG_RECORD_ID_CLOCK_CONFIGURATION = 0x2d
    PICMG_RECORD_ID_ZONE_3_INTERFACE_COMPATIBILITY = 0x30
    PICMG_RECORD_ID_CARRIER_BUSED_CONNECTIVITY = 0x31
    PICMG_RECORD_ID_ZONE_3_INTERFACE_DOCUMENTATION = 0x32

    def __init__(self, data: Sequence[int],
                 ignore_checksum: bool = False) -> None:
        """Decode the PICMG record.

        Args:
            data: The data of the multirecord area, starting with the
                record.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Raises:
            DecodingError: The data is too short or a checksum is wrong.
        """
        FruDataMultiRecord.__init__(self, data,
                                    ignore_checksum=ignore_checksum)

    @staticmethod
    def create_from_record_id(data: Sequence[int],
                              ignore_checksum: bool = False) -> FruPicmgRecord:
        """Decode a PICMG record with the class for its PICMG record type.

        The Power Module Capability record is decoded by
        :class:`FruPicmgPowerModuleCapabilityRecord`, the other records by
        :class:`FruPicmgRecord`.

        Args:
            data: The data of the multirecord area, starting with the
                record.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Returns:
            The decoded record.
        """
        picmg_record = FruPicmgRecord(data, ignore_checksum=ignore_checksum)
        if picmg_record.picmg_record_type_id ==\
                FruPicmgRecord.PICMG_RECORD_ID_MTCA_POWER_MODULE_CAPABILITY:
            return FruPicmgPowerModuleCapabilityRecord(
                data, ignore_checksum=ignore_checksum)

        return picmg_record

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        if len(data) < 10:
            raise DecodingError('data too short')
        data = array.array('B', data)
        FruDataMultiRecord._from_data(self, data, ignore_checksum=ignore_checksum)
        self.manufacturer_id = \
            data[5] | data[6] << 8 | data[7] << 16
        self.picmg_record_type_id = data[8]
        self.format_version = data[9]


class FruPicmgPowerModuleCapabilityRecord(FruPicmgRecord):
    """The MicroTCA Power Module Capability record.

    Attributes:
        maximum_current_output (float): The maximum current output in
            amperes.
    """

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        if len(data) < 12:
            raise DecodingError('data too short')
        FruPicmgRecord._from_data(self, data, ignore_checksum=ignore_checksum)
        maximum_current_output = data[10] | data[11] << 8
        self.maximum_current_output = float(maximum_current_output/10)


def _int16(data: bytes, offset: int, signed: bool = False) -> int:
    """Return the 16 bit value at offset, LS byte first."""
    return int.from_bytes(data[offset:offset + 2], 'little', signed=signed)


class FruDcOutputRecord(FruDataMultiRecord):
    """A DC Output record (type 0x01).

    The record describes a DC output of the FRU, e.g. a voltage an FMC module
    supplies to its carrier. The voltages are in mV, the currents in mA.

    Attributes:
        standby_enable (bool): The output is also on in standby.
        output_number (int): The output number. ANSI/VITA 57.1 assigns the
            numbers of an FMC module: 0 VADJ, 1 3P3V, 2 12P0V, 3 VIO_B_M2C,
            4 VREF_A_M2C, 5 VREF_B_M2C of P1, 6 - 11 the same for P2.
        nominal_voltage (int): The nominal voltage.
        max_negative_voltage (int): The maximum negative voltage deviation.
            The FRU data of FMC modules store the lower voltage limit.
        max_positive_voltage (int): The maximum positive voltage deviation.
            The FRU data of FMC modules store the upper voltage limit.
        ripple_and_noise (int): The ripple and noise peak to peak.
        min_current_draw (int): The minimum current draw.
        max_current_draw (int): The maximum current draw.
    """

    def __str__(self) -> str:
        """Return the record type and the decoded values."""
        return ('%s DC Output %d: %d mV (%d - %d mV), ripple and noise %d mV, '
                '%d - %d mA%s'
                % (self._type_string(), self.output_number,
                   self.nominal_voltage, self.max_negative_voltage,
                   self.max_positive_voltage, self.ripple_and_noise,
                   self.min_current_draw, self.max_current_draw,
                   ', standby' if self.standby_enable else ''))

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruDataMultiRecord._from_data(self, data,
                                      ignore_checksum=ignore_checksum)
        raw = bytes(self.raw)
        if len(raw) < 13:
            raise DecodingError('DC output record too short (%d bytes)'
                                % len(raw))
        self.standby_enable = bool(raw[0] & 0x80)
        self.output_number = raw[0] & 0x0f
        # the voltages are signed and in 10 mV units
        self.nominal_voltage = _int16(raw, 1, signed=True) * 10
        self.max_negative_voltage = _int16(raw, 3, signed=True) * 10
        self.max_positive_voltage = _int16(raw, 5, signed=True) * 10
        self.ripple_and_noise = _int16(raw, 7)
        self.min_current_draw = _int16(raw, 9)
        self.max_current_draw = _int16(raw, 11)


class FruDcLoadRecord(FruDataMultiRecord):
    """A DC Load record (type 0x02).

    The record describes a DC load of the FRU, e.g. a voltage an FMC module
    needs from its carrier. The voltages are in mV, the currents in mA.

    Attributes:
        output_number (int): The number of the output that supplies the
            load, see :class:`FruDcOutputRecord`.
        nominal_voltage (int): The nominal voltage.
        min_voltage (int): The minimum voltage.
        max_voltage (int): The maximum voltage.
        ripple_and_noise (int): The ripple and noise peak to peak.
        min_current_load (int): The minimum current load.
        max_current_load (int): The maximum current load.
    """

    def __str__(self) -> str:
        """Return the record type and the decoded values."""
        return ('%s DC Load %d: %d mV (%d - %d mV), ripple and noise %d mV, '
                '%d - %d mA'
                % (self._type_string(), self.output_number,
                   self.nominal_voltage, self.min_voltage, self.max_voltage,
                   self.ripple_and_noise, self.min_current_load,
                   self.max_current_load))

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruDataMultiRecord._from_data(self, data,
                                      ignore_checksum=ignore_checksum)
        raw = bytes(self.raw)
        if len(raw) < 13:
            raise DecodingError('DC load record too short (%d bytes)'
                                % len(raw))
        self.output_number = raw[0] & 0x0f
        # the voltages are signed and in 10 mV units
        self.nominal_voltage = _int16(raw, 1, signed=True) * 10
        self.min_voltage = _int16(raw, 3, signed=True) * 10
        self.max_voltage = _int16(raw, 5, signed=True) * 10
        self.ripple_and_noise = _int16(raw, 7)
        self.min_current_load = _int16(raw, 9)
        self.max_current_load = _int16(raw, 11)


# the manufacturer ID of the FMC records of ANSI/VITA 57
VITA_MANUFACTURER_ID = 0x0012a2


class FruFmcRecord(FruDataMultiRecord):
    """An FMC record of ANSI/VITA 57, an OEM record of VITA (type 0xFA).

    The records are decoded by :meth:`create_from_record_id` with the class
    for their subtype, a record of an unknown subtype by this class. The
    ``SUBTYPE_*`` constants are the subtypes, the ``MODULE_SIZE_*``,
    ``CONNECTOR_*`` and ``CLOCK_DIRECTION_*`` constants the values of the
    main definitions.

    Attributes:
        subtype (int): The subtype of the FMC record.
    """

    SUBTYPE_MAIN_DEFINITION = 0x00
    SUBTYPE_PLUS_MAIN_DEFINITION = 0x01
    SUBTYPE_I2C_DEVICE_DEFINITION = 0x10

    MODULE_SIZE_SINGLE_WIDTH = 0
    MODULE_SIZE_DOUBLE_WIDTH = 1

    CONNECTOR_LPC = 0
    CONNECTOR_HPC = 1
    CONNECTOR_HSPC = 2

    CLOCK_DIRECTION_M2C = 0
    CLOCK_DIRECTION_C2M = 1

    _MODULE_SIZES = {0: 'single width', 1: 'double width'}
    _CLOCK_DIRECTIONS = {0: 'M2C', 1: 'C2M'}

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruDataMultiRecord._from_data(self, data,
                                      ignore_checksum=ignore_checksum)
        if len(self.raw) < 4:
            raise DecodingError('FMC record too short (%d bytes)'
                                % len(self.raw))
        self.subtype = self.raw[3]

    @staticmethod
    def create_from_record_id(data: Sequence[int],
                              ignore_checksum: bool = False) -> FruFmcRecord:
        """Decode an FMC record with the class for its subtype.

        Args:
            data: The data of the multirecord area, starting with the
                record.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Returns:
            The decoded record.

        Raises:
            DecodingError: The record is too short or a checksum is wrong.
        """
        record = FruFmcRecord(data, ignore_checksum=ignore_checksum)
        cls = {
            FruFmcRecord.SUBTYPE_MAIN_DEFINITION: FruFmcMainDefinition,
            FruFmcRecord.SUBTYPE_PLUS_MAIN_DEFINITION:
                FruFmcPlusMainDefinition,
            FruFmcRecord.SUBTYPE_I2C_DEVICE_DEFINITION:
                FruFmcI2cDeviceDefinition,
        }.get(record.subtype)
        if cls is None:
            return record
        return cls(data, ignore_checksum=ignore_checksum)

    def _check_length(self, length: int) -> bytes:
        """Return the data after the subtype, raise if it is too short."""
        payload = bytes(self.raw[4:])
        if len(payload) < length:
            raise DecodingError('FMC record subtype %d too short (%d bytes)'
                                % (self.subtype, len(payload)))
        return payload

    @staticmethod
    def _name(names: dict[int, str], value: int) -> str:
        return names.get(value, 'reserved (%d)' % value)


class FruFmcMainDefinition(FruFmcRecord):
    """The FMC main definition record of ANSI/VITA 57.1.

    Attributes:
        module_size (int): One of the ``MODULE_SIZE_*`` constants.
        p1_connector_size (int): ``CONNECTOR_LPC``, ``CONNECTOR_HPC`` or
            ``CONNECTOR_NOT_FITTED``.
        p2_connector_size (int): ``CONNECTOR_LPC``, ``CONNECTOR_HPC`` or
            ``CONNECTOR_NOT_FITTED``.
        clock_direction (int): One of the ``CLOCK_DIRECTION_*`` constants.
        p1_a_num_signals (int): The number of signals of P1 bank A.
        p1_b_num_signals (int): The number of signals of P1 bank B.
        p2_a_num_signals (int): The number of signals of P2 bank A.
        p2_b_num_signals (int): The number of signals of P2 bank B.
        p1_gbt_num_trcv (int): The number of GBT transceivers of P1.
        p2_gbt_num_trcv (int): The number of GBT transceivers of P2.
        tck_max_clock (int): The maximum TCK clock in MHz.
    """

    CONNECTOR_NOT_FITTED = 3

    _CONNECTORS = {0: 'LPC', 1: 'HPC', 3: 'not fitted'}

    def __str__(self) -> str:
        """Return the record type and the decoded values."""
        return ('%s FMC Main Definition: %s, P1 %s, P2 %s, clock %s, '
                'P1 %d/%d signals, P2 %d/%d signals, P1 %d GBT, P2 %d GBT, '
                'TCK %d MHz'
                % (self._type_string(),
                   self._name(self._MODULE_SIZES, self.module_size),
                   self._name(self._CONNECTORS, self.p1_connector_size),
                   self._name(self._CONNECTORS, self.p2_connector_size),
                   self._name(self._CLOCK_DIRECTIONS, self.clock_direction),
                   self.p1_a_num_signals, self.p1_b_num_signals,
                   self.p2_a_num_signals, self.p2_b_num_signals,
                   self.p1_gbt_num_trcv, self.p2_gbt_num_trcv,
                   self.tck_max_clock))

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruFmcRecord._from_data(self, data, ignore_checksum=ignore_checksum)
        payload = self._check_length(7)
        self.module_size = payload[0] >> 6 & 0x3
        self.p1_connector_size = payload[0] >> 4 & 0x3
        self.p2_connector_size = payload[0] >> 2 & 0x3
        self.clock_direction = payload[0] >> 1 & 0x1
        self.p1_a_num_signals = payload[1]
        self.p1_b_num_signals = payload[2]
        self.p2_a_num_signals = payload[3]
        self.p2_b_num_signals = payload[4]
        self.p1_gbt_num_trcv = payload[5] >> 4
        self.p2_gbt_num_trcv = payload[5] & 0xf
        self.tck_max_clock = payload[6]


class FruFmcPlusMainDefinition(FruFmcRecord):
    """The FMC+ main definition record of ANSI/VITA 57.4.

    Attributes:
        module_size (int): One of the ``MODULE_SIZE_*`` constants.
        p1_p3_connector_size (int): ``CONNECTOR_LPC``, ``CONNECTOR_HPC``,
            ``CONNECTOR_HSPC`` or ``CONNECTOR_HSPC_HSPCE``.
        p2_p4_connector_size (int): ``CONNECTOR_LPC``, ``CONNECTOR_HPC``,
            ``CONNECTOR_HSPC``, ``CONNECTOR_HSPC_HSPCE`` or
            ``CONNECTOR_NOT_FITTED``.
        clock_direction (int): One of the ``CLOCK_DIRECTION_*`` constants.
        p1_a_num_signals (int): The number of signals of P1 bank A.
        p1_b_num_signals (int): The number of signals of P1 bank B.
        p2_a_num_signals (int): The number of signals of P2 bank A.
        p2_b_num_signals (int): The number of signals of P2 bank B.
        p1_gbt_num_trcv (int): The number of GBT transceivers of P1.
        p2_gbt_num_trcv (int): The number of GBT transceivers of P2.
        tck_max_clock (int): The maximum TCK clock in MHz.
    """

    # HSPC connector with an HSPCe extension connector (P3 or P4)
    CONNECTOR_HSPC_HSPCE = 3
    CONNECTOR_NOT_FITTED = 7

    _CONNECTORS = {0: 'LPC', 1: 'HPC', 2: 'HSPC', 3: 'HSPC/HSPCe',
                   7: 'not fitted'}

    def __str__(self) -> str:
        """Return the record type and the decoded values."""
        return ('%s FMC+ Main Definition: %s, P1/P3 %s, P2/P4 %s, clock %s, '
                'P1 %d/%d signals, P2 %d/%d signals, P1 %d GBT, P2 %d GBT, '
                'TCK %d MHz'
                % (self._type_string(),
                   self._name(self._MODULE_SIZES, self.module_size),
                   self._name(self._CONNECTORS, self.p1_p3_connector_size),
                   self._name(self._CONNECTORS, self.p2_p4_connector_size),
                   self._name(self._CLOCK_DIRECTIONS, self.clock_direction),
                   self.p1_a_num_signals, self.p1_b_num_signals,
                   self.p2_a_num_signals, self.p2_b_num_signals,
                   self.p1_gbt_num_trcv, self.p2_gbt_num_trcv,
                   self.tck_max_clock))

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruFmcRecord._from_data(self, data, ignore_checksum=ignore_checksum)
        payload = self._check_length(7)
        self.module_size = payload[0] >> 6 & 0x3
        self.p1_p3_connector_size = payload[0] >> 4 & 0x3
        self.p2_p4_connector_size = payload[0] >> 1 & 0x7
        self.clock_direction = payload[0] & 0x1
        self.p1_a_num_signals = payload[1]
        self.p2_a_num_signals = payload[2]
        # the 6 bit numbers of P2 bank B signals and P1 transceivers are
        # split over two bytes
        self.p1_b_num_signals = payload[3] & 0x3f
        self.p2_b_num_signals = (payload[4] & 0x0f) << 2 | payload[3] >> 6
        self.p1_gbt_num_trcv = (payload[5] & 0x03) << 4 | payload[4] >> 4
        self.p2_gbt_num_trcv = payload[5] >> 2
        self.tck_max_clock = payload[6]


class FruFmcI2cDeviceDefinition(FruFmcRecord):
    """The FMC I2C device definition record of ANSI/VITA 57.1.

    The record lists the I2C devices of an FMC module. It is a string in
    6-bit ASCII of the device addresses, each encoded as one character,
    followed by the device name.

    Attributes:
        devices (list[tuple[str, list[int]]]): The I2C devices as tuples of
            the device name and the device addresses.
    """

    def __str__(self) -> str:
        """Return the record type and the I2C devices."""
        devices = ', '.join('%s (%s)' % (name, ', '.join(map(str, addresses)))
                            for name, addresses in self.devices)
        return '%s FMC I2C Devices: %s' % (self._type_string(), devices)

    @staticmethod
    def _address(character: str) -> int | None:
        """Return the address of an address character, None for others.

        The characters '!' to '*' are the addresses 0 to 9, '+' to '/' the
        addresses 11 to 15, address 10 is not used.
        """
        code = ord(character) - ord('!')
        if 0 <= code < 10:
            return code
        if 10 <= code < 15:
            return code + 1
        return None

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        FruFmcRecord._from_data(self, data, ignore_checksum=ignore_checksum)
        payload = bytes(self.raw[4:])
        # the 6-bit ASCII is packed in groups of 3 bytes
        payload += bytes(-len(payload) % 3)
        text = _unpack6bitascii(payload)
        self.devices: list[tuple[str, list[int]]] = []
        position = 0
        while position < len(text):
            addresses = []
            while position < len(text):
                address = self._address(text[position])
                if address is None:
                    break
                addresses.append(address)
                position += 1
            start = position
            while position < len(text) and \
                    self._address(text[position]) is None:
                position += 1
            name = text[start:position].strip()
            if name or addresses:
                self.devices.append((name, addresses))


class InventoryMultiRecordArea:
    """The multirecord area.

    The list of records ends with the record with the end of list flag. If
    the flag is missing, it ends at the end of the area: at the next area
    or at the end of the FRU data.

    Attributes:
        records (list[FruDataMultiRecord]): The records of the area,
            decoded by :meth:`FruDataMultiRecord.create_from_record_id`.
    """

    def __init__(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        """Decode the multirecord area.

        Args:
            data: The data of the multirecord area.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Raises:
            DecodingError: A record is invalid or its checksum is wrong.
        """
        if data:
            self._from_data(data, ignore_checksum=ignore_checksum)

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        self.records = list()
        offset = 0
        # the list ends with the end of list flag, or at the end of the area
        # if the flag is missing
        while offset < len(data):
            record = FruDataMultiRecord.create_from_record_id(
                data[offset:], ignore_checksum=ignore_checksum)
            self.records.append(record)
            offset += record.length + 5
            if record.end_of_list:
                break


class FruInventory:
    """The decoded FRU inventory data.

    The areas are None if they are not present.

    Attributes:
        raw (Sequence[int]): The FRU inventory data.
        common_header (InventoryCommonHeader): The common header.
    """

    def __init__(self, data: Sequence[int] | None = None,
                 ignore_checksum: bool = False) -> None:
        """Decode the FRU inventory data.

        Args:
            data: The FRU inventory data. Nothing is decoded if it is None
                or empty, the areas are added by
                :meth:`Fru.get_fru_inventory` then.
            ignore_checksum: Don't raise a DecodingError on a wrong
                checksum.

        Raises:
            DecodingError: An area is invalid or its checksum is wrong.
        """
        #: The internal use area.
        self.internal_use_area: InventoryInternalUseArea | None = None
        #: The chassis info area.
        self.chassis_info_area: InventoryChassisInfoArea | None = None
        #: The board info area.
        self.board_info_area: InventoryBoardInfoArea | None = None
        #: The product info area.
        self.product_info_area: InventoryProductInfoArea | None = None
        #: The multirecord area.
        self.multirecord_area: InventoryMultiRecordArea | None = None

        if data:
            self._from_data(data, ignore_checksum=ignore_checksum)

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        self.raw = data
        self.common_header = InventoryCommonHeader(
            data[:8], ignore_checksum=ignore_checksum)

        offset = self.common_header.internal_use_area_offset
        if offset:
            end = self.common_header.next_area_offset(offset)
            self.internal_use_area = InventoryInternalUseArea(
                data[offset:end])

        if self.common_header.chassis_info_area_offset:
            self.chassis_info_area = InventoryChassisInfoArea(
                data[self.common_header.chassis_info_area_offset:],
                ignore_checksum=ignore_checksum)

        if self.common_header.board_info_area_offset:
            self.board_info_area = InventoryBoardInfoArea(
                data[self.common_header.board_info_area_offset:],
                ignore_checksum=ignore_checksum)

        if self.common_header.product_info_area_offset:
            self.product_info_area = InventoryProductInfoArea(
                data[self.common_header.product_info_area_offset:],
                ignore_checksum=ignore_checksum)

        offset = self.common_header.multirecord_area_offset
        if offset:
            end = self.common_header.next_area_offset(offset)
            self.multirecord_area = InventoryMultiRecordArea(
                data[offset:end], ignore_checksum=ignore_checksum)
