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

import math
import errors
import array
import time
from pyipmi.errors import DecodingError, CompletionCodeError, RetryError
from pyipmi.utils import check_completion_code, ByteBuffer
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import constants

from pyipmi.helper import get_sdr_data_helper, clear_repository_helper

SDR_TYPE_FULL_SENSOR_RECORD = 0x01
SDR_TYPE_COMPACT_SENSOR_RECORD = 0x02
SDR_TYPE_EVENT_ONLY_SENSOR_RECORD = 0x03
SDR_TYPE_ENTITY_ASSOCIATION_RECORD = 0x08
SDR_TYPE_FRU_DEVICE_LOCATOR_RECORD = 0x11
SDR_TYPE_MANAGEMENT_CONTROLLER_DEVICE_LOCATOR_RECORD = 0x12
SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD = 0x13
SDR_TYPE_BMC_MESSAGE_CHANNEL_INFO_RECORD = 0x14

GET_INITIALIZATION_AGENT_STATUS = 0
RUN_INITIALIZATION_AGENT = 1

class Sdr:
    def get_sdr_repository_info(self):
        req = create_request_by_name('GetSdrRepositoryInfo')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return SdrRepositoryInfo(rsp)

    def get_sdr_repository_allocation_info(self):
        req = create_request_by_name('GetSdrRepositoryAllocationInfo')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return SdrRepositoryAllocationInfo(rsp)

    def reserve_sdr_repository(self):
        req = create_request_by_name('ReserveSdrRepository')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.reservation_id

    def _get_sdr_chunk(self, reservation_id, record_id, offset, length):
        print length
        req = create_request_by_name('GetSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.bytes_to_read = length
        retry = 5

        while True:
            retry -= 1
            if retry == 0:
                raise RetryError()
            rsp = self.send_message(req)
            if rsp.completion_code == constants.CC_OK:
                break
            elif rsp.completion_code == constants.CC_RES_CANCELED:
                req.reservation_id = self.reserve_sdr_repository()
                time.sleep(0.1)
                continue
            elif rsp.completion_code == constants.CC_TIMEOUT:
                time.sleep(0.1)
                continue
            elif rsp.completion_code == constants.CC_RESP_COULD_NOT_BE_PRV:
                time.sleep(0.1 * retry)
                continue
            else:
                check_completion_code(rsp.completion_code)

        return (rsp.next_record_id, rsp.data)

    def get_repository_sdr(self, record_id, reservation_id=None):
        (next_id, record_data) = get_sdr_data_helper(
                self.reserve_sdr_repository, self._get_sdr_chunk,
                record_id, reservation_id)
        return create_sdr(record_data, next_id)

    def sdr_repository_entries(self):
        """A generator that returns the SDR list. Starting with ID=0x0000 and
        end when ID=0xffff is returned.
        """
        reservation_id = self.reserve_device_sdr_repository()
        record_id = 0

        while True:
            s = self.get_repository_sdr(record_id, reservation_id)
            yield s
            if s.next_id == 0xffff:
                break
            record_id = s.next_id

    def get_repository_sdr_list(self, reservation_id=None):
        """Returns the complete SDR list.
        """
        return list(self.sdr_repository_entries())

    def partial_add_sdr(self,
                reservation_id, record_id, offset, progress, data):

        req = create_request_by_name('PartialAddSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        req.offset = offset
        req.status.in_progress = progress
        req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.record_id

    def delete_sdr(self, record_id):
        """Deletes the sensor record specified by 'record_id'.
        """

        reservation_id = self.reserve_device_sdr_repository()
        req = create_request_by_name('DeleteSdr')
        req.reservation_id = reservation_id
        req.record_id = record_id
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.record_id

    def _clear_sdr_repository(self, cmd, reservation_id):
        req = create_request_by_name('ClearSdrRepository')
        req.reservation_id = reservation_id
        req.cmd = cmd
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.status.erase_in_progress

    def clear_sdr_repository(self, retry=5):
        clear_repository_helper(self.reserve_sdr_repository,
                self._clear_sdr_repository, retry)

    def _run_initialization_agent(self, cmd):
        req = create_request_by_name('RunInitializationAgent')
        req.cmd = cmd
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return rsp.status.initialization_completed

    def start_initialization_agent(self):
        self._run_initialization_agent(RUN_INITIALIZATION_AGENT)

    def get_initialization_agent_status(self):
        return self._run_initialization_agent(GET_INITIALIZATION_AGENT_STATUS)

class SdrRepositoryInfo:
    def __init__(self, rsp):
        if rsp:
            self.from_response(rsp)

    def from_response(self, rsp):
        self.sdr_version = rsp.sdr_version
        self.record_count = rsp.record_count
        self.free_space = rsp.free_space
        self.most_recent_addition = rsp.most_recent_addition
        self.support_get_allocation_info = rsp.support.get_allocation_info
        self.support_reserve = rsp.support.reserve
        self.support_partial_add = rsp.support.partial_add
        self.support_delete = rsp.support.delete
        self.support_update_type = rsp.support.update_type
        self.support_overflow_flag = rsp.support.overflow_flag

class SdrRepositoryAllocationInfo:
    def __init__(self, rsp):
        if rsp:
            self.from_response(rsp)

    def from_response(self, rsp):
        self.number_of_units = rsp.number_of_units
        self.unit_size = rsp.unit_size
        self.free_units = rsp.free_units
        self.largest_free_block = rsp.largest_free_block
        self.maximum_record_size = rsp.maximum_record_size


def create_sdr(data, next_id=None):
    sdr_type = data[3]

    if sdr_type == SDR_TYPE_FULL_SENSOR_RECORD:
        return SdrFullSensorRecord(data, next_id)
    elif sdr_type == SDR_TYPE_COMPACT_SENSOR_RECORD:
        return SdrCompactSensorRecord(data, next_id)
    elif sdr_type == SDR_TYPE_EVENT_ONLY_SENSOR_RECORD:
        return SdrEventOnlySensorRecord(data, next_id)
    elif sdr_type == SDR_TYPE_FRU_DEVICE_LOCATOR_RECORD:
        return SdrFruDeviceLocator(data, next_id)
    elif sdr_type == SDR_TYPE_MANAGEMENT_CONTROLLER_DEVICE_LOCATOR_RECORD:
        return SdrManagementContollerDeviceLocator(data, next_id)
    elif sdr_type == SDR_TYPE_MANAGEMENT_CONTROLLER_CONFIRMATION_RECORD:
        raise DecodingError('Unsupported SDR type(0x%02x)' % sdr_type)
    elif sdr_type == SDR_TYPE_BMC_MESSAGE_CHANNEL_INFO_RECORD:
        raise DecodingError('Unsupported SDR type(0x%02x)' % sdr_type)
    else:
        raise DecodingError('Unsupported SDR type(0x%02x)' % sdr_type)


class SdrCommon:
    def __init__(self, rsp=None, next_id=None):
        if rsp:
            self.from_response(rsp)
        if next_id:
            self.next_id = next_id

    def __str__(self):
        s = '["%-16s"] [%s]' % \
            (self.device_id_string, ' '.join(['%02x' % b for b in self.data]))
        return s

    def from_response(self, data):
        if len(data) < 5:
            raise DecodingError('Invalid SDR length (%d)' % len(data))

        self.data = data
        buffer = ByteBuffer(data[:])
        self.id = buffer.pop_unsigned_int(2)
        self.version = buffer.pop_unsigned_int(1)
        self.type = buffer.pop_unsigned_int(1)
        self.lenght = buffer.pop_unsigned_int(1)

###
# SDR type 0x01
##################################################
class SdrFullSensorRecord(SdrCommon):
    DATA_FMT_UNSIGNED = 0
    DATA_FMT_1S_COMPLEMENT = 1
    DATA_FMT_2S_COMPLEMENT = 2
    DATA_FMT_NONE = 3

    L_LINEAR = 0
    L_LN = 1
    L_LOG = 2
    L_LOG2 = 3
    L_E = 4
    L_EXP10 = 5
    L_EXP2 = 6
    L_1_X = 7
    L_SQR = 8
    L_CUBE = 9
    L_SQRT = 10
    L_CUBERT = 11

    def __init__(self, data, next_id=None):
        SdrCommon.__init__(self, data, next_id)
        if data:
            self.from_data(data)

    def convert_sensor_raw_to_value(self, raw):
        fmt = self.analog_data_format
        if (fmt == self.DATA_FMT_1S_COMPLEMENT):
            if raw & 0x80:
                raw = -((raw & 0x7f) ^ 0x7f)
        elif (fmt == self.DATA_FMT_2S_COMPLEMENT):
            if raw & 0x80:
                raw = -((raw & 0x7f) ^ 0x7f) - 1
        raw = float(raw)

        return self.l((self.m * raw + (self.b * 10**self.k1)) * 10**self.k2)

    def convert_sensor_value_to_raw(self, value):
        linearization = self.linearization & 0x7f

        if linearization is not self.L_LINEAR:
            raise NotImplementedError()

        raw = ((float(value) * 10**(-1 * self.k2)) / self.m) - (self.b * 10**self.k1)

        fmt = self.analog_data_format
        if (fmt == self.DATA_FMT_1S_COMPLEMENT):
            if value < 0:
                raise NotImplementedError()
        elif (fmt == self.DATA_FMT_2S_COMPLEMENT):
            if value < 0:
                raise NotImplementedError()

        raw = int(round(raw))
        if raw > 0xff:
            raise ValueError()

        return raw

    @property
    def l(self):
        linearization = self.linearization & 0x7f
        if linearization == self.L_LN:
            l = math.log
        elif linearization == self.L_LOG:
            l = lambda x: math.log(x, 10)
        elif linearization == self.L_LOG2:
            l = lambda x: math.log(x, 2)
        elif linearization == self.L_E:
            l = math.exp
        elif linearization == self.L_EXP10:
            l = lambda x: math.pow(10, x)
        elif linearization == self.L_EXP2:
            l = lambda x: math.pow(2, x)
        elif linearization == self.L_1_X:
            l = lambda x: 1.0 / x
        elif linearization == self.L_SQR:
            l = lambda x: math.pow(x, 2)
        elif linearization == self.L_CUBE:
            l = lambda x: math.pow(x, 3)
        elif linearization == self.L_SQRT:
            l = math.sqrt
        elif linearization == self.L_CUBERT:
            l = lambda x: math.pow(x, 1.0/3)
        elif linearization == self.L_LINEAR:
            l = lambda x: x
        else:
            raise errors.DecodingError('unknown linearization %d' %
                    linearization)
        return l

    def _convert_complement(self, value, size):
        if (value & (1 << (size-1))):
            value = -(1<<size) + value
        return value

    def from_data(self, data):
        buffer = ByteBuffer(data[5:])
        # record key bytes
        self.owner_id = buffer.pop_unsigned_int(1)
        self.owner_lun = buffer.pop_unsigned_int(1) & 0x3
        self.number = buffer.pop_unsigned_int(1)
        # record body bytes
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)

        # byte 11
        initialization = buffer.pop_unsigned_int(1)
        self.initialization = []
        if initialization & 0x40:
            self.initialization.append('scanning')
        if initialization & 0x20:
            self.initialization.append('events')
        if initialization & 0x10:
            self.initialization.append('thresholds')
        if initialization & 0x08:
            self.initialization.append('hysteresis')
        if initialization & 0x04:
            self.initialization.append('type')
        if initialization & 0x02:
            self.initialization.append('default_event_generation')
        if initialization & 0x01:
            self.initialization.append('default_scanning')

        # byte 12 - sensor capabilities
        capabilities = buffer.pop_unsigned_int(1)
        self.capabilities = []
        # ignore sensor
        if capabilities & 0x80:
            self.capabilities.append('ignore_sensor')
        # sensor auto re-arm support
        if capabilities & 0x40:
            self.capabilities.append('auto_rearm')
        # sensor hysteresis support
        HYSTERESIS_MASK = 0x30
        HYSTERESIS_IS_NOT_SUPPORTED = 0x00
        HYSTERESIS_IS_READABLE = 0x10
        HYSTERESIS_IS_READ_AND_SETTABLE = 0x20
        HYSTERESIS_IS_FIXED = 0x30
        if capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_NOT_SUPPORTED:
            self.capabilities.append('hysteresis_not_supported')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_READABLE:
            self.capabilities.append('hysteresis_readable')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_READ_AND_SETTABLE:
            self.capabilities.append('hysteresis_read_and_setable')
        elif capabilities & HYSTERESIS_MASK == HYSTERESIS_IS_FIXED:
            self.capabilities.append('hysteresis_fixed')
        # sensor threshold support
        THRESHOLD_MASK = 0x30
        THRESHOLD_IS_NOT_SUPPORTED = 0x00
        THRESHOLD_IS_READABLE = 0x10
        THRESHOLD_IS_READ_AND_SETTABLE = 0x20
        THRESHOLD_IS_FIXED = 0x30
        if capabilities & THRESHOLD_MASK == THRESHOLD_IS_NOT_SUPPORTED:
            self.capabilities.append('threshold_not_supported')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_READABLE:
            self.capabilities.append('threshold_readable')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_READ_AND_SETTABLE:
            self.capabilities.append('threshold_read_and_setable')
        elif capabilities & THRESHOLD_MASK == THRESHOLD_IS_FIXED:
            self.capabilities.append('threshold_fixed')
        # sensor event message control support
        if (capabilities & 0x03) is 0:
            pass
        if (capabilities & 0x03) is 1:
            pass
        if (capabilities & 0x03) is 2:
            pass
        if (capabilities & 0x03) is 3:
            pass

        self.sensor_type_code = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.assertion_mask = buffer.pop_unsigned_int(2)
        self.deassertion_mask = buffer.pop_unsigned_int(2)
        self.discrete_reading_mask = buffer.pop_unsigned_int(2)
        # byte 21, 22, 23
        units_1 = buffer.pop_unsigned_int(1)
        units_2 = buffer.pop_unsigned_int(1)
        units_3 = buffer.pop_unsigned_int(1)
        self.analog_data_format = (units_1 >> 6) & 0x3
        self.rate_unit = (units_1 >> 3) >> 0x7
        self.modifier_unit = (units_1 >> 1) & 0x2
        self.percentage = units_1 & 0x1
        # byte 24
        self.linearization = buffer.pop_unsigned_int(1) & 0x7f
        # byte 25, 26
        m = buffer.pop_unsigned_int(1)
        m_tol = buffer.pop_unsigned_int(1)
        self.m = (m & 0xff) | ((m_tol & 0xc0) << 2)
        self.tolerance = (m_tol & 0x3f)

        # byte 27, 28, 29
        b = buffer.pop_unsigned_int(1)
        b_acc = buffer.pop_unsigned_int(1)
        acc_accexp = buffer.pop_unsigned_int(1)
        self.b = (b & 0xff) | ((b_acc & 0xc0) << 2)
        self.b = self._convert_complement(self.b, 10)
        self.accuracy = (b_acc & 0x3f) | ((acc_accexp & 0xf0) << 4)
        self.accuracy_exp = (acc_accexp & 0x0c) >> 2
        # byte 30
        rexp_bexp = buffer.pop_unsigned_int(1)
        self.k2 = (rexp_bexp & 0xf0) >> 4
        # convert 2s complement
        #if self.k2 & 0x8: # 4bit
        #    self.k2 = -0x10 + self.k2
        self.k2 = self._convert_complement(self.k2, 4)

        self.k1 = rexp_bexp & 0x0f
        # convert 2s complement
        #if self.k1 & 0x8:
        #    self.k1 = -0x10 + self.k1
        self.k1 = self._convert_complement(self.k1, 4)

        # byte 31
        analog_characteristics = buffer.pop_unsigned_int(1)
        self.analog_characteristic = []
        if analog_characteristics & 0x01:
            self.analog_characteristic.append('nominal_reading')
        if analog_characteristics & 0x02:
            self.analog_characteristic.append('normal_max')
        if analog_characteristics & 0x04:
            self.analog_characteristic.append('normal_min')

        self.nominal_reading = buffer.pop_unsigned_int(1)
        self.normal_maximum = buffer.pop_unsigned_int(1)
        self.normal_minimum = buffer.pop_unsigned_int(1)
        self.sensor_maximum_reading = buffer.pop_unsigned_int(1)
        self.sensor_minimum_reading = buffer.pop_unsigned_int(1)
        self.threshold = {}
        self.threshold['unr'] = buffer.pop_unsigned_int(1)
        self.threshold['ucr'] = buffer.pop_unsigned_int(1)
        self.threshold['unc'] = buffer.pop_unsigned_int(1)
        self.threshold['lnr'] = buffer.pop_unsigned_int(1)
        self.threshold['lcr'] = buffer.pop_unsigned_int(1)
        self.threshold['lnc'] = buffer.pop_unsigned_int(1)
        self.hysteresis = {}
        self.hysteresis['positive_going'] = buffer.pop_unsigned_int(1)
        self.hysteresis['negative_going'] = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(2)
        self.oem = buffer.pop_unsigned_int(1)
        self.device_id_string_type_length = buffer.pop_unsigned_int(1)
        self.device_id_string = buffer.to_string()


###
# SDR type 0x02
##################################################
class SdrCompactSensorRecord(SdrCommon):
    def __init__(self, data, next_id=None):
        SdrCommon.__init__(self, data, next_id)
        if data:
            self.from_data(data)

    def from_data(self, data):
        buffer = ByteBuffer(data[5:])
        self.owner_id = buffer.pop_unsigned_int(1)
        self.owner_lun = buffer.pop_unsigned_int(1) & 0x3
        self.number = buffer.pop_unsigned_int(1)
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)
        self.sensor_initialization = buffer.pop_unsigned_int(1)
        self.capabilities = buffer.pop_unsigned_int(1)
        self.sensor_type = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.assertion_mask = buffer.pop_unsigned_int(2)
        self.deassertion_mask = buffer.pop_unsigned_int(2)
        self.discrete_reading_mask = buffer.pop_unsigned_int(2)
        self.units_1 = buffer.pop_unsigned_int(1)
        self.units_2 = buffer.pop_unsigned_int(1)
        self.units_3 = buffer.pop_unsigned_int(1)
        self.record_sharing = buffer.pop_unsigned_int(2)
        self.positive_going_hysteresis = buffer.pop_unsigned_int(1)
        self.negative_going_hysteresis = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(3)
        self.oem = buffer.pop_unsigned_int(1)
        self.device_id_string_type_length = buffer.pop_unsigned_int(1)
        self.device_id_string = buffer.to_string()


###
# SDR type 0x03
##################################################
class SdrEventOnlySensorRecord(SdrCommon):
    def __init__(self, data, next_id=None):
        SdrCommon.__init__(self, data, next_id)
        if data:
            self.from_data(data)

    def __str__(self):
        return 'Not supported yet.'

    def from_data(self, data):
        buffer = ByteBuffer(data[5:])
        self.owner_id = buffer.pop_unsigned_int(1)
        self.owner_lun = buffer.pop_unsigned_int(1) & 0x3
        self.number = buffer.pop_unsigned_int(1)
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)
        self.sensor_type = buffer.pop_unsigned_int(1)
        self.event_reading_type_code = buffer.pop_unsigned_int(1)
        self.record_sharing = buffer.pop_unsigned_int(2)
        self.reserved = buffer.pop_unsigned_int(1)
        self.oem = buffer.pop_unsigned_int(1)
        self.device_id_string_type_length = buffer.pop_unsigned_int(1)
        self.device_id_string = buffer.to_string()

###
# SDR type 0x11
##################################################
class SdrFruDeviceLocator(SdrCommon):
    def __init__(self, data, next_id=None):
        SdrCommon.__init__(self, data, next_id)
        if data:
            self.from_data(data)

    def from_data(self, data):
        buffer = ByteBuffer(data[5:])
        # record key bytes
        self.device_access_address = buffer.pop_unsigned_int(1) >> 1
        self.fru_device_id = buffer.pop_unsigned_int(1)
        self.logical_physical = buffer.pop_unsigned_int(1)
        self.channel_number = buffer.pop_unsigned_int(1)
        # record body bytes
        self.reserved = buffer.pop_unsigned_int(1)
        self.device_type = buffer.pop_unsigned_int(1)
        self.device_type_modifier= buffer.pop_unsigned_int(1)
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)
        self.oem = buffer.pop_unsigned_int(1)
        self.device_id_string_type_length = buffer.pop_unsigned_int(1)
        self.device_id_string = buffer.to_string()


###
# SDR type 0x12
##################################################
class SdrManagementContollerDeviceLocator(SdrCommon):
    def __init__(self, data, next_id=None):
        SdrCommon.__init__(self, data, next_id)
        if data:
            self.from_data(data)

    def from_data(self, data):
        buffer = ByteBuffer(data[5:])
        self.device_slave_address = buffer.pop_unsigned_int(1) >> 1
        self.channel_number = buffer.pop_unsigned_int(1) & 0xf
        self.power_state_notification = buffer.pop_unsigned_int(1)
        self.global_initialization = 0
        self.device_capabilities = buffer.pop_unsigned_int(1)
        self.reserved = buffer.pop_unsigned_int(3)
        self.entity_id = buffer.pop_unsigned_int(1)
        self.entity_instance = buffer.pop_unsigned_int(1)
        self.oem = buffer.pop_unsigned_int(1)
        self.device_id_string_type_length = buffer.pop_unsigned_int(1)
        self.device_id_string = buffer.to_string()
