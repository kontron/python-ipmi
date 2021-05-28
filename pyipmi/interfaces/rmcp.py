# Copyright (c) 2018  Kontron Europe GmbH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

import socket
import struct
import hashlib
import random
import threading
from array import array
from queue import Queue

from .. import Target
from ..session import Session
from ..msgs import (create_message, create_request_by_name,
                    encode_message, decode_message, constants)
from ..messaging import ChannelAuthenticationCapabilities
from ..errors import DecodingError, NotSupportedError
from ..logger import log
from ..interfaces.ipmb import (IpmbHeaderReq, encode_ipmb_msg,
                               encode_bridged_message, decode_bridged_message,
                               rx_filter)
from ..utils import check_completion_code, py3_array_tobytes


CLASS_NORMAL_MSG = 0x00
CLASS_ACK_MSG = 0x80

RMCP_CLASS_ASF = 0x06
RMCP_CLASS_IPMI = 0x07
RMCP_CLASS_OEM = 0x08


def call_repeatedly(interval, func, *args):
    stopped = threading.Event()

    def loop():
        # the first call is in `interval` secs
        while not stopped.wait(interval):
            try:
                func(*args)
            except socket.timeout:
                pass

    t = threading.Thread(target=loop)
    t.daemon = True
    t.start()

    return stopped.set


class RmcpMsg(object):
    RMCP_HEADER_FORMAT = '!BxBB'
    ASF_RMCP_V_1_0 = 6

    def __init__(self, class_of_msg=None):
        if class_of_msg is not None:
            self.class_of_msg = class_of_msg

    def pack(self, sdu, seq_number):
        pdu = struct.pack(self.RMCP_HEADER_FORMAT, self.ASF_RMCP_V_1_0,
                          seq_number, self.class_of_msg)
        if sdu is not None:
            pdu += sdu
        return pdu

    def unpack(self, pdu):
        header_len = struct.calcsize(self.RMCP_HEADER_FORMAT)
        header = pdu[:header_len]
        (self.version, self.seq_number, self.class_of_msg) = \
            struct.unpack(self.RMCP_HEADER_FORMAT, header)
        sdu = pdu[header_len:]

        if self.version != self.ASF_RMCP_V_1_0:
            raise DecodingError('invalid RMCP version field')

        return sdu


class AsfMsg(object):
    ASF_HEADER_FORMAT = '!IBBxB'

    ASF_TYPE_PRESENCE_PONG = 0x40
    ASF_TYPE_PRESENCE_PING = 0x80

    asf_type = 0

    def __init__(self):
        self.iana_enterprise_number = 4542
        self.tag = 0
        self.data = None
        self.sdu = None

    def pack(self):
        if self.data:
            data_len = len(self.data)
        else:
            data_len = 0

        pdu = struct.pack(self.ASF_HEADER_FORMAT,
                          self.iana_enterprise_number,
                          self.asf_type,
                          self.tag,
                          data_len)
        if self.data:
            pdu += self.data

        return pdu

    def unpack(self, sdu):
        self.sdu = sdu
        header_len = struct.calcsize(self.ASF_HEADER_FORMAT)

        header = sdu[:header_len]
        (self.iana_enterprise_number, self.asf_type, self.tag, data_len) = \
            struct.unpack(self.ASF_HEADER_FORMAT, header)

        if len(sdu) < header_len + data_len:
            raise DecodingError('short SDU')
        elif len(sdu) > header_len + data_len:
            raise DecodingError('SDU has extra bytes')

        if data_len != 0:
            self.data = sdu[header_len:header_len + data_len]
        else:
            self.data = None

        if hasattr(self, 'check_header'):
            self.check_header()

    def __str__(self):
        if self.data:
            return ' '.join('%02x' % b for b in array('B', self.data))
        if self.sdu:
            return ' '.join('%02x' % b for b in array('B', self.sdu))
        return ''


class AsfPing(AsfMsg):
    def __init__(self):
        AsfMsg.__init__(self)
        self.asf_type = self.ASF_TYPE_PRESENCE_PING

    def check_header(self):
        if self.asf_type != self.ASF_TYPE_PRESENCE_PING:
            raise DecodingError('type does not match')
        if self.data:
            raise DecodingError('Data length is not zero')


class AsfPong(AsfMsg):
    DATA_FORMAT = '!IIBB6x'

    def __init__(self):
        self.asf_type = self.ASF_TYPE_PRESENCE_PONG
        self.oem_iana_enterprise_number = 4542
        self.oem_defined = 0
        self.supported_entities = 0
        self.supported_interactions = 0

    def unpack(self, sdu):
        AsfMsg.unpack(self, sdu)
        # header_len = struct.calcsize(self.ASF_HEADER_FORMAT)
        (self.oem_iana_enterprise_number, self.oem_defined,
            self.supported_entities, self.supported_interactions) =\
            struct.unpack(self.DATA_FORMAT, self.data)

        self.check_data()

    def check_data(self):
        if self.oem_iana_enterprise_number == 4542 and self.oem_defined != 0:
            raise DecodingError('SDU malformed')
        if self.supported_interactions != 0:
            raise DecodingError('SDU malformed')

    def check_header(self):
        if self.asf_type != self.ASF_TYPE_PRESENCE_PONG:
            raise DecodingError('type does not match')
        if len(self.data) != struct.calcsize(self.DATA_FORMAT):
            raise DecodingError('Data length mismatch')


class IpmiMsg(object):
    HEADER_FORMAT_NO_AUTH = '!BIIB'
    HEADER_FORMAT_AUTH = '!BII16BB'

    def __init__(self, session=None):
        self.session = session

    def _pack_session_id(self):
        if self.session is not None:
            session_id = self.session.sid
        else:
            session_id = 0
        return struct.unpack("<I", struct.pack(">I", session_id))[0]

    def _pack_sequence_number(self):
        if self.session is not None:
            seq = self.session.sequence_number
        else:
            seq = 0

        return struct.unpack("<I", struct.pack(">I", seq))[0]

    def _padd_password(self):
        """Padd the password.

        The password/key is 0 padded to 16-bytes for all specified
        authentication types.
        """
        password = self.session._auth_password
        if isinstance(password, str):
            password = str.encode(password)
        return password.ljust(16, b'\x00')

    def _pack_auth_code_straight(self):
        """Return the auth code as bytestring."""
        return self._padd_password()

    def _pack_auth_code_md5(self, sdu):
        auth_code = struct.pack('>16s I %ds I 16s' % len(sdu),
                                self._pack_auth_code_straight(),
                                self._pack_session_id(),
                                sdu,
                                self._pack_sequence_number(),
                                self._pack_auth_code_straight())
        return hashlib.md5(auth_code).digest()

    def pack(self, sdu):
        if sdu is not None:
            data_len = len(sdu)
        else:
            data_len = 0

        if self.session is not None:
            auth_type = self.session.auth_type
            if self.session.activated:
                self.session.increment_sequence_number()
        else:
            auth_type = Session.AUTH_TYPE_NONE

        pdu = struct.pack('!BII',
                          auth_type,
                          self._pack_sequence_number(),
                          self._pack_session_id())

        if auth_type == Session.AUTH_TYPE_NONE:
            pass
        elif auth_type == Session.AUTH_TYPE_PASSWORD:
            pdu += self._pack_auth_code_straight()
        elif auth_type == Session.AUTH_TYPE_MD5:
            pdu += self._pack_auth_code_md5(sdu)
        else:
            raise NotSupportedError('authentication type %s' % auth_type)

        pdu += py3_array_tobytes(array('B', [data_len]))

        if sdu is not None:
            pdu += sdu

        return pdu

    def unpack(self, pdu):
        auth_type = array('B', pdu)[0]

        if auth_type != 0:
            header_len = struct.calcsize(self.HEADER_FORMAT_AUTH)
            header = pdu[:header_len]
            # TBD .. find a way to do this better
            self.auth_type = array('B', pdu)[0]
            (self.sequence_number,) = struct.unpack('!I', pdu[1:5])
            (self.session_id,) = struct.unpack('!I', pdu[5:9])
            self.auth_code = [a for a in struct.unpack('!16B', pdu[9:25])]
            data_len = array('B', pdu)[25]
        else:
            header_len = struct.calcsize(self.HEADER_FORMAT_NO_AUTH)
            header = pdu[:header_len]
            (self.auth_type, self.sequence_number, self.session_id,
                data_len) = struct.unpack(self.HEADER_FORMAT_NO_AUTH, header)

        if len(pdu) < header_len + data_len:
            raise DecodingError('short SDU')
        elif len(pdu) > header_len + data_len:
            raise DecodingError('SDU has extra bytes ({:d},{:d},{:d} )'.format(
                len(pdu), header_len, data_len))

        if hasattr(self, 'check_header'):
            self.check_header()

        if data_len != 0:
            sdu = pdu[header_len:header_len + data_len]
        else:
            sdu = None

        return sdu

    def check_data(self):
        pass

    def check_header(self):
        pass


class Rmcp(object):
    NAME = 'rmcp'

    _session = None

    def __init__(self, slave_address=0x81, host_target_address=0x20,
                 keep_alive_interval=1):
        self.host = None
        self.port = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq_number = 0xff
        self.slave_address = slave_address
        self.host_target = Target(host_target_address)
        self.set_timeout(2.0)
        self.next_sequence_number = 0
        self.keep_alive_interval = keep_alive_interval
        self._stop_keep_alive = None
        self._q = Queue()
        self.transaction_lock = threading.Lock()

    def _send_rmcp_msg(self, sdu, class_of_msg):
        rmcp = RmcpMsg(class_of_msg)
        pdu = rmcp.pack(sdu, self.seq_number)
        self._sock.sendto(pdu, (self.host, self.port))
        if self.seq_number != 255:
            self.seq_number = (self.seq_number + 1) % 254

    def _receive(self):
        (pdu, _) = self._sock.recvfrom(4096)
        rmcp = RmcpMsg()
        sdu = rmcp.unpack(pdu)
        return (rmcp.seq_number, rmcp.class_of_msg, sdu)

    def set_timeout(self, timeout):
        self._sock.settimeout(timeout)

    def _send_ipmi_msg(self, data):
        log().debug('IPMI TX: {:s}'.format(
            ' '.join('%02x' % b for b in array('B', data))))
        ipmi = IpmiMsg(self._session)
        tx_data = ipmi.pack(data)
        self._send_rmcp_msg(tx_data, RMCP_CLASS_IPMI)

    def _receive_ipmi_msg(self):
        (_, class_of_msg, pdu) = self._receive()
        if class_of_msg != RMCP_CLASS_IPMI:
            raise DecodingError('invalid class field in ASF message')
        msg = IpmiMsg()
        data = msg.unpack(pdu)
        log().debug('IPMI RX: {:s}'.format(
            ' '.join('%02x' % b for b in array('B', data))))
        return data

    def _send_asf_msg(self, msg):
        log().debug('ASF TX: msg')
        self._send_rmcp_msg(msg.pack(), RMCP_CLASS_ASF)

    def _receive_asf_msg(self, cls):
        (_, class_of_msg, data) = self._receive()
        log().debug('ASF RX: msg')
        if class_of_msg != RMCP_CLASS_ASF:
            raise DecodingError('invalid class field in ASF message')
        msg = cls()
        msg.unpack(data)
        return msg

    def ping(self):
        ping = AsfPing()
        self._send_asf_msg(ping)
        self._receive_asf_msg(AsfPong)

    def _get_channel_auth_cap(self):
        CHANNEL_NUMBER_FOR_THIS = 0xe
        # get channel auth cap
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.target = self.host_target
        req.channel.number = CHANNEL_NUMBER_FOR_THIS
        req.privilege_level.requested = Session.PRIV_LEVEL_ADMINISTRATOR
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        caps = ChannelAuthenticationCapabilities(rsp)
        return caps

    def _get_session_challenge(self, session):
        # get session challenge
        req = create_request_by_name('GetSessionChallenge')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        if session._auth_username:
            req.user_name = session._auth_username.ljust(16, '\x00')
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        return rsp

    def _activate_session(self, session, challenge):
        # activate session
        req = create_request_by_name('ActivateSession')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        req.privilege_level.maximum_requested =\
            Session.PRIV_LEVEL_ADMINISTRATOR
        req.challenge_string = challenge
        req.session_id = self._session.sid
        req.initial_outbound_sequence_number = random.randrange(1, 0xffffffff)
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        return rsp

    def _set_session_privilege_level(self, level):
        req = create_request_by_name('SetSessionPrivilegeLevel')
        req.target = self.host_target
        req.privilege_level.requested = level
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        return rsp

    def _get_device_id(self):
        req = create_request_by_name('GetDeviceId')
        req.target = self.host_target
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)

    def establish_session(self, session):
        self._session = None
        self.host = session._rmcp_host
        self.port = session._rmcp_port

        # 0 - Ping
        self.ping()

        # 1 - Get Channel Authentication Capabilities
        log().debug('Get Channel Authentication Capabilities')
        caps = self._get_channel_auth_cap()
        log().debug('%s' % caps)

        # 2 - Get Session Challenge
        log().debug('Get Session Challenge')
        session.auth_type = caps.get_max_auth_type()
        rsp = self._get_session_challenge(session)
        session_challenge = rsp.challenge_string
        session.sid = rsp.temporary_session_id
        self._session = session

        # 3 - Activate Session
        log().debug('Activate Session')
        rsp = self._activate_session(session, session_challenge)
        self._session.sid = rsp.session_id
        self._session.sequence_number = rsp.initial_inbound_sequence_number
        self._session.activated = True

        log().debug('Set Session Privilege Level')
        # 4 - Set Session Privilege Level
        self._set_session_privilege_level(Session.PRIV_LEVEL_ADMINISTRATOR)

        log().debug('Session opened')

        if self.keep_alive_interval:
            self._stop_keep_alive = call_repeatedly(
                    self.keep_alive_interval, self._get_device_id)

    def close_session(self):
        if self._stop_keep_alive:
            self._stop_keep_alive()

        if self._session.activated is False:
            log().debug('Session already closed')
            return

        log().debug('Close Session %s' % self._session)
        req = create_request_by_name('CloseSession')
        req.target = self.host_target
        req.session_id = self._session.sid
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        self._session.activated = False

#        self._q.join()

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _send_and_receive(self, target, lun, netfn, cmdid, payload):
        """Send and receive data using RMCP interface.

        target:
        lun:
        netfn:
        cmdid:
        raw_bytes: IPMI message payload as bytestring

        Returns the received data as array.
        """
        self._inc_sequence_number()

        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmd_id = cmdid

        # Bridge message
        if target.routing:
            tx_data = encode_bridged_message(target.routing, header, payload,
                                             self.next_sequence_number)
        else:
            tx_data = encode_ipmb_msg(header, payload)

        with self.transaction_lock:
            self._send_ipmi_msg(tx_data)

            received = False
            while received is False:
                if not self._q.empty():
                    rx_data = self._q.get()
                else:
                    rx_data = self._receive_ipmi_msg()

                if array('B', rx_data)[5] == constants.CMDID_SEND_MESSAGE:
                    rx_data = decode_bridged_message(rx_data)

                received = rx_filter(header, rx_data)

                if not received:
                    self._q.put(rx_data)

        return rx_data[6:-1]

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        """Interface function to send and receive raw message.

        target: IPMI target
        lun: logical unit number
        netfn: network function
        raw_bytes: RAW bytes as bytestring

        Returns the IPMI message response bytestring.
        """
        return self._send_and_receive(target=target,
                                      lun=lun,
                                      netfn=netfn,
                                      cmdid=array('B', raw_bytes)[0],
                                      payload=raw_bytes[1:])

    def send_and_receive(self, req):
        """Interface function to send and receive an IPMI message.

        target: IPMI target
        req: IPMI message request

        Returns the IPMI message response.
        """
        rx_data = self._send_and_receive(target=req.target,
                                         lun=req.lun,
                                         netfn=req.netfn,
                                         cmdid=req.cmdid,
                                         payload=encode_message(req))
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)
        return rsp
