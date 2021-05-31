import argparse
import os
import random
import socket
import yaml

from array import array

import pyipmi

from pyipmi.interfaces import rmcp
from pyipmi.interfaces import ipmb
from pyipmi.msgs import (create_message, decode_message, encode_message,
                         create_response_message, create_request_by_name)
from pyipmi.msgs.constants import (NETFN_GROUP_EXTENSION,
                                   CC_INV_CMD,
                                   REPOSITORY_ERASURE_COMPLETED,
                                   REPOSITORY_ERASURE_IN_PROGRESS,
                                   REPOSITORY_INITIATE_ERASE,
                                   REPOSITORY_GET_ERASE_STATUS)
from pyipmi.session import Session
from pyipmi.utils import ByteBuffer

UDP_IP = "127.0.0.1"
UDP_PORT = 1623

session = Session()

handler_registry = {}


def register_message_handler(msg_name):
    def reg(fn):
        msg_type = type(create_request_by_name(msg_name))
        handler_registry[msg_type] = fn
        return fn
    return reg


@register_message_handler("GetChannelAuthenticationCapabilities")
def handle_channel_auth_caps(config, req):
    rsp = create_response_message(req)
    rsp.support.straight = 1
    rsp.status.anonymous_login_enabled = 1
    return rsp


@register_message_handler("GetSessionChallenge")
def handle_get_session_challenge(config, req):
    rsp = create_response_message(req)
    rsp.temporary_session_id = random.randrange(1, 0xffffffff)
    return rsp


@register_message_handler("ActivateSession")
def handle_activate_session(config, req):
    rsp = create_response_message(req)
    rsp.session_id = random.randrange(1, 0xffffffff)
    rsp.authentication.type = req.authentication.type
    rsp.privilege_level.maximum_allowed = req.privilege_level.maximum_requested
    session.session_id = rsp.session_id
    session.set_auth_type_user('admin', 'admin')
    session.auth_type = Session.AUTH_TYPE_PASSWORD
    return rsp


@register_message_handler("CloseSession")
def handle_close_session(config, req):
    rsp = create_response_message(req)
    return rsp


@register_message_handler("SetSessionPrivilegeLevel")
def handle_set_session_priv_level(config, req):
    rsp = create_response_message(req)
    return rsp


@register_message_handler("GetDeviceId")
def handle_get_device_id(config, req):
    rsp = create_response_message(req)
    return rsp


@register_message_handler("GetFruInventoryAreaInfo")
def handle_fru_inventory_are_info(config, req):
    rsp = create_response_message(req)
    fru_file_name = None

    if config['fru'][req.fru_id]:
        fru_file_name = config['fru'][req.fru_id]

    try:
        statinfo = os.stat(fru_file_name)
        rsp.area_size = statinfo.st_size
    except FileNotFoundError:
        print('cannot find file')

    return rsp


@register_message_handler("ReadFruData")
def handle_fru_read(config, req):
    rsp = create_response_message(req)
    fru_file_name = None

    if config['fru'][req.fru_id]:
        fru_file_name = config['fru'][req.fru_id]

    with open(fru_file_name, 'rb') as fru:
        fru.seek(req.offset)
        d = fru.read(req.count)

        rsp.count = len(d)
        rsp.data = d
    return rsp


@register_message_handler("GetSdrRepositoryInfo")
def handle_sdr_repository_info(config, req):
    rsp = create_response_message(req)
    rsp.count = 0
    return rsp


@register_message_handler("ReserveSdrRepository")
def handle_reserve_sdr_repositry(config, req):
    rsp = create_response_message(req)
    return rsp


@register_message_handler("ClearSdrRepository")
def handle_clear_sdr_repositry(config, req):
    rsp = create_response_message(req)
#    if req.cmd in [REPOSITORY_INITIATE_ERASE, REPOSITORY_GET_ERASE_STATUS]:
    rsp.status.erase_in_progress = REPOSITORY_ERASURE_COMPLETED
    return rsp


@register_message_handler("GetSdr")
def handle_get_sdr(req):
    rsp = create_response_message(config, req)
    return rsp


@register_message_handler("GetDeviceSdrInfo")
def handle_device_sdr_info(req):
    rsp = create_response_message(config, req)
    rsp.number_of_sensors = 0
    return rsp


@register_message_handler("ReserveDeviceSdrRepository")
def handle_reserve_device_sdr_repository(config, req):
    rsp = create_response_message(req)
    return rsp


def handle_ipmi_request_msg(config, req):
    try:
        #fct = mapping[type(req)]
        fct = handler_registry[type(req)]
        rsp = fct(config, req)
    except KeyError:
        rsp = create_response_message(req)
        print('no handler for:', type(req))
        rsp.completion_code = CC_INV_CMD
    return rsp


def handle_asf_msg(sdu):
    asf = rmcp.AsfMsg()
    asf.unpack(sdu)
    if asf.asf_type == rmcp.AsfMsg.ASF_TYPE_PRESENCE_PING:
        print('ASF RX: ping:', asf)
    pong = rmcp.AsfPong()
    pdu = pong.pack()
    print('ASF TX: pong:', asf)
    return pdu


def handle_ipmi_msg(config, sdu):

    def _get_group_id(ipmi_sdu):
        group_id = None
        if rx_header.netfn == NETFN_GROUP_EXTENSION:
            group_id = ipmi_sdu[6]
        return group_id

    session.sequence_number += 1
    # rmcp ipmi req msg
    ipmi_rx = rmcp.IpmiMsg()
    ipmi_sdu = ipmi_rx.unpack(sdu)

    rx_header = ipmb.IpmbHeaderReq()
    rx_header.decode(ipmi_sdu)

    group_id = _get_group_id(ipmi_sdu)

    try:
        req = create_message(rx_header.netfn, rx_header.cmd_id, group_id)
    except KeyError:
        print('cannot create message: netfn 0x{:x} cmd: 0x{:x} group: {}'.format(rx_header.netfn, rx_header.cmd_id, group_id))
        # bytes are immutable ... so convert to change
        a = bytearray(ipmi_sdu)
        # set completion code . invalid command
        a[6] = pyipmi.msgs.constants.CC_INV_CMD
        # netfn + 1
        a[1] = a[1] | 0x4
        ipmi_sdu = bytes(a)
        # rmcp ipmi rsp msg
        ipmi_tx = rmcp.IpmiMsg(session)
        tx_data = ipmi_tx.pack(ipmi_sdu)
        return tx_data

    print('IPMI RX: {}: {:s}'.format(type(req).__name__,
            ' '.join('%02x' % b for b in array('B', ipmi_sdu))))
    decode_message(req, ipmi_sdu[6:-1])

    rsp = handle_ipmi_request_msg(config, req)
    data = encode_message(rsp)

    tx_header = ipmb.IpmbHeaderReq()
    tx_header.netfn = rsp.netfn
    tx_header.rs_lun = rx_header.rq_lun
    tx_header.rs_sa = rx_header.rq_sa
    tx_header.rq_seq = rx_header.rq_seq
    tx_header.rq_lun = rx_header.rs_lun
    tx_header.rq_sa = rx_header.rs_sa
    tx_header.cmd_id = rsp.cmdid
    tx_data = ipmb.encode_ipmb_msg(tx_header, data)
    print('IPMI TX: {}: {:s}'.format(type(rsp).__name__,
            ' '.join('%02x' % b for b in array('B', tx_data))))

    # rmcp ipmi rsp msg
    ipmi_tx = rmcp.IpmiMsg(session)
    tx_data = ipmi_tx.pack(tx_data)

    if type(req) == pyipmi.msgs.device_messaging.CloseSessionReq:
        session.session_id = None
        session._auth_type = Session.AUTH_TYPE_NONE
        session._auth_username = None
        session._auth_password = None

    return tx_data


def main(args=None):
    parser = argparse.ArgumentParser(description="IPMI server emulation.")
    parser.add_argument("-p", "--port", type=int, dest="port", help="RMCP port", default=623)
    parser.add_argument("-c", "--config", type=str, dest="config", help="Config file")
    parser.add_argument(
        "-v", action="store_true", dest="verbose", help="be more verbose"
    )

    args = parser.parse_args(args)

    config = None
    if args.config:
        with open(args.config, 'r') as stream:
            config = yaml.safe_load(stream)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, args.port))


    while True:
        pdu, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        msg = rmcp.RmcpMsg()
        sdu = msg.unpack(pdu)

        if msg.class_of_msg == rmcp.RMCP_CLASS_ASF:
            tx_data = handle_asf_msg(sdu)
            rmcp_msg = rmcp.RmcpMsg(rmcp.RMCP_CLASS_ASF)
            pdu = rmcp_msg.pack(tx_data, session.sequence_number)
            sock.sendto(pdu, addr)
        elif msg.class_of_msg == rmcp.RMCP_CLASS_IPMI:
            tx_data = handle_ipmi_msg(config, sdu)
            rmcp_msg = rmcp.RmcpMsg(rmcp.RMCP_CLASS_IPMI)
            pdu = rmcp_msg.pack(tx_data, session.sequence_number)
            sock.sendto(pdu, addr)
        else:
            print('unknown class_of_msg {}'.format(msg.class_of_msg))


if __name__ == '__main__':
    main()
