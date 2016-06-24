from __future__ import absolute_import
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

from . import constants
from . import register_message_class
from . import Message
from . import ByteArray
from . import UnsignedInt
from . import Timestamp
from . import Bitfield
from . import CompletionCode
from . import Conditional
from . import Optional
from . import RemainingBytes


@register_message_class
class GetDeviceSdrInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT


@register_message_class
class GetDeviceSdrInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
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
            Optional(
                Timestamp('sensor_population_change')
            ),
    )


@register_message_class
class GetDeviceSdrReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
            UnsignedInt('reservation_id', 2, 0x0000),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('bytes_to_read', 1),
    )


@register_message_class
class GetDeviceSdrRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('next_record_id', 2),
            RemainingBytes('record_data'),
    )


@register_message_class
class ReserveDeviceSdrRepositoryReq(Message):
    __cmdid__ = constants.CMDID_RESERVE_DEVICE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_SENSOR_EVENT


@register_message_class
class ReserveDeviceSdrRepositoryRsp(Message):
    __cmdid__ = constants.CMDID_RESERVE_DEVICE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2)
    )


@register_message_class
class GetSensorThresholdsReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorThresholdsRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
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


@register_message_class
class SetSensorHysteresisReq(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
            UnsignedInt('sensor_number', 1),
            UnsignedInt('reserved', 1, 0xff),
            UnsignedInt('positive_going_hysteresis', 1),
            UnsignedInt('negative_going_hysteresis', 1),
    )


@register_message_class
class SetSensorHysteresisRsp(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetSensorHysteresisReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
            UnsignedInt('sensor_number', 1),
            UnsignedInt('reserved', 1, 0xff),
    )


@register_message_class
class GetSensorHysteresisRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('positive_going_hysteresis', 1),
            UnsignedInt('negative_going_hysteresis', 1),
    )


@register_message_class
class SetSensorThresholdsReq(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
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


@register_message_class
class SetSensorThresholdsRsp(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetSensorEventEnableReq(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
            UnsignedInt('sensor_number', 1),
            Bitfield('enable', 1,
                Bitfield.ReservedBit(4, 0),
                Bitfield.Bit('config', 2, 0),
                Bitfield.Bit('sensor_scanning', 1, 0),
                Bitfield.Bit('event_message', 1, 0),
            ),
            Optional(UnsignedInt('byte3', 1)),
            Optional(UnsignedInt('byte4', 1)),
            Optional(UnsignedInt('byte5', 1)),
            Optional(UnsignedInt('byte6', 1)),
    )

@register_message_class
class SetSensorEventEnableRsp(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetSensorEventEnableReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorEventEnableRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
            Bitfield('enabled', 1,
                Bitfield.ReservedBit(6, 0),
                Bitfield.Bit('sensor_scanning', 1, 0),
                Bitfield.Bit('event_message', 1, 0),
            ),
            Optional(UnsignedInt('byte3', 1)),
            Optional(UnsignedInt('byte4', 1)),
            Optional(UnsignedInt('byte5', 1)),
            Optional(UnsignedInt('byte6', 1)),
    )


@register_message_class
class RearmSensorEventsReq(Message):
    __cmdid__ = constants.CMDID_RE_ARM_SENSOR
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
        UnsignedInt('sensor_number', 1),
        Bitfield('re_arm', 1,
                Bitfield.ReservedBit(7, 0),
                Bitfield.Bit('all_event_status', 1, 0),
            ),
        UnsignedInt('re_arm_assertion_event', 2, 0),
        UnsignedInt('re_arm_deassertion_event', 2, 0),
    )


@register_message_class
class RearmSensorEventsRsp(Message):
    __cmdid__ = constants.CMDID_RE_ARM_SENSOR
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class GetSensorReadingReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_READING
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorReadingRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_READING
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __fields__ = (
            CompletionCode(),
            UnsignedInt('sensor_reading', 1),
            Bitfield('config', 1,
                Bitfield.ReservedBit(5, 0),
                Bitfield.Bit('initial_update_in_progress', 1, 0),
                Bitfield.Bit('sensor_scanning_disabled', 1, 0),
                Bitfield.Bit('event_message_disabled', 1, 0),
            ),
            #Alias('update_in_progress', 'stats.update_in_progress'),
            #Alias('scanning_disabled', 'stats.scanning_disabled'),
            #Alias('event_disabled', 'stats.event_disabled'),
            Optional(UnsignedInt('states1', 1)),
            Optional(UnsignedInt('states2', 1)),
    )
