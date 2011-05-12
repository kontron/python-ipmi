#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#
import time

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.utils import check_completion_code, pop_unsigned_int
from pyipmi.event import Event
import pyipmi.msgs.sel

INITIATE_ERASE = 0xaa
GET_ERASE_STATUS = 0x00
ERASURE_IN_PROGRESS = 0x0
ERASURE_COMPLETED = 0x1

class Helper:
    def get_sel_reservation_id(self, fn):
        m = pyipmi.msgs.sel.ReserveSel()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        return m.rsp.reservation_id

    def clear_sel(self, fn, retry=5):
        m = pyipmi.msgs.sel.ClearSel()
        m.req.reservation_id = self.get_sel_reservation_id(fn)

        m.req.cmd = pyipmi.sel.INITIATE_ERASE
        while True:
            fn(m)
            if m.rsp.completion_code == pyipmi.msgs.constants.CC_RES_CANCELED:
                m.req.reservation_id = self.get_sel_reservation_id(fn)
                retry -= 1
                continue
            else:
                check_completion_code(m.rsp.completion_code)
                break

        m.req.cmd = pyipmi.sel.GET_ERASE_STATUS
        while True:
            if retry <= 0:
                raise pyipmi.errors.RetryError()

            fn(m)
            if m.rsp.completion_code == pyipmi.msgs.constants.CC_OK:
                if m.rsp.status.erase_in_progress == pyipmi.sel.ERASURE_IN_PROGRESS:
                    time.sleep(0.5)
                    retry -= 1
                    continue
                else:
                    break
            elif m.rsp.completion_code == pyipmi.msgs.constants.CC_RES_CANCELED:
                time.sleep(0.2)
                m.req.reservation_id = self.get_sel_reservation_id(fn)
                retry -= 1
                continue
            else:
                check_completion_code(m.rsp.completion_code)
                break

    def sel_entries(self, fn):
        '''Generator which returns all SEL entries.'''
        m = pyipmi.msgs.sel.GetSelInfo()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        if m.rsp.entries == 0:
            return
        reservation_id = self.get_sel_reservation_id(fn)
        next_record_id = 0
        while True:
            m = pyipmi.msgs.sel.GetSelEntry()
            m.req.reservation_id = reservation_id
            m.req.record_id = next_record_id
            m.req.offset = 0
            self.max_req_len = 0xff # read entire record

            record_data = []
            while True:
                m.req.length = self.max_req_len
                if (m.req.offset + m.req.length) > 16:
                    m.req.length = 16 - m.req.offset

                fn(m)
                if m.rsp.completion_code == 0xca:
                    if self.max_req_len  == 0xff:
                        self.max_req_len = 16
                    else:
                        self.max_req_len -= 1
                    continue
                else:
                    check_completion_code(m.rsp.completion_code)

                record_data += m.rsp.record_data
                m.req.offset = len(record_data)

                if len(record_data) >= 16:
                    break

            next_record_id = m.rsp.next_record_id

            yield SelEntry(record_data)
            if next_record_id == 0xffff:
                break

    def get_sel_entries(self, fn):
        '''Returns all SEL entries as a list.'''
        return list(self.sel_entries(fn))

class SelEntry:
    TYPE_SYSTEM_EVENT = 0x02
    TYPE_OEM_TIMESTAMPED_RANGE = range(0xc0, 0xe0)
    TYPE_OEM_NON_TIMESTAMPED_RANGE = range(0xe0, 0x100)

    def __init__(self, rsp=None):
        if rsp:
            self.from_response(rsp)

    def __str__(self):
        s = '[%s]' % (' '.join(['%02x' % ord(b) for b in self.data]))
        str = []
        str.append('SEL Record ID 0x%04x' % self.record_id)
        str.append('  Raw: %s' % s)
        str.append('  Type: %d' % self.type)
        str.append('  Timestamp: %d' % self.timestamp)
        str.append('  EvM rev: %d' % self.evm_rev)
        str.append('  Sensor Type: 0x%02x' % self.sensor_type)
        str.append('  Sensor Number: %d' % self.sensor_number)
        str.append('  Event Direction: %d' % self.event_direction)
        str.append('  Event Type: 0x%02x' % self.event_type)
        str.append('  Event Data: %s' % (self.event_data))
        return "\n".join(str)

    def type_to_string(self, type):
        s = None
        if type == SelEntry.TYPE_SYSTEM_EVENT:
            s = 'System Event'
        elif type in SelEntry.TYPE_OEM_TIMESTAMPED_RANGE:
            s = 'OEM timestamped (0x%02x)' % type
        elif type in SelEntry.TYPE_NON_OEM_TIMESTAMPED_RANGE:
            s = 'OEM non-timestamped (0x%02x)' % type
        return s

    def from_response(self, data):
        if len(data) != 16:
            raise DecodingError('Invalid SEL record length (%d)' % len(data))

        self.data = data

        # pop will change data, therefore copy it
        tmp_data = data[:]

        self.record_id = pop_unsigned_int(tmp_data, 2)
        self.type = pop_unsigned_int(tmp_data, 1)
        if (self.type != self.TYPE_SYSTEM_EVENT
                and self.type not in self.TYPE_OEM_TIMESTAMPED_RANGE
                and self.type not in self.TYPE_NON_OEM_TIMESTAMPED_RANGE):
            raise DecodingError('Unknown SEL type (0x%02x)' % self.type)
        self.timestamp = pop_unsigned_int(tmp_data, 4)
        self.generator_id = pop_unsigned_int(tmp_data, 2)
        self.evm_rev = pop_unsigned_int(tmp_data, 1)
        self.sensor_type = pop_unsigned_int(tmp_data, 1)
        self.sensor_number = pop_unsigned_int(tmp_data, 1)
        event_desc = pop_unsigned_int(tmp_data, 1)
        if event_desc & 0x80:
            self.event_direction = Event.DIR_DEASSERTION
        else:
            self.event_direction = Event.DIR_ASSERTION
        self.event_type = event_desc & 0x3f
        self.event_data = tmp_data[:]
