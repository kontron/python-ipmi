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

import time

from pyipmi.errors import DecodingError, CompletionCodeError, RetryError
from pyipmi.utils import check_completion_code, ByteBuffer
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import constants
from pyipmi.event import EVENT_ASSERTION, EVENT_DEASSERTION

from pyipmi.helper import clear_repository_helper


class Sel:
    def get_sel_entries_count(self):
        req = create_request_by_name('GetSelInfo')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.entries

    def get_sel_reservation_id(self):
        req = create_request_by_name('ReserveSel')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.reservation_id

    def _clear_sel(self, cmd, reservation):
        req = create_request_by_name('ClearSel')
        req.reservation_id = reservation
        req.cmd = cmd
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.status.erase_in_progress

    def clear_sel(self, retry=5):
        clear_repository_helper(self.get_sel_reservation_id,
                self._clear_sel, retry)

    def sel_entries(self):
        """Generator which returns all SEL entries."""
        req = create_request_by_name('GetSelInfo')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        if rsp.entries == 0:
            return
        reservation_id = self.get_sel_reservation_id()
        next_record_id = 0
        while True:
            req = create_request_by_name('GetSelEntry')
            req.reservation_id = reservation_id
            req.record_id = next_record_id
            req.offset = 0
            self.max_req_len = 0xff # read entire record

            record_data = ByteBuffer()
            while True:
                req.length = self.max_req_len
                if (self.max_req_len != 0xff
                        and (req.offset + req.length) > 16):
                    req.length = 16 - req.offset

                rsp = self.send_message(req)
                if rsp.completion_code == constants.CC_CANT_RET_NUM_REQ_BYTES:
                    if self.max_req_len  == 0xff:
                        self.max_req_len = 16
                    else:
                        self.max_req_len -= 1
                    continue
                else:
                    check_completion_code(rsp.completion_code)

                record_data.append_array(rsp.record_data)
                req.offset = len(record_data)

                if len(record_data) >= 16:
                    break

            next_record_id = rsp.next_record_id

            yield SelEntry(record_data)
            if next_record_id == 0xffff:
                break

    def get_sel_entries(self):
        '''Returns all SEL entries as a list.'''
        return list(self.sel_entries())

class SelEntry:
    TYPE_SYSTEM_EVENT = 0x02
    TYPE_OEM_TIMESTAMPED_RANGE = range(0xc0, 0xe0)
    TYPE_OEM_NON_TIMESTAMPED_RANGE = range(0xe0, 0x100)

    def __init__(self, rsp=None):
        if rsp:
            self.from_response(rsp)

    def __str__(self):
        s = '[%s]' % (' '.join(['%02x' % b for b in self.data]))
        str = []
        str.append('SEL Record ID 0x%04x' % self.record_id)
        str.append('  Raw: %s' % s)
        str.append('  Type: %d' % self.type)
        str.append('  Timestamp: %d' % self.timestamp)
        str.append('  Generator: %d' % self.generator_id)
        str.append('  EvM rev: %d' % self.evm_rev)
        str.append('  Sensor Type: 0x%02x' % self.sensor_type)
        str.append('  Sensor Number: %d' % self.sensor_number)
        str.append('  Event Direction: %d' % self.event_direction)
        str.append('  Event Type: 0x%02x' % self.event_type)
        str.append('  Event Data: 0x%s' % self.event_data.encode('hex'))
        return "\n".join(str)

    def type_to_string(self, type):
        s = None
        if type == SelEntry.TYPE_SYSTEM_EVENT:
            s = 'System Event'
        elif type in SelEntry.TYPE_OEM_TIMESTAMPED_RANGE:
            s = 'OEM timestamped (0x%02x)' % type
        elif type in SelEntry.TYPE_OEM_NON_TIMESTAMPED_RANGE:
            s = 'OEM non-timestamped (0x%02x)' % type
        return s

    def from_response(self, data):
        if len(data) != 16:
            raise DecodingError('Invalid SEL record length (%d)' % len(data))

        self.data = data

        # pop will change data, therefore copy it
        buffer = ByteBuffer(data)

        self.record_id = buffer.pop_unsigned_int(2)
        self.type = buffer.pop_unsigned_int(1)
        if (self.type != self.TYPE_SYSTEM_EVENT
                and self.type not in self.TYPE_OEM_TIMESTAMPED_RANGE
                and self.type not in self.TYPE_OEM_NON_TIMESTAMPED_RANGE):
            raise DecodingError('Unknown SEL type (0x%02x)' % self.type)
        self.timestamp = buffer.pop_unsigned_int(4)
        self.generator_id = buffer.pop_unsigned_int(2)
        self.evm_rev = buffer.pop_unsigned_int(1)
        self.sensor_type = buffer.pop_unsigned_int(1)
        self.sensor_number = buffer.pop_unsigned_int(1)
        event_desc = buffer.pop_unsigned_int(1)
        if event_desc & 0x80:
            self.event_direction = EVENT_DEASSERTION
        else:
            self.event_direction = EVENT_ASSERTION
        self.event_type = event_desc & 0x3f
        self.event_data = buffer.pop_string(3)
