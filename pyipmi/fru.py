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
of a common header and the optional chassis info, board info, product info
and multirecord areas.

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
import os
from collections.abc import Sequence

from .errors import DecodingError, CompletionCodeError, RetryError, DataNotFound
from .helper import ReadLength
from .msgs import constants
from .utils import bcd_search, chunks, py3_array_tobytes
from .fields import FruTypeLengthString
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

        while True:
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
        DecodingError: An area is invalid or its checksum is wrong.
    """
    try:
        file = open(filename, "rb")
    except OSError:
        print('Error open file "%s"' % filename)

    ################################
    # get file size
    file_size = os.stat(filename).st_size
    file_data = file.read(file_size)
    data = array.array('B', file_data)
    file.close()
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
        CommonInfoArea._from_data(self, data)
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
        CommonInfoArea._from_data(self, data)
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
    """

    TYPE_POWER_SUPPLY_INFORMATION = 0
    TYPE_DC_OUTPUT = 1
    TYPE_DC_LOAD = 2
    TYPE_MANAGEMENT_ACCESS_RECORD = 3
    TYPE_BASE_COMPATIBILITY_RECORD = 4
    TYPE_EXTENDED_COMPATIBILITY_RECORD = 5
    TYPE_OEM = list(range(0x0c, 0x100))
    TYPE_OEM_PICMG = 0xc0

    def __str__(self) -> str:
        """Return the record type ID and the record data as hex string."""
        return '%02x: %s' % (self.record_type_id,
                             ' '.join('%02x' % b for b in self.raw))

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
        if (sum(self.raw) + data[3]) % 256 != 0 and ignore_checksum is False:
            raise DecodingError('FruDataMultiRecord record checksum failed')

    @staticmethod
    def create_from_record_id(data: Sequence[int]) -> FruDataMultiRecord:
        """Decode a record with the class for its record type.

        PICMG records are decoded by :class:`FruPicmgRecord`, the other
        records by :class:`FruDataUnknown`.

        Args:
            data: The data of the multirecord area, starting with the
                record.

        Returns:
            The decoded record.
        """
        if data[0] == FruDataMultiRecord.TYPE_OEM_PICMG:
            return FruPicmgRecord.create_from_record_id(data)
        else:
            return FruDataUnknown(data)


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

    def __init__(self, data: Sequence[int]) -> None:
        """Decode the PICMG record.

        Args:
            data: The data of the multirecord area, starting with the
                record.

        Raises:
            DecodingError: The data is too short or a checksum is wrong.
        """
        FruDataMultiRecord.__init__(self, data)

    @staticmethod
    def create_from_record_id(data: Sequence[int]) -> FruPicmgRecord:
        """Decode a PICMG record with the class for its PICMG record type.

        The Power Module Capability record is decoded by
        :class:`FruPicmgPowerModuleCapabilityRecord`, the other records by
        :class:`FruPicmgRecord`.

        Args:
            data: The data of the multirecord area, starting with the
                record.

        Returns:
            The decoded record.
        """
        picmg_record = FruPicmgRecord(data)
        if picmg_record.picmg_record_type_id ==\
                FruPicmgRecord.PICMG_RECORD_ID_MTCA_POWER_MODULE_CAPABILITY:
            return FruPicmgPowerModuleCapabilityRecord(data)

        return FruPicmgRecord(data)

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
        FruPicmgRecord._from_data(self, data)
        maximum_current_output = data[10] | data[11] << 8
        self.maximum_current_output = float(maximum_current_output/10)


class InventoryMultiRecordArea:
    """The multirecord area.

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
            self._from_data(data)

    def _from_data(self, data: Sequence[int], ignore_checksum: bool = False) -> None:
        self.records = list()
        offset = 0
        while True:
            record = FruDataMultiRecord.create_from_record_id(data[offset:])
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
        self.common_header = InventoryCommonHeader(data[:8])

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

        if self.common_header.multirecord_area_offset:
            self.multirecord_area = InventoryMultiRecordArea(
                data[self.common_header.multirecord_area_offset:],
                ignore_checksum=ignore_checksum)
