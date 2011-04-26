#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.utils import check_completion_code, pop_unsigned_int
from pyipmi.event import Event
import pyipmi.msgs.sel

class Helper:
    def sel_entries(self, fn):
        '''Generator which returns all SEL entries.'''
        m = pyipmi.msgs.sel.ReserveSel()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        reservation_id = m.rsp.reservation_id
        next_record_id = 0
        while True:
            m = pyipmi.msgs.sel.GetSelEntry()
            m.req.reservation_id = reservation_id
            m.req.record_id = next_record_id
            m.req.offset = 0
            m.req.length = 0xff  # read entire record

            fn(m)
            check_completion_code(m.rsp.completion_code)
            next_record_id = m.rsp.next_record_id

            yield SelEntry(m.rsp.record_data)
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
        return s

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
        if (self.type != TYPE_SYSTEM_EVENT
                and self.type not in TYPE_OEM_TIMESTAMPED_RANGE
                and self.type not in TYPE_NON_OEM_TIMESTAMPED_RANGE):
            raise DecodingError('Unknown SEL type (0x%02x)' % self.type)
        self.timestamp = pop_unsigned_int(tmp_data, 4)
        self.generator_id = pop_unsigned_int(tmp_data, 2)
        self.evm_rev = pop_unsigned_int(tmp_data, 1)
        self.sensor_type = pop_unsigned_int(tmp_data, 1)
        self.sensor_number = pop_unsigned_int(tmp_data, 1)
        event_desc = pop_unsigned_int(tmp_data, 1)
        if event_desc & 0x80:
            self.event_direction = Event.DIR_ASSERTION
        else:
            self.event_direction = Event.DIR_DEASSERTION
        self.event_type = event_desc & 0x3f
        self.event_data = tmp_data[:]
