#!/usr/bin/env python

import pyipmi.msgs.vita

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_VitaGetVsoCapabilitiesReq_decode():
    m = pyipmi.msgs.vita.VitaGetVsoCapabilitiesReq()
    decode_message(m, b'\x03')
    assert m.vita_identifier == 3


def test_VitaGetVsoCapabilitiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetVsoCapabilitiesReq()
    data = encode_message(m)
    assert data[0] == 3


def test_VitaGetVsoCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetVsoCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x22\x11\xff\x02\x10\x20')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.ipmc_identifier.tier_functionality == 2
    assert m.ipmc_identifier.layer_functionality == 2
    assert m.ipmb_capabilities.number_ipmbs == 1
    assert m.ipmb_capabilities.max_frequency == 1
    assert m.vso_standard.standard == 3
    assert m.specification_revision == 2
    assert m.max_fru_id == 16
    assert m.ipmc_fru_device_id == 32


def test_VitaGetVsoCapabilitiesRsp_encode():
    m = pyipmi.msgs.vita.VitaGetVsoCapabilitiesRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x00\x00\x00'


def test_VitaGetChassisAddressTableInfoReq_decode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoReq()
    decode_message(m, b'\x03')
    assert m.vita_identifier == 3


def test_VitaGetChassisAddressTableInfoReq_encode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoReq()
    data = encode_message(m)
    assert data == b'\x03'


def test_VitaGetChassisAddressTableInfoReq_encode_address_key():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoReq()
    m.fru_id = 0
    m.address_key_type = m.ADDRESS_KEY_IPMB_ADDRESS
    m.address_key = 0x82
    assert encode_message(m) == b'\x03\x00\x01\x82'
    decode_message(m, b'\x03\x01')
    assert m.fru_id == 1
    assert m.address_key_type is None


def test_VitaGetChassisAddressTableInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoRsp()
    decode_message(m, b'\x00\x03\x41\x82\xff\x00\x01\x00')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.hardware_address == 0x41
    assert m.ipmb_0_address == 0x82
    assert m.fru_id == 0
    assert m.site_id == 1
    assert m.site_type == 0


def test_VitaGetChassisAddressTableInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoRsp()
    m.hardware_address = 0x10
    m.ipmb_0_address = 0x20
    m.fru_id = 1
    m.site_id = 1
    m.site_type = 3
    assert encode_message(m) == b'\x00\x03\x10\x20\xff\x01\x01\x03'


def test_VitaGetChassisManagerIpmbAddressRsp_decode():
    m = pyipmi.msgs.vita.VitaGetChassisManagerIpmbAddressRsp()
    decode_message(m, b'\x00\x03\x20\x00')
    assert m.active_address == 0x20
    assert m.backup_address == 0


def test_VitaGetChassisManagerIpAddressesReq_encode():
    m = pyipmi.msgs.vita.VitaGetChassisManagerIpAddressesReq()
    m.address_number = 0
    assert encode_message(m) == b'\x03\x00'


def test_VitaGetChassisManagerIpAddressesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetChassisManagerIpAddressesRsp()
    decode_message(m, b'\x00\x03\x10\x00\x00\x00\x01\x03\x01\x05'
                      b'\x80\x7f\x00\x00\x01\x02\x6f')
    assert m.last_change == 0x10
    assert m.address_count == 1
    assert m.site_type == 3
    assert m.site_number == 1
    assert m.max_unavailable_time == 5
    assert m.address_type == m.ADDRESS_TYPE_CHASSIS_MANAGER | \
        m.ADDRESS_TYPE_IPV4
    assert bytes(m.address) == b'\x7f\x00\x00\x01\x02\x6f'


def test_VitaGetFruAddressInfoReq_decode():
    m = pyipmi.msgs.vita.VitaGetFruAddressInfoReq()
    decode_message(m, b'\x03\x05')
    assert m.vita_identifier == 3
    assert m.fru_id == 5


def test_VitaGetFruAddressInfoReq_encode():
    m = pyipmi.msgs.vita.VitaGetFruAddressInfoReq()
    m.fru_id = 0x5
    data = encode_message(m)
    assert data == b'\x03\x05'


def test_VitaGetFruAddressInfoReq_without_fru_id():
    # the FRU device ID is optional, FRU 0 is meant without it
    m = pyipmi.msgs.vita.VitaGetFruAddressInfoReq()
    decode_message(m, b'\x03')
    assert m.fru_id is None
    assert encode_message(pyipmi.msgs.vita.VitaGetFruAddressInfoReq()) == \
        b'\x03'


def test_VitaGetFruAddressInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruAddressInfoRsp()
    decode_message(m, b'\x00\x03\x22\x33\x44\x55\x66\x77\x88')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaGetFruAddressInfoInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruAddressInfoRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x00\x00\x00'


def test_VitaGetChassisIdentifierReq_decode():
    m = pyipmi.msgs.vita.VitaGetChassisIdentifierReq()
    decode_message(m, b'\x03')
    assert m.vita_identifier == 3


def test_VitaGetChassisIdentifierInfoReq_encode():
    m = pyipmi.msgs.vita.VitaGetChassisIdentifierReq()
    data = encode_message(m)
    assert data == b'\x03'


def test_VitaGetChassisIdentifierInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaGetChassisIdentifierRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaGetChassisIdentifierInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaGetChassisIdentifierRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaSetChassisIdentifierReq_decode():
    m = pyipmi.msgs.vita.VitaSetChassisIdentifierReq()
    decode_message(m, b'\x03')
    assert m.vita_identifier == 3


def test_VitaSetChassisIdentifierInfoReq_encode():
    m = pyipmi.msgs.vita.VitaSetChassisIdentifierReq()
    data = encode_message(m)
    assert data == b'\x03'


def test_VitaSetChassisIdentifierInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaSetChassisIdentifierRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaSetChassisIdentifierInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaSetChassisIdentifierRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaFruControlReq_decode():
    m = pyipmi.msgs.vita.VitaFruControlReq()
    decode_message(m, b'\x03\x11\x22')
    assert m.vita_identifier == 3


def test_VitaFruControlInfoReq_encode():
    m = pyipmi.msgs.vita.VitaFruControlReq()
    data = encode_message(m)
    assert data == b'\x03\x00\x00'


def test_VitaFruControlInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaFruControlRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaFruControlInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaFruControlRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaGetFruLedPropertiesReq_decode():
    m = pyipmi.msgs.vita.VitaGetFruLedPropertiesReq()
    decode_message(m, b'\x03\x02')
    assert m.vita_identifier == 3
    assert m.fru_id == 2


def test_VitaGetFruLedPropertiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetFruLedPropertiesReq()
    m.fru_id = 2
    data = encode_message(m)
    assert data == b'\x03\x02'


def test_VitaGetFruLedPropertiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruLedPropertiesRsp()
    decode_message(m, b'\x00\x03\x00\x10')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.led_count == 16


def test_VitaGetFruLedPropertiesRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruLedPropertiesRsp()
    m.led_count = 16
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x10'


def test_VitaGetFruLedCapabilitiesReq_decode():
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesReq()
    decode_message(m, b'\x03\x02\x05')
    assert m.vita_identifier == 3
    assert m.fru_id == 2
    assert m.led_id == 5


def test_VitaGetFruLedCapabilitiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesReq()
    m.fru_id = 2
    m.led_id = 5
    data = encode_message(m)
    assert data == b'\x03\x02\x05'


def test_VitaGetFruLedCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x55\x02\x04')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.color_capabilities.blue == 0
    assert m.color_capabilities.red == 1
    assert m.color_capabilities.green == 0
    assert m.color_capabilities.amber == 1
    assert m.color_capabilities.orange == 0
    assert m.color_capabilities.white == 1
    assert m.default_color_local_control.value == 2
    assert m.default_color_override_control.value == 4
    assert m.flags is None

    # optional
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x55\x02\x04\x03')
    assert m.vita_identifier == 3
    assert m.flags == 3


def test_VitaGetFruLedCapabilitiesRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    m.color_capabilities.red = 1
    m.default_color_local_control.value = 2
    m.default_color_override_control.value = 4
    data = encode_message(m)
    assert data == b'\x00\x03\x04\x02\x04'

    # optional
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    m.flags = 4
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x04'


def test_VitaSetFruLedStateReq_decode():
    m = pyipmi.msgs.vita.VitaSetFruLedStateReq()
    decode_message(m, b'\x03\x02\x05\x01\x02\x03')
    assert m.vita_identifier == 3
    assert m.fru_id == 2
    assert m.led_id == 5
    assert m.function == 1
    assert m.on_duration == 2
    assert m.color == 3


def test_VitaSetFruLedStateReq_encode():
    m = pyipmi.msgs.vita.VitaSetFruLedStateReq()
    m.fru_id = 2
    m.led_id = 5
    data = encode_message(m)
    assert data == b'\x03\x02\x05\x00\x00\x00'


def test_VitaSetFruLedStateRsp_decode():
    m = pyipmi.msgs.vita.VitaSetFruLedStateRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaSetFruLedStateRsp_encode():
    m = pyipmi.msgs.vita.VitaSetFruLedStateRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaSetIpmbStateReq_decode():
    m = pyipmi.msgs.vita.VitaSetIpmbStateReq()
    decode_message(m, b'\x03\x0f\x0f\x00')
    assert m.vita_identifier == 3
    assert m.ipmb_a.state == 1
    assert m.ipmb_a.identification == 7
    assert m.ipmb_b.state == 1
    assert m.ipmb_b.identification == 7
    assert m.speed.ipmb_a == 0
    assert m.speed.ipmb_b == 0


def test_VitaSetIpmbStateReq_encode():
    m = pyipmi.msgs.vita.VitaSetIpmbStateReq()
    m.ipmb_a.state = 1
    m.ipmb_a.identification = 7
    m.ipmb_b.state = 1
    m.ipmb_b.identification = 7
    m.speed.ipmb_a = 1
    m.speed.ipmb_b = 1

    data = encode_message(m)
    assert data == b'\x03\x0f\x0f\x05'


def test_VitaSetIpmbStateRsp_decode():
    m = pyipmi.msgs.vita.VitaSetIpmbStateRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaSetIpmbStateRsp_encode():
    m = pyipmi.msgs.vita.VitaSetIpmbStateRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaSetFruStatePolicyReq_decode():
    m = pyipmi.msgs.vita.VitaSetFruStatePolicyReq()
    decode_message(m, b'\x03\x01\x00\x00')
    assert m.vita_identifier == 3


def test_VitaSetFruStatePolicyReq_encode():
    m = pyipmi.msgs.vita.VitaSetFruStatePolicyReq()
    data = encode_message(m)
    assert data == b'\x03\x00\x00\x00'


def test_VitaSetFruStatePolicyRsp_decode():
    m = pyipmi.msgs.vita.VitaSetFruStatePolicyRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaSetFruStatePolicyRsp_encode():
    m = pyipmi.msgs.vita.VitaSetFruStatePolicyRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaGetFruStatePolicyReq_decode():
    m = pyipmi.msgs.vita.VitaGetFruStatePolicyReq()
    decode_message(m, b'\x03\x00')
    assert m.vita_identifier == 3


def test_VitaGetFruStatePolicyReq_encode():
    m = pyipmi.msgs.vita.VitaGetFruStatePolicyReq()
    data = encode_message(m)
    assert data == b'\x03\x00'


def test_VitaGetFruStatePolicyRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruStatePolicyRsp()
    decode_message(m, b'\x03')
    assert m.vita_identifier == 3


def test_VitaGetFruStatePolicyRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruStatePolicyRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00'


def test_VitaSetFruActivationReq_decode():
    m = pyipmi.msgs.vita.VitaSetFruActivationReq()
    decode_message(m, b'\x03\x00\x00')
    assert m.vita_identifier == 3


def test_VitaGetFruActivationReq_encode():
    m = pyipmi.msgs.vita.VitaSetFruActivationReq()
    data = encode_message(m)
    assert data == b'\x03\x00\x00'


def test_VitaSetFruActivationRsp_decode():
    m = pyipmi.msgs.vita.VitaSetFruActivationRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaSetFruActivationRsp_encode():
    m = pyipmi.msgs.vita.VitaSetFruActivationRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'


def test_VitaFruControlCapabilitiesReq_decode():
    m = pyipmi.msgs.vita.VitaFruControlCapabilitiesReq()
    decode_message(m, b'\x03\x00')
    assert m.vita_identifier == 3


def test_VitaFruControlCapabilitiesReq_encode():
    m = pyipmi.msgs.vita.VitaFruControlCapabilitiesReq()
    data = encode_message(m)
    assert data == b'\x03\x00'


def test_VitaFruControlCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaFruControlCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x55')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.capabilities.cold_reset == 1
    assert m.capabilities.warm_reset == 0
    assert m.capabilities.graceful_reboot == 1
    assert m.capabilities.diagnostic_interrupt == 0
    assert m.capabilities.controlling_payload_power == 1


def test_VitaFruControlCapabilitiesRsp_encode():
    m = pyipmi.msgs.vita.VitaFruControlCapabilitiesRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00'


def test_VitaGetMandatorySensorNumbersReq_decode():
    m = pyipmi.msgs.vita.VitaGetMandatorySensorNumbersReq()
    decode_message(m, b'\x03\x00')
    assert m.vita_identifier == 3


def test_VitaGetMandatorySensorNumbersReq_encode():
    m = pyipmi.msgs.vita.VitaGetMandatorySensorNumbersReq()
    data = encode_message(m)
    assert data == b'\x03\x00'


def test_VitaGetMandatorySensorNumbersRsp_decode():
    m = pyipmi.msgs.vita.VitaGetMandatorySensorNumbersRsp()
    decode_message(m, b'\x00\x03\x00\x02\x03\x04\x05\x06\xff\x07')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.fru_state_sensor == 0
    assert m.fru_health_sensor == 2
    assert m.fru_voltage_sensor == 3
    assert m.fru_temperature_sensor == 4
    assert m.test_result_sensor == 5
    assert m.test_status_sensor == 6
    assert m.payload_mode_sensor == 7


def test_VitaGetMandatorySensorNumbersRsp_encode():
    m = pyipmi.msgs.vita.VitaGetMandatorySensorNumbersRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00'


def test_VitaGetFruHashReq_decode():
    m = pyipmi.msgs.vita.VitaGetFruHashReq()
    decode_message(m, b'\x03\x00')
    assert m.vita_identifier == 3


def test_VitaGetFruHashReq_encode():
    m = pyipmi.msgs.vita.VitaGetFruHashReq()
    data = encode_message(m)
    assert data == b'\x03\x00'


def test_VitaGetFruHashRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruHashRsp()
    decode_message(m, b'\x00\x03\x01\x02\x03\x04')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.fru_hash == 0x04030201


def test_VitaGetFruHashRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruHashRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x00'


def test_VitaGetPayloadModeCapabilitiesReq_decode():
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesReq()
    decode_message(m, b'\x03\x00')
    assert m.vita_identifier == 3


def test_VitaGetPayloadModeCapabilitiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesReq()
    data = encode_message(m)
    assert data == b'\x03\x00'


def test_VitaGetPayloadModeCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x55')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.supported_modes_lsb == 0x55
    assert m.supported_modes_msb is None

    # optional
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x12\x34')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.supported_modes_lsb == 0x12
    assert m.supported_modes_msb == 0x34


def test_VitaGetPayloadModeCapabilitiesRsp_encode():
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesRsp()
    data = encode_message(m)
    assert data == b'\x00\x03\x00'

    # optional
    m = pyipmi.msgs.vita.VitaGetPayloadModeCapabilitiesRsp()
    m.supported_modes_lsb = 1
    m.supported_modes_msb = 1
    data = encode_message(m)
    assert data == b'\x00\x03\x01\x01'


def test_VitaSetPayloadModeReq_decode():
    m = pyipmi.msgs.vita.VitaSetPayloadModeReq()
    decode_message(m, b'\x03\x00\x01')
    assert m.vita_identifier == 3
    assert m.mode == 1


def test_VitaSetPayloadModeReq_encode():
    m = pyipmi.msgs.vita.VitaSetPayloadModeReq()
    data = encode_message(m)
    assert data == b'\x03\x00\x00'


def test_VitaSetPayloadModeRsp_decode():
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.oem_response_3 is None

    # optional
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    decode_message(m, b'\x00\x03\xaa\x55')
    assert m.completion_code == 0
    assert m.vita_identifier == 3
    assert m.oem_response_3 == 0xaa
    assert m.oem_response_4 == 0x55


def test_VitaSetPayloadModeRsp_encode():
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'

    # optional
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    m.oem_response_3 = 1
    data = encode_message(m)
    assert data == b'\x00\x03\x01'


def test_decode_rsp_vita_get_chassis_identifier():
    # VSO identifier 0x03, then the identifier: 8-bit ASCII 'ABC'
    m = pyipmi.msgs.vita.VitaGetChassisIdentifierRsp()
    decode_message(m, b'\x00\x03\xc3ABC')
    assert m.completion_code == 0x00
    assert bytes(m.chassis_identifier) == b'\xc3ABC'


def test_encode_req_vita_set_chassis_identifier():
    m = pyipmi.msgs.vita.VitaSetChassisIdentifierReq()
    m.chassis_identifier = b'\xc3ABC'
    assert encode_message(m) == b'\x03\xc3ABC'


def test_VitaGetFanSpeedPropertiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetFanSpeedPropertiesReq()
    m.fru_id = 1
    assert encode_message(m) == b'\x03\x01'


def test_VitaGetFanSpeedPropertiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFanSpeedPropertiesRsp()
    decode_message(m, b'\x00\x03\x01\x0f\x08\x80')
    assert m.completion_code == 0
    assert m.minimum_speed_level == 1
    assert m.maximum_speed_level == 15
    assert m.normal_operation_level == 8
    assert m.properties.local_control_supported == 1


def test_VitaSetFanLevelReq_encode():
    m = pyipmi.msgs.vita.VitaSetFanLevelReq()
    m.fru_id = 0
    m.fan_level = 10
    assert encode_message(m) == b'\x03\x00\x0a'
    m.local_control_enable_state = 1
    assert encode_message(m) == b'\x03\x00\x0a\x01'


def test_VitaSetFanLevelReq_decode():
    m = pyipmi.msgs.vita.VitaSetFanLevelReq()
    decode_message(m, b'\x03\x00\xff')
    assert m.fan_level == 0xff
    assert m.local_control_enable_state is None


def test_VitaGetFanLevelRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFanLevelRsp()
    decode_message(m, b'\x00\x03\x0a')
    assert m.override_fan_level == 10
    assert m.local_control_fan_level is None
    decode_message(m, b'\x00\x03\xff\x08\x01')
    assert m.override_fan_level == 0xff
    assert m.local_control_fan_level == 8
    assert m.local_control_enable_state == 1


def test_VitaGetFanLevelRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFanLevelRsp()
    m.override_fan_level = 5
    assert encode_message(m) == b'\x00\x03\x05'
    m.local_control_fan_level = 8
    m.local_control_enable_state = 0
    assert encode_message(m) == b'\x00\x03\x05\x08\x00'


def test_VitaSetFanPolicyReq_encode():
    m = pyipmi.msgs.vita.VitaSetFanPolicyReq()
    m.fan_tray_site = 1
    m.enable = m.DISABLE
    m.timeout = 12
    assert encode_message(m) == b'\x03\x01\x00\x0c'
    m.site_number = 2
    m.site_type = 0
    assert encode_message(m) == b'\x03\x01\x00\x0c\x02\x00'


def test_VitaSetFanPolicyReq_decode_without_timeout():
    m = pyipmi.msgs.vita.VitaSetFanPolicyReq()
    decode_message(m, b'\x03\x01\x01')
    assert (m.fan_tray_site, m.enable, m.timeout) == (1, 1, None)


def test_VitaGetFanPolicyRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFanPolicyRsp()
    decode_message(m, b'\x00\x03\x01\x01')
    assert (m.policy, m.coverage) == (m.POLICY_ENABLED, 1)
    decode_message(m, b'\x00\x03\xff')
    assert (m.policy, m.coverage) == (m.POLICY_INDETERMINATE, None)


def test_VitaGetFanPolicyReq_encode():
    m = pyipmi.msgs.vita.VitaGetFanPolicyReq()
    m.fan_tray_site = 1
    assert encode_message(m) == b'\x03\x01'


def test_VitaFruInventoryDeviceLockControlReq_encode():
    m = pyipmi.msgs.vita.VitaFruInventoryDeviceLockControlReq()
    m.fru_id = 254
    m.operation = m.OPERATION_UNLOCK_COMMIT
    m.lock_id = 0x1234
    assert encode_message(m) == b'\x03\xfe\x03\x34\x12'


def test_VitaFruInventoryDeviceLockControlRsp_decode():
    m = pyipmi.msgs.vita.VitaFruInventoryDeviceLockControlRsp()
    decode_message(m, b'\x00\x03\x34\x12\x78\x56\x34\x12')
    assert (m.lock_id, m.last_commit) == (0x1234, 0x12345678)


def test_VitaFruInventoryDeviceWriteReq_encode():
    m = pyipmi.msgs.vita.VitaFruInventoryDeviceWriteReq()
    m.fru_id = 254
    m.lock_id = 0x1234
    m.offset = 8
    m.data = b'\x01\x02'
    assert encode_message(m) == b'\x03\xfe\x34\x12\x08\x00\x01\x02'


def test_VitaFruInventoryDeviceWriteRsp_decode():
    m = pyipmi.msgs.vita.VitaFruInventoryDeviceWriteRsp()
    decode_message(m, b'\x00\x03\x02')
    assert m.count_written == 2


def test_VitaGetIpmbLinkInfoReq_encode():
    m = pyipmi.msgs.vita.VitaGetIpmbLinkInfoReq()
    assert encode_message(m) == b'\x03\x00\x00'
    m.key_type = m.KEY_SENSOR_NUMBER
    m.key = 0x21
    assert encode_message(m) == b'\x03\x01\x21'


def test_VitaGetIpmbLinkInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaGetIpmbLinkInfoRsp()
    decode_message(m, b'\x00\x03\x05\x21')
    assert m.link_number == 5
    assert m.sensor_number == 0x21


def test_VitaGetFruPersistentControlRsp_decode():
    m = pyipmi.msgs.vita.VitaGetFruPersistentControlRsp()
    decode_message(m, b'\x00\x03\x02')
    assert m.state.cold_reset == 0
    assert m.state.warm_reset == 1


def test_VitaSetFruPersistentControlReq_encode():
    m = pyipmi.msgs.vita.VitaSetFruPersistentControlReq()
    m.fru_id = 1
    m.mask.cold_reset = 1
    m.state.cold_reset = 1
    assert encode_message(m) == b'\x03\x01\x01\x01'
    # with an empty mask the request changes nothing
    m.mask.cold_reset = 0
    assert encode_message(m) == b'\x03\x01\x00\x01'


def test_VitaFruPersistentControlCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaFruPersistentControlCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x03')
    assert m.capabilities.cold_reset == 1
    assert m.capabilities.warm_reset == 1


def test_VitaGetWriteProtectCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetWriteProtectCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x43\x84')
    assert m.destinations.embedded_nvm == 1
    assert m.destinations.local_nvm == 1
    assert m.destinations.remote_nvm == 0
    assert m.destinations.oem1 == 1
    assert m.categories.logs == 1
    assert m.categories.oem2 == 1
    assert m.categories.identification == 0


def test_VitaGetWriteProtectEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaGetWriteProtectEnablesReq()
    m.operation.by_destination = m.BY_DESTINATION
    m.operation.selector = m.DESTINATION_REMOTE_NVM
    assert encode_message(m) == b'\x03\x82'
    m.operation.by_destination = m.BY_CATEGORY
    m.operation.selector = m.OEM2
    assert encode_message(m) == b'\x03\x07'


def test_VitaGetWriteProtectEnablesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetWriteProtectEnablesRsp()
    decode_message(m, b'\x00\x03\x05')
    assert m.enables == 0x05


def test_VitaSetWriteProtectEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaSetWriteProtectEnablesReq()
    assert encode_message(m) == b'\x03\x00\x00\x00'
    m.operation.selector = m.CATEGORY_CONFIGURATION
    m.mask = 0x03
    m.enables = 0x01
    assert encode_message(m) == b'\x03\x01\x03\x01'


def test_VitaGetControlBitsCapabilitiesReq_encode():
    m = pyipmi.msgs.vita.VitaGetControlBitsCapabilitiesReq()
    assert encode_message(m) == b'\x03\x00'
    m.first_bank = 2
    m.number_of_banks = 3
    assert encode_message(m) == b'\x03\x02\x03'


def test_VitaGetControlBitsCapabilitiesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetControlBitsCapabilitiesRsp()
    decode_message(m, b'\x00\x03\x02\x0f\xf0\xff\x01\x02\x03')
    assert m.number_of_banks_supported == 2
    assert bytes(m.banks) == b'\x0f\xf0\xff\x01\x02\x03'


def test_VitaGetControlBitsReq_encode():
    m = pyipmi.msgs.vita.VitaGetControlBitsReq()
    m.first_bank = 1
    assert encode_message(m) == b'\x03\x01'


def test_VitaGetControlBitsRsp_decode():
    m = pyipmi.msgs.vita.VitaGetControlBitsRsp()
    decode_message(m, b'\x00\x03\x01\x02\x03')
    assert bytes(m.banks) == b'\x01\x02\x03'


def test_VitaSetControlBitsReq_encode():
    m = pyipmi.msgs.vita.VitaSetControlBitsReq()
    m.first_bank = 0
    m.banks = b'\x01\x01\x00'
    assert encode_message(m) == b'\x03\x00\x01\x01\x00'


def test_VitaSetControlBitsRsp_decode():
    m = pyipmi.msgs.vita.VitaSetControlBitsRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0


def test_VitaGetBridgedNetFnSupportReq_encode():
    m = pyipmi.msgs.vita.VitaGetBridgedNetFnSupportReq()
    m.net_function.code = 0x2c >> 1
    m.index = 1
    assert encode_message(m) == b'\x03\x2c\x01'


def test_VitaGetBridgedNetFnSupportRsp_decode():
    m = pyipmi.msgs.vita.VitaGetBridgedNetFnSupportRsp()
    decode_message(m, b'\x00\x03\x02\x00\x03')
    assert m.total_elements == 2
    assert bytes(m.elements) == b'\x00\x03'


def test_VitaGetBridgedCommandEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaGetBridgedCommandEnablesReq()
    m.channel.number = 0xe
    m.operation.net_function = 0x2c >> 1
    m.operation.operation = m.COMMANDS_80_FF
    m.group = b'\x03'
    assert encode_message(m) == b'\x03\x0e\x6c\x03'
    m.operation.operation = m.PASS_THROUGH
    m.operation.net_function = 0x06 >> 1
    m.group = b''
    assert encode_message(m) == b'\x03\x0e\x86'


def test_VitaGetBridgedCommandEnablesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetBridgedCommandEnablesRsp()
    decode_message(m, b'\x00\x03\x01\x80')
    assert bytes(m.enables) == b'\x01\x80'


def test_VitaSetBridgedCommandEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaSetBridgedCommandEnablesReq()
    m.channel.all_channels = 1
    m.operation.operation = m.PASS_THROUGH
    m.operation.net_function = 0x06 >> 1
    m.data = b'\xff\xff'
    assert encode_message(m) == b'\x03\x80\x86\xff\xff'


def test_VitaGetBridgedCommandSubFunctionEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaGetBridgedCommandSubFunctionEnablesReq()
    m.channel.number = 1
    m.net_function.code = 0x2c >> 1
    m.command = 0x09
    m.group = b'\x03'
    assert encode_message(m) == b'\x03\x01\x2c\x09\x03'


def test_VitaGetBridgedCommandSubFunctionEnablesRsp_decode():
    m = pyipmi.msgs.vita.VitaGetBridgedCommandSubFunctionEnablesRsp()
    decode_message(m, b'\x00\x03\x01\x00\x00\x80')
    assert m.enables == 0x80000001
    assert m.additional_enables is None
    decode_message(m, b'\x00\x03\x01\x00\x00\x00\x02\x00\x00\x00')
    assert m.additional_enables == 2


def test_VitaSetBridgedCommandSubFunctionEnablesReq_encode():
    m = pyipmi.msgs.vita.VitaSetBridgedCommandSubFunctionEnablesReq()
    m.net_function.code = 0x06 >> 1
    m.command = 0x24
    m.data = b'\x0f\x00\x00\x00'
    assert encode_message(m) == b'\x03\x00\x06\x24\x0f\x00\x00\x00'


def test_VitaSetBridgedNetFnPolicyReq_encode():
    m = pyipmi.msgs.vita.VitaSetBridgedNetFnPolicyReq()
    m.channel.number = 2
    m.policy.raw_messages = 1
    m.policy.oem_unknown_requests = 1
    assert encode_message(m) == b'\x03\x02\x05'


def test_VitaGetBridgedNetFnPolicyReq_encode():
    m = pyipmi.msgs.vita.VitaGetBridgedNetFnPolicyReq()
    m.channel.all_channels = 1
    assert encode_message(m) == b'\x03\x80'


def test_VitaGetBridgedNetFnPolicyRsp_decode():
    m = pyipmi.msgs.vita.VitaGetBridgedNetFnPolicyRsp()
    decode_message(m, b'\x00\x03\x01\x02')
    assert bytes(m.policies) == b'\x01\x02'
