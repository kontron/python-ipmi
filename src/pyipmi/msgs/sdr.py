import array

import constants
from pyipmi.msgs import Message
from pyipmi.msgs import ByteArray
from pyipmi.msgs import UnsignedInt
from pyipmi.msgs import Timestamp
from pyipmi.msgs import Bitfield
from pyipmi.msgs import CompletionCode
from pyipmi.msgs import Conditional
from pyipmi.utils import push_unsigned_int, pop_unsigned_int
from pyipmi.errors import DecodingError, EncodingError

class GetSDRRepositoryInfo(Message):
    CMDID = constants.CMDID_GET_SDR_REPOSITORY_INFO
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('sdr_version', 1),
            UnsignedInt('record_count', 2),
            UnsignedInt('free_space', 2),
            Timestamp('most_recent_addtion'),
            Timestamp('most_recent_erase'),
            Bitfield('operation_support', 1,
                Bitfield.Bit('get_sdr_repository_allocation_command', 1),
                Bitfield.Bit('reverse_sdr_repository_command', 1),
                Bitfield.Bit('partial_add_sdr_command', 1),
                Bitfield.Bit('delete_sdr_command', 1),
                Bitfield.ReservedBit(1, 0),
                Bitfield.Bit('sdr_repository_update_type', 2),
                Bitfield.Bit('overflow_flag', 1)
            ),
    )


class GetDeviceSdrInfo(Message):
    CMDID = constants.CMDID_GET_DEVICE_SDR_INFO
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('number_of_sensors', 1),
            Bitfield('flags', 1,
                Bitfield.Bit('lun0_has_sensors', 1),
                Bitfield.Bit('lun1_has_sensors', 1),
                Bitfield.Bit('lun2_has_sensors', 1),
                Bitfield.Bit('lun3_has_sensors', 1),
                Bitfield.ReservedBit(3, 0),
                Bitfield.Bit('dynamic_population', 1)
            ),
            Timestamp('sensor_population_change'),
    )


class GetDeviceSdr(Message):
    CMDID = constants.CMDID_GET_DEVICE_SDR
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = (
            UnsignedInt('reservation_id', 2),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('length', 1),
    )
    _RSP_DESC = ()

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            push_unsigned_int(data, self.rsp.next_record_id, 2)
            data.extend(self.rsp.record_data)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array.array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.next_record_id = pop_unsigned_int(data, 2)
        self.rsp.record_data = data[:]

class ReserveDeviceSdrRepository(Message):
    CMDID = constants.CMDID_RESERVE_DEVICE_SDR_REPOSITORY
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = ()
    _RSP_DESC = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2)
    )


class GetSensorThreshold(Message):
    CMDID = constants.CMDID_GET_SENSOR_THRESHOLD
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = (
        UnsignedInt('sensor_number', 1),
    )
    _RSP_DESC = (
        CompletionCode(),
        Bitfield('readable_mask', 1,
                Bitfield.Bit('lnc', 1, default=0),
                Bitfield.Bit('lcr', 1, default=0),
                Bitfield.Bit('lnr', 1, default=0),
                Bitfield.Bit('unc', 1, default=0),
                Bitfield.Bit('ucr', 1, default=0),
                Bitfield.Bit('unr', 1, default=0),
                Bitfield.ReservedBit(2, 0),
            ),
        Bitfield('threshold', 6,
                Bitfield.Bit('lnc', 8, default=0),
                Bitfield.Bit('lcr', 8, default=0),
                Bitfield.Bit('lnr', 8, default=0),
                Bitfield.Bit('unc', 8, default=0),
                Bitfield.Bit('ucr', 8, default=0),
                Bitfield.Bit('unr', 8, default=0),
            ),
    )


class SetSensorThreshold(Message):
    CMDID = constants.CMDID_SET_SENSOR_THRESHOLD
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = (
        UnsignedInt('sensor_number', 1),
        Bitfield('set_mask', 1,
                Bitfield.Bit('lnc', 1, default=0),
                Bitfield.Bit('lcr', 1, default=0),
                Bitfield.Bit('lnr', 1, default=0),
                Bitfield.Bit('unc', 1, default=0),
                Bitfield.Bit('ucr', 1, default=0),
                Bitfield.Bit('unr', 1, default=0),
                Bitfield.ReservedBit(2, 0),
            ),
        Bitfield('threshold', 6,
                Bitfield.Bit('lnc', 8, default=0),
                Bitfield.Bit('lcr', 8, default=0),
                Bitfield.Bit('lnr', 8, default=0),
                Bitfield.Bit('unc', 8, default=0),
                Bitfield.Bit('ucr', 8, default=0),
                Bitfield.Bit('unr', 8, default=0),
            ),
    )
    _RSP_DESC = (
        CompletionCode(),
    )


class GetSensorReading(Message):
    CMDID = constants.CMDID_GET_SENSOR_READING
    NETFN = constants.NETFN_SENSOR_EVENT
    LUN = 0
    _REQ_DESC = (
        UnsignedInt('sensor_number', 1),
    )
    _RSP_DESC = ()

    def _encode_rsp(self):
        data = array.array('c')
        push_unsigned_int(data, self.rsp.completion_code, 1)
        if (self.rsp.completion_code == constants.CC_OK):
            push_unsigned_int(data, self.rsp.sensor_reading, 1)
            tmp = (self.rsp.event_disabled & 0x1 << 5
                    | self.rsp.scanning_disabled & 0x1 << 6
                    | self.rsp.update_in_progress & 0x1 << 7)
            push_unsigned_int(data, tmp, 1)
            if self.rsp.states1:
                push_unsigned_int(data, self.rsp.states1, 1)
            if self.rsp.states2:
                push_unsigned_int(data, self.rsp.states2, 1)
        return data.tostring()

    def _decode_rsp(self, data):
        data = array.array('c', data)
        self.rsp.completion_code = pop_unsigned_int(data, 1)
        if (self.rsp.completion_code != constants.CC_OK):
            return
        self.rsp.sensor_reading = pop_unsigned_int(data, 1)

        tmp = pop_unsigned_int(data, 1)
        self.rsp.event_disabled = (tmp & 0x80) >> 7
        self.rsp.scanning_disabled = (tmp & 0x40) >> 6
        self.rsp.update_in_progress = (tmp & 0x20) >> 5

        if len(data):
            self.rsp.states1 = pop_unsigned_int(data, 1)
        if len(data):
            self.rsp.states2 = pop_unsigned_int(data, 1)
