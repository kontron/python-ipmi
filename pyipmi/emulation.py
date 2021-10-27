import argparse
import logging
import os
import random
import socket
import sys
import yaml

from array import array
from collections import OrderedDict

import pyipmi

from pyipmi.logger import log

from pyipmi.interfaces import rmcp
from pyipmi.interfaces import ipmb
from pyipmi.msgs import (create_message, decode_message, encode_message,
                         create_response_message, create_request_by_name)
from pyipmi.msgs import constants
from pyipmi.session import Session
from pyipmi.utils import ByteBuffer

UDP_IP = "127.0.0.1"
UDP_PORT = 1623

session = Session()

sdr_list = OrderedDict()
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

    try:
        fru_filename = config['fru'][req.fru_id]
    except KeyError:
        log().debug('cannot find file for fru_id={} in config'.format(req.fru_id))
        rsp.completion_code = constants.CC_PARAM_OUT_OF_RANGE
        return rsp

    try:
        statinfo = os.stat(fru_filename)
        rsp.area_size = statinfo.st_size
    except FileNotFoundError:
        log().debug('cannot open file={} for fru_id={}'.format(fru_filename, req.fru_id))
        rsp.completion_code = constants.CC_PARAM_OUT_OF_RANGE
        return rsp

    return rsp


@register_message_handler("ReadFruData")
def handle_fru_read(config, req):
    rsp = create_response_message(req)
    fru_file_name = None

    try:
        fru_filename = config['fru'][req.fru_id]
    except KeyError:
        rsp.completion_code = constants.CC_PARAM_OUT_OF_RANGE
        log().debug('cannot find file for fru_id={} in config'.format(req.fru_id))
        return rsp

    try:
        with open(fru_filename, 'rb') as fru:
            fru.seek(req.offset)
            d = fru.read(req.count)

            rsp.count = len(d)
            rsp.data = d
    except FileNotFoundError:
        log().debug('cannot open file={} for fru_id={}'.format(fru_filename, req.fru_id))
        rsp.completion_code = constants.CC_PARAM_OUT_OF_RANGE
        return rsp

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
    rsp.status.erase_in_progress = constants.REPOSITORY_ERASURE_COMPLETED
    return rsp


@register_message_handler("GetSdr")
def handle_get_sdr(config, req):
    rsp = create_response_message(req)

    next_index = list(sdr_list.keys()).index(req.record_id) + 1
    try:
        next_record_id = list(sdr_list)[next_index]
    except IndexError:
        next_record_id = 0xffff
    rsp.next_record_id = next_record_id

    sdr = sdr_list[req.record_id]
    rsp.record_data = sdr.data[req.offset:req.offset+req.bytes_to_read]
    return rsp


@register_message_handler("GetDeviceSdrInfo")
def handle_device_sdr_info(config, req):
    rsp = create_response_message(req)
    rsp.number_of_sensors = 0
    return rsp


@register_message_handler("ReserveDeviceSdrRepository")
def handle_reserve_device_sdr_repository(config, req):
    rsp = create_response_message(req)
    return rsp


#@register_message_handler("GetDeviceSdr")
#def handle_get_device_sdr(config, req):
#    rsp = create_response_message(req)
#    return rsp

@register_message_handler("SendMessage")
def handle_send_message(config, req):
    # tbd
    rsp = create_response_message(req)
    rsp.completion_code = constants.CC_PARAM_OUT_OF_RANGE
    return rsp



def handle_ipmi_request_msg(config, req):
    try:
        fct = handler_registry[type(req)]
    except KeyError:
        rsp = create_response_message(req)
        log().debug('no handler for: {}'.format(type(req)))
        rsp.completion_code = constants.CC_INV_CMD
        return rsp

    rsp = fct(config, req)
    return rsp


def handle_asf_msg(sdu):
    asf = rmcp.AsfMsg()
    asf.unpack(sdu)
    t = rmcp.AsfMsg().from_data(sdu)
    if asf.asf_type == rmcp.AsfMsg.ASF_TYPE_PRESENCE_PING:
        log().debug('ASF RX: ping: {}'.format(asf))
    pong = rmcp.AsfPong()
    pdu = pong.pack()
    log().debug('ASF TX: pong: {}'.format(asf))
    return pdu


def handle_ipmi_msg(config, sdu):

    def _get_group_id(ipmi_sdu):
        group_id = None
        if rx_header.netfn == constants.NETFN_GROUP_EXTENSION:
            group_id = ipmi_sdu[6]
        return group_id

    session.sequence_number += 1
    if session.sequence_number > 255:
        session.sequence_number = 0
    # rmcp ipmi req msg
    ipmi_rx = rmcp.IpmiMsg()
    ipmi_sdu = ipmi_rx.unpack(sdu)

    rx_header = ipmb.IpmbHeaderReq()
    rx_header.decode(ipmi_sdu)

    group_id = _get_group_id(ipmi_sdu)

    try:
        req = create_message(rx_header.netfn, rx_header.cmdid, group_id)
    except KeyError:
        log().debug('Cant create message: netfn 0x{:x} cmd: 0x{:x} group: {}'.format(rx_header.netfn, rx_header.cmdid, group_id))
        # bytes are immutable ... so convert to change
        a = bytearray(ipmi_sdu)
        # set completion code . invalid command
        a[6] = constants.CC_INV_CMD
        # netfn + 1
        a[1] = a[1] | 0x4
        ipmi_sdu = bytes(a)
        # rmcp ipmi rsp msg
        ipmi_tx = rmcp.IpmiMsg(session)
        tx_data = ipmi_tx.pack(ipmi_sdu)
        return tx_data

    log().debug('IPMI RX: {}: {:s}'.format(req,
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
    tx_header.cmdid = rsp.cmdid
    tx_data = ipmb.encode_ipmb_msg(tx_header, data)
    log().debug('IPMI TX: {}: {:s}'.format(rsp,
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


def load_sdr_dump(dump_file):
    with open(dump_file, 'rb') as f:
        while True:
            h = f.read(5)
            if not h:
                break
            t = pyipmi.sdr.SdrCommon(h)
            b = f.read(t.length)
            sdr = pyipmi.sdr.SdrCommon().from_data(h + b)
            sdr_list[sdr.id] = sdr


def main(args=None):
    parser = argparse.ArgumentParser(description="IPMI server emulation.")
    parser.add_argument("-p", "--port", type=int, dest="port", help="RMCP port", default=623)
    parser.add_argument("-c", "--config", type=str, dest="config", help="Config file")
    parser.add_argument(
        "-v", action="store_true", dest="verbose", help="be more verbose"
    )

    args = parser.parse_args(args)

    handler = logging.StreamHandler()
    if args.verbose:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
    pyipmi.logger.add_log_handler(handler)
    pyipmi.logger.set_log_level(logging.DEBUG)

    config = None
    if args.config:
        with open(args.config, 'r') as stream:
            config = yaml.safe_load(stream)

    if 'sdr' in config:
        load_sdr_dump(config['sdr'])

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
