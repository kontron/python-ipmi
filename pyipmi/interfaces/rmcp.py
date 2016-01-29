import socket
import struct
import array
import hashlib

from pyipmi import Target
from pyipmi.session import Session
from pyipmi.msgs import create_message, create_request_by_name, \
        encode_message, decode_message, device_messaging
from pyipmi.messaging import ChannelAuthenticationCapabilities
from pyipmi.errors import DecodingError, NotSupportedError
from pyipmi.logger import log
from pyipmi.interfaces.ipmb import IpmbHeader, checksum, encode_ipmb_msg
from pyipmi.utils import check_completion_code

CLASS_NORMAL_MSG = 0x00
CLASS_ACK_MSG = 0x80

RMCP_CLASS_ASF = 0x06
RMCP_CLASS_IPMI = 0x07
RMCP_CLASS_OEM = 0x08



class RmcpMsg:
    RMCP_HEADER_FORMAT = '!BxBB'
    ASF_RMCP_V_1_0  = 6

    def __init__(self, class_of_msg=None):
        if class_of_msg is not None:
            self.class_of_msg = class_of_msg

    def pack(self, sdu, seq_number):
        pdu = struct.pack(self.RMCP_HEADER_FORMAT,
                self.ASF_RMCP_V_1_0, seq_number, self.class_of_msg)
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
            raise UnpackException('invalid RMCP version field')

        return sdu


class AsfMsg:
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
            data_len = len(data)
        else:
            data_len = 0

        pdu = struct.pack(self.ASF_HEADER_FORMAT, self.iana_enterprise_number,
                    self.asf_type, self.tag, data_len)
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
            return ' '.join('%02x' % ord(b) for b in self.data)
        if self.sdu:
            return ' '.join('%02x' % ord(b) for b in self.sdu)
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
        header_len = struct.calcsize(self.ASF_HEADER_FORMAT)
        (self.oem_iana_enterprise_number, self.oem_defined,
                self.supported_entities, self.supported_interactions) = \
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


class IpmiMsg():
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
        """The password/key is 0 padded to 16-bytes for all specified
        authentication types. """
        return self.session._auth_password.ljust(16, '\x00')

    def _pack_auth_code_straight(self):
        return self._padd_password()

    def _pack_auth_code_md5(self, sdu):
        auth_code = struct.pack('>16s I %ds I 16s' % len(sdu),
                self.session._auth_password,
                self._pack_session_id(),
                sdu,
                self._pack_sequence_number(),
                self.session._auth_password)
        return hashlib.md5(auth_code).digest()

    def pack(self, sdu):
        if sdu is not None:
            data_len = len(sdu)
        else:
            data_len = 0

        if self.session is not None:
            auth_type = self.session.auth_type
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

        pdu += chr(data_len)

        if sdu is not None:
            pdu += sdu

        return pdu

    def unpack(self, pdu):
        self.pdu = pdu
        auth_type = ord(pdu[0])

        if auth_type != 0:
            header_len = struct.calcsize(self.HEADER_FORMAT_AUTH)
        else:
            header_len = struct.calcsize(self.HEADER_FORMAT_NO_AUTH)

        header = pdu[:header_len]
        if auth_type != 0:
            # TBD .. find a way to do this better
            self.auth_type = ord(pdu[0])
            (self.sequence_number,) = struct.unpack('!I', pdu[1:5])
            (self.session_id,) = struct.unpack('!I', pdu[5:9])
            self.auth_code =\
                    [a for a in struct.unpack('!16B', pdu[9:25])]
            data_len = ord(pdu[25])
        else:
            (self.auth_type, self.sequence_number,
                    self.session_id, data_len) =\
                            struct.unpack(self.HEADER_FORMAT_NO_AUTH, header)

        if len(pdu) < header_len + data_len:
            raise DecodingError('short SDU')
        elif len(pdu) > header_len + data_len:
            raise DecodingError('SDU has extra bytes')

        if hasattr(self, 'check_header'):
            self.check_header()

        if data_len != 0:
            self.sdu = pdu[header_len:header_len + data_len]
        else:
            self.sdu = None

        return self.sdu


    def check_data(self):
        pass

    def check_header(self):
        pass


class Rmcp:
    NAME = 'rmcp'

    _session = None

    def __init__(self, slave_address=0x81, host_target_address=0x20):
        self.host = None
        self.port = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq_number = 0xff
        self.slave_address = slave_address
        self.host_target = Target(host_target_address)
        self.set_timeout(2.0)
        self.next_sequence_number = 0
        self._debug = False

    def _send_rmcp_msg(self, sdu, class_of_msg):
        rmcp = RmcpMsg(class_of_msg)
        pdu = rmcp.pack(sdu, self.seq_number)

        if self._debug:
            print 'TX: %s' %(' '.join('%02x' % ord(b) for b in pdu))

        self._sock.sendto(pdu, (self.host, self.port))
        if self.seq_number != 255:
            self.seq_number = (self.seq_number + 1) % 254

    def _receive(self):
        (pdu, _) = self._sock.recvfrom(4096)
        if self._debug:
            print 'RX: %s' %(' '.join('%02x' % ord(b) for b in pdu))

        rmcp = RmcpMsg()
        sdu = rmcp.unpack(pdu)


        return (rmcp.seq_number, rmcp.class_of_msg, sdu)

    def set_timeout(self, timeout):
        self._sock.settimeout(timeout)

    def _send_ipmi_msg(self, data):
        ipmi = IpmiMsg(self._session)
        self._send_rmcp_msg(ipmi.pack(data), RMCP_CLASS_IPMI)

    def _receive_ipmi_msg(self):
        (_, class_of_msg, pdu) = self._receive()
        if class_of_msg != RMCP_CLASS_IPMI:
            raise DecodingError('invalid class field in ASF message')
        msg = IpmiMsg()
        return msg.unpack(pdu)

    def _send_asf_msg(self, msg):
        self._send_rmcp_msg(msg.pack(), RMCP_CLASS_ASF)

    def _receive_asf_msg(self, cls):
        (_, class_of_msg, data) = self._receive()
        if class_of_msg != RMCP_CLASS_ASF:
            raise DecodingError('invalid class field in ASF message')
        msg = cls()
        msg.unpack(data)
        return msg

    def ping(self):
        ping = AsfPing()
        self._send_asf_msg(ping)
        pong = self._receive_asf_msg(AsfPong)

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
        if self._debug:
            print caps
        return caps

    def _get_session_challenge(self, session):
        # get session challenge
        req = create_request_by_name('GetSessionChallenge')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        if session._auth_username:
            req.user_name = session._auth_username
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)
        return rsp

    def _activate_session(self, session, challenge):
        # activate session
        req = create_request_by_name('ActivateSession')
        req.target = self.host_target
        req.authentication.type = session.auth_type
        req.privilege_level.maximum_requested = \
                        Session.PRIV_LEVEL_ADMINISTRATOR
        req.challenge_string = challenge
        req.session_id = self._session.sid
        req.initial_outbound_sequence_number = 5
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

    def establish_session(self, session):
        self.host = session._rmcp_host
        self.port = session._rmcp_port

        self._session = None

        self.ping()

        caps = self._get_channel_auth_cap()

        session.auth_type = caps.get_max_auth_type
        rsp = self._get_session_challenge(session)
        session_challenge = rsp.challenge_string
        #print session

        # now set session
        self._session = session
        self._session.sid = rsp.temporary_session_id

        rsp = self._activate_session(session, session_challenge)
        self._session.sid = rsp.session_id
        self._session.sequence_number = rsp.initial_inbound_sequence_number
        #print self._session

        # set session privilege level
        rsp = self._set_session_privilege_level(Session.PRIV_LEVEL_ADMINISTRATOR)

    def close_session(self):
        req = create_request_by_name('CloseSession')
        req.target = self.host_target
        req.session_id = self._session.sid
        rsp = self.send_and_receive(req)
        check_completion_code(rsp.completion_code)

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _send_and_receive(self, target, lun, netfn, cmdid, payload):
        self._inc_sequence_number()

        header = IpmbHeader()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmd_id = cmdid

        cmd_data =  [ord(c) for c in payload]
        tx_data = encode_ipmb_msg(header, cmd_data)
        self._send_ipmi_msg(tx_data.tostring())
        data = self._receive_ipmi_msg()
        if self._debug:
            print 'RX IPMI: %s' %(' '.join('%02x' % ord(b) for b in data))

        return data[6:-1]

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        return self._send_and_receive(target, lun, netfn, ord(raw_bytes[0]),
                raw_bytes[1:])

    def send_and_receive(self, msg):
        rx_data = self._send_and_receive(msg.target, msg.lun, msg.netfn,
                        msg.cmdid, encode_message(msg))
        msg = create_message(msg.cmdid, msg.netfn + 1)
        decode_message(msg, rx_data)
        return msg

if __name__ == '__main__':
    host = '10.0.114.12'
    session = Session()
    session.set_auth_type_user('admin', 'admin')

    r = Rmcp(host)
    r._debug = True
    r.ping()
    r.establish_session(session)
