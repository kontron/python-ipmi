#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


def test_VitaGetChassisAddressTableInfoRsp_decode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoRsp()
    decode_message(m, b'\x00\x03')
    assert m.completion_code == 0
    assert m.vita_identifier == 3


def test_VitaGetChassisAddressTableInfoRsp_encode():
    m = pyipmi.msgs.vita.VitaGetChassisAddressTableInfoReq()
    data = encode_message(m)
    assert data == b'\x03'


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
    decode_message(m, b'\x00\x03\x00\x55\x02\x04')
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
    decode_message(m, b'\x00\x03\x00\x55\x02\x04\x03')
    assert m.vita_identifier == 3
    assert m.flags == 3


def test_VitaGetFruLedCapabilitiesRsp_encode():
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    m.color_capabilities.red = 1
    m.default_color_local_control.value = 2
    m.default_color_override_control.value = 4
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x04\x02\x04'

    # optional
    m = pyipmi.msgs.vita.VitaGetFruLedCapabilitiesRsp()
    m.flags = 4
    data = encode_message(m)
    assert data == b'\x00\x03\x00\x00\x00\x00\x04'


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
    assert m.oem_response_3  == 0xaa
    assert m.oem_response_4  == 0x55


def test_VitaSetPayloadModeRsp_encode():
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    data = encode_message(m)
    assert data == b'\x00\x03'

    # optional
    m = pyipmi.msgs.vita.VitaSetPayloadModeRsp()
    m.oem_response_3 = 1
    data = encode_message(m)
    assert data == b'\x00\x03\x01'

