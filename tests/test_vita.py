#!/usr/bin/env python

import pytest

import pyipmi
import pyipmi.ipmitool
from pyipmi.errors import CompletionCodeError
from pyipmi.interfaces.base import Interface
from pyipmi.msgs import constants
from pyipmi.vita import (VITA_LED_COLOR_GREEN, VITA_LED_FUNCTION_ON,
                         VITA_POLICY_ACTIVATION_LOCKED,
                         VITA_POLICY_DEACTIVATION_LOCKED)

# raw responses (completion code and data) by command id
RESPONSES = {
    # tier 2, layer 2, 2 IPMBs at 400 kHz, VITA 46.11 revision 1.0
    constants.CMDID_VITA_GET_VSO_CAPABILITIES:
        b'\x00\x03\x11\x11\x00\x01\x03\x00',
    constants.CMDID_VITA_GET_FRU_ADDRESS_INFO:
        b'\x00\x03\x41\x82\xff\x00\x01\x00\x00\x84',
    constants.CMDID_VITA_GET_FRU_LED_PROPERTIES: b'\x00\x03\x0f\x02',
    # blue, red, green; default local green, override red; HW restrict
    constants.CMDID_VITA_GET_LED_COLOR_CAPABILITIES:
        b'\x00\x03\x0e\x03\x02\x02',
    # local control (on, green) and override (off, red)
    constants.CMDID_VITA_GET_FRU_LED_STATE:
        b'\x00\x03\x03\xff\x00\x03\x00\x00\x02',
    constants.CMDID_VITA_GET_FRU_STATE_POLICY_BITS: b'\x00\x03\x05',
}


class VitaStub(Interface):
    """Records the requests and answers with RESPONSES."""

    NAME = 'vitastub'

    def __init__(self):
        self.requests = []
        self.completion_code = 0

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        assert netfn == constants.NETFN_GROUP_EXTENSION
        self.requests.append(raw_bytes)
        if self.completion_code:
            return bytes((self.completion_code,))
        return RESPONSES.get(raw_bytes[0], b'\x00\x03')


@pytest.fixture
def ipmi():
    ipmi = pyipmi.create_connection(VitaStub())
    ipmi.target = pyipmi.Target(0x82)
    return ipmi


def last_request(ipmi):
    return ipmi.interface.requests[-1]


def test_get_vso_capabilities(ipmi):
    rsp = ipmi.get_vita_vso_capabilities()
    assert last_request(ipmi) == b'\x00\x03'
    assert rsp.ipmc_identifier.tier_functionality == 1
    assert rsp.ipmb_capabilities.number_ipmbs == 1
    assert rsp.specification_revision == 1
    assert rsp.max_fru_id == 3


def test_get_fru_address_info(ipmi):
    rsp = ipmi.get_vita_fru_address_info(2)
    assert last_request(ipmi) == b'\x40\x03\x02'
    assert rsp.hardware_address == 0x41
    assert rsp.ipmb_0_address == 0x82
    assert rsp.address_on_channel_7 == 0x84


def test_fru_control(ipmi):
    ipmi.vita_fru_control(1, pyipmi.vita.VITA_FRU_CONTROL_WARM_RESET)
    assert last_request(ipmi) == b'\x04\x03\x01\x01'


def test_fru_activation(ipmi):
    ipmi.set_vita_fru_activation(1)
    assert last_request(ipmi) == b'\x0c\x03\x01\x01'
    ipmi.set_vita_fru_deactivation(1)
    assert last_request(ipmi) == b'\x0c\x03\x01\x00'


def test_fru_state_policy(ipmi):
    rsp = ipmi.get_vita_fru_state_policy(1)
    assert last_request(ipmi) == b'\x0b\x03\x01'
    assert rsp.activation_policies.activation_lock == 1
    assert rsp.activation_policies.commanded_deactivation_ignored == 1

    ipmi.set_vita_fru_state_policy(
        1, VITA_POLICY_ACTIVATION_LOCKED | VITA_POLICY_DEACTIVATION_LOCKED,
        VITA_POLICY_ACTIVATION_LOCKED)
    assert last_request(ipmi) == b'\x0a\x03\x01\x03\x01'


def test_led(ipmi):
    rsp = ipmi.get_vita_led_properties(0)
    assert last_request(ipmi) == b'\x05\x03\x00'
    assert rsp.led_count == 2

    rsp = ipmi.get_vita_led_color_capabilities(0, 1)
    assert last_request(ipmi) == b'\x06\x03\x00\x01'
    assert rsp.color_capabilities.green == 1
    assert rsp.flags == 2

    rsp = ipmi.get_vita_led_state(0, 1)
    assert last_request(ipmi) == b'\x08\x03\x00\x01'
    assert rsp.state.override == 1
    assert rsp.override_color == 2

    ipmi.set_vita_led_state(0, 1, VITA_LED_FUNCTION_ON, 0,
                            VITA_LED_COLOR_GREEN)
    assert last_request(ipmi) == b'\x07\x03\x00\x01\xff\x00\x03'


def test_completion_code_error(ipmi):
    ipmi.interface.completion_code = constants.CC_INV_CMD
    with pytest.raises(CompletionCodeError):
        ipmi.get_vita_vso_capabilities()


def run_cli(ipmi, command, capsys):
    args = pyipmi.ipmitool.build_parser().parse_args(command.split())
    args.func(ipmi, args)
    return capsys.readouterr().out


def test_cli_properties(ipmi, capsys):
    out = run_cli(ipmi, 'vita properties', capsys)
    assert 'Tier  2' in out
    assert 'Layer 2' in out
    assert 'Frequency  400kHz' in out
    assert '2 IPMB interfaces supported' in out
    assert 'VSO Standard      : VITA 46.11' in out
    assert 'VSO Spec Revision : 1.0' in out


def test_cli_addrinfo(ipmi, capsys):
    out = run_cli(ipmi, 'vita addrinfo', capsys)
    assert last_request(ipmi) == b'\x40\x03\x00'
    assert 'IPMB-0 Address   : 0x82' in out
    assert 'Site Type        : Front Loading VPX Plug-In Module' in out
    assert 'Channel 7 Address: 0x84' in out

    run_cli(ipmi, 'vita addrinfo 0x02', capsys)
    assert last_request(ipmi) == b'\x40\x03\x02'


def test_cli_set_commands(ipmi, capsys):
    assert 'ok' in run_cli(ipmi, 'vita frucontrol 1 0', capsys)
    assert last_request(ipmi) == b'\x04\x03\x01\x00'
    assert 'activated' in run_cli(ipmi, 'vita activate 1', capsys)
    assert 'deactivated' in run_cli(ipmi, 'vita deactivate 1', capsys)
    run_cli(ipmi, 'vita policy set 1 0x0f 0x08', capsys)
    assert last_request(ipmi) == b'\x0a\x03\x01\x0f\x08'
    run_cli(ipmi, 'vita led set 0 1 255 0 3', capsys)
    assert last_request(ipmi) == b'\x07\x03\x00\x01\xff\x00\x03'


def test_cli_policy_get(ipmi, capsys):
    out = run_cli(ipmi, 'vita policy get 1', capsys)
    assert 'FRU State Policy Bits:\t5h' in out
    assert 'Commanded-Deactivation-Ignored Policy Bit is 1' in out
    assert 'Activation-Locked Policy Bit is 1' in out


def test_cli_led(ipmi, capsys):
    assert 'LED Count:' in run_cli(ipmi, 'vita led prop 0', capsys)

    out = run_cli(ipmi, 'vita led cap 0 1', capsys)
    assert 'LED Color Capabilities: BLUE, RED, GREEN' in out
    assert 'LOCAL control:  GREEN' in out
    assert 'OVERRIDE state: RED' in out
    assert '[HW RESTRICT]' in out

    out = run_cli(ipmi, 'vita led get 0 1', capsys)
    assert '[LOCAL CONTROL] [OVERRIDE]' in out
    assert 'Local Control function:     ff\t[ON]' in out
    assert 'Override function:     0\t[OFF]' in out
    assert 'Override Color:        2\t[RED]' in out


def test_cli_missing_argument(ipmi, capsys):
    with pytest.raises(SystemExit):
        run_cli(ipmi, 'vita led get 0', capsys)
    err = capsys.readouterr().err
    assert 'usage: pyipmi vita led get' in err
    assert 'required: led_id' in err
