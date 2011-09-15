import constants
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
class GetSDRRepositoryInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetSDRRepositoryInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_SDR_REPOSITORY_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
    __fields__ = (
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


@register_message_class
class GetDeviceSdrInfoReq(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class GetDeviceSdrInfoRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR_INFO
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
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
    __default_lun__ = 0
    __fields__ = (
            UnsignedInt('reservation_id', 2, 0x0000),
            UnsignedInt('record_id', 2),
            UnsignedInt('offset', 1),
            UnsignedInt('length', 1),
    )


@register_message_class
class GetDeviceSdrRsp(Message):
    __cmdid__ = constants.CMDID_GET_DEVICE_SDR
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            UnsignedInt('next_record_id', 2),
            RemainingBytes('record_data'),
    )


@register_message_class
class ReserveDeviceSdrRepositoryReq(Message):
    __cmdid__ = constants.CMDID_RESERVE_DEVICE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = ()


@register_message_class
class ReserveDeviceSdrRepositoryRsp(Message):
    __cmdid__ = constants.CMDID_RESERVE_DEVICE_SDR_REPOSITORY
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            UnsignedInt('reservation_id', 2)
    )


@register_message_class
class GetSensorThresholdsReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorThresholdsRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
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
    __default_lun__ = 0
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
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetSensorHysteresisReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = (
            UnsignedInt('sensor_number', 1),
            UnsignedInt('reserved', 1, 0xff),
    )


@register_message_class
class GetSensorHysteresisRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_HYSTERESIS
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
            UnsignedInt('positive_going_hysteresis', 1),
            UnsignedInt('negative_going_hysteresis', 1),
    )


@register_message_class
class SetSensorThresholdsReq(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_THRESHOLD
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
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
    __default_lun__ = 0
    __fields__ = (
        CompletionCode(),
    )


@register_message_class
class SetSensorEventEnableReq(Message):
    __cmdid__ = constants.CMDID_SET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
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
    __default_lun__ = 0
    __fields__ = (
            CompletionCode(),
    )


@register_message_class
class GetSensorEventEnableReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorEventEnableRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_EVENT_ENABLE
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
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
class GetSensorReadingReq(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_READING
    __netfn__ = constants.NETFN_SENSOR_EVENT
    __default_lun__ = 0
    __fields__ = (
        UnsignedInt('sensor_number', 1),
    )


@register_message_class
class GetSensorReadingRsp(Message):
    __cmdid__ = constants.CMDID_GET_SENSOR_READING
    __netfn__ = constants.NETFN_SENSOR_EVENT | 1
    __default_lun__ = 0
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
