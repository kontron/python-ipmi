import socket
import struct
import array

from pyipmi import Target, Session
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import create_message, create_request_by_name, \
        encode_message, decode_message, device_messaging
from pyipmi.errors import DecodingError
from pyipmi.logger import log
from pyipmi.interfaces.ipmb import IpmbHeader, checksum
from pyipmi.utils import check_completion_code

CLASS_NORMAL_MSG = 0x00
CLASS_ACK_MSG = 0x80

RMCP_CLASS_ASF = 0x06
RMCP_CLASS_IPMI = 0x07
RMCP_CLASS_OEM = 0x08

ASF_TYPE_PRESENCE_PONG = 0x40
ASF_TYPE_PRESENCE_PING = 0x80

class RmcpMsg:
    pass

class AsfMsg:
    ASF_HEADER_FORMAT = '!IBBxB'

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

        sdu = struct.pack(self.ASF_HEADER_FORMAT, self.iana_enterprise_number,
                    self.asf_type, self.tag, data_len)
        if self.data:
            sdu += self.data

        return sdu

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
    pp_fields = []

    def __init__(self):
        AsfMsg.__init__(self)
        self.asf_type = ASF_TYPE_PRESENCE_PING

    def check_header(self):
        if self.asf_type != ASF_TYPE_PRESENCE_PING:
            raise DecodingError('type does not match')
        if self.data:
            raise DecodingError('Data length is not zero')


class AsfPong(AsfMsg):
    DATA_FORMAT = '!IIBB6x'
    pp_fields = [
                ('asf_type', lambda i: '%02x' % i),
                ('oem_iana_enterprise_number', lambda i: '%04x' % i),
                ('oem_defined', lambda i: '%04x' % i),
                ('supported_entities', lambda i: '%02x' % i),
                ('supported_interactions', lambda i: '%02x' % i),
            ]

    def __init__(self):
        self.asf_type = ASF_TYPE_PRESENCE_PONG
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
        if self.asf_type != ASF_TYPE_PRESENCE_PONG:
            raise DecodingError('type does not match')
        if len(self.data) != struct.calcsize(self.DATA_FORMAT):
            raise DecodingError('Data length mismatch')


class IpmiSession():
    authentication_type = 0
    sequence_number = 0
    session_id = 0
    authentication_code = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]


class IpmiMsg():
    HEADER_FORMAT_NO_AUTH = '!BIIB'
    HEADER_FORMAT_AUTH = '!BII16BB'

    authentication_type = 0
    sequence_number = 0
    session_id = 0
    authentication_code = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    def __init__(self, session=None, data=None):

        if session != None:
            self.authentication_type = sesssion.authentication_type
            self.sequence_number = session.sequence_number
            self.session_id = session.session_id
            self.authentication_code = session.authentication_code

        self.data = data

    def pack(self):
        if self.data is not None:
            data_len = len(self.data)
        else:
            data_len = 0

        if self.authentication_type != 0:
            sdu = struct.pack('!BII',
                        self.authentication_type,
                        self.sequence_number,
                        self.session_id)
            # TBD .. find a way to do this with pack
            sdu +=  array.array('B', self.authentication_code).tostring()
            sdu += chr(data_len)

        else:
            sdu = struct.pack(self.HEADER_FORMAT_NO_AUTH,
                        self.authentication_type,
                        self.sequence_number,
                        self.session_id,
                        data_len)

        if self.data is not None:
            sdu += self.data

        return sdu

    def unpack(self, sdu):
        self.sdu = sdu
        authentication_type = ord(sdu[0])

        if authentication_type != 0:
            header_len = struct.calcsize(self.HEADER_FORMAT_AUTH)
        else:
            header_len = struct.calcsize(self.HEADER_FORMAT_NO_AUTH)

        header = sdu[:header_len]
        if authentication_type != 0:
            # TBD .. find a way to do this better
            self.authentication_type = ord(sdu[0])
            (self.sequence_number,) = struct.unpack('!I', sdu[1:5])
            (self.session_id,) = struct.unpack('!I', sdu[5:9])
            self.authentication_code =\
                    [a for a in struct.unpack('!16B', sdu[9:25])]
            data_len = ord(sdu[25])
        else:
            (self.authentication_type, self.sequence_number,
                    self.session_id, data_len) = struct.unpack(self.HEADER_FORMAT_NO_AUTH, header)

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

    def check_data(self):
        pass

    def check_header(self):
        pass


class Rmcp:
    RMCP_HEADER_FORMAT = '!BxBB'
    ASF_RMCP_V_1_0  = 6

    session_id = None

    def __init__(self, host, port=623, slave_address=0x81):
        self.host = host
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.version = self.ASF_RMCP_V_1_0
        self.seq_number = 0xff
        self.slave_address = slave_address
        self.set_timeout(2.0)
        self.next_sequence_number = 0
        self._debug = False

    def _send(self, sdu, class_of_msg):
        header = struct.pack(self.RMCP_HEADER_FORMAT,
                self.version, self.seq_number, class_of_msg)
        pdu = header + sdu
        if self._debug:
            print 'TX: %s' %(' '.join('%02x' % ord(b) for b in pdu))
        self._sock.sendto(pdu, (self.host, self.port))
        if self.seq_number != 255:
            self.seq_number = (self.seq_number + 1) % 254

    def _receive(self):
        (data, _) = self._sock.recvfrom(4096)
        if self._debug:
            print 'RX: %s' %(' '.join('%02x' % ord(b) for b in data))
        header_len = struct.calcsize(self.RMCP_HEADER_FORMAT)
        header = data[:header_len]
        (version, seq_number, class_of_msg) = \
                struct.unpack(self.RMCP_HEADER_FORMAT, header)
        if version != self.version:
            raise UnpackException('invalid RMCP version field')
        return (seq_number, class_of_msg, data[header_len:])

    def set_timeout(self, timeout):
        self._sock.settimeout(timeout)

    def _send_ipmi_msg(self, data):
        msg = IpmiMsg(data=data)
        self._send(msg.pack(), RMCP_CLASS_IPMI)

    def _receive_ipmi_msg(self):
        (_, class_of_msg, pdu) = self._receive()
        if class_of_msg != RMCP_CLASS_IPMI:
            raise DecodingError('invalid class field in ASF message')
        msg = IpmiMsg()
        msg.unpack(pdu)
        return msg

    def _send_asf_msg(self, msg):
        self._send(msg.pack(), RMCP_CLASS_ASF)

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

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

        t = Target(0x20)

        # get channel auth cap
        req = create_request_by_name('GetChannelAuthenticationCapabilities')
        req.channel.number = 0xe
        req.privilege_level.requested = 4
        rx_data = self._send_and_receive(t, req.lun, req.netfn, req.cmdid, encode_message(req))
        rsp = create_message(req.cmdid, req.netfn + 1)
        decode_message(rsp, rx_data)
        check_completion_code(rsp.completion_code)

        # get session challenge
        req = create_request_by_name('GetSessionChallenge')
        req.authentication.type = self._session.auth_type
        if self._session._auth_username:
            req.user_name = self._session._auth_username

        tx_data = encode_message(req)
        rx_data = self._send_and_receive(t, req.lun, req.netfn, req.cmdid,tx_data)
        rsp = create_message(req.cmdid, req.netfn + 1)
        decode_message(rsp, rx_data)
        check_completion_code(rsp.completion_code)
        self.session_id = rsp.temporary_session_id
        session_challenge = rsp.challenge_string

        # activate session
        req = create_request_by_name('ActivateSession')
        req.authentication.type = self._session.auth_type
        req.privilege_level.maximum_requested = 4
        req.challenge_string = session_challenge
        req.initial_outbound_sequence_number = 1
        tx_data = encode_message(req)
        rx_data = self._send_and_receive(t, req.lun, req.netfn, req.cmdid,tx_data)
        rsp = create_message(req.cmdid, req.netfn + 1)
        decode_message(rsp, rx_data)
        check_completion_code(rsp.completion_code)

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    def _encode_ipmb_msg_req(self, header, cmd_data):
        data = header.encode()
        data.extend(cmd_data)
        data.append(checksum(data[3:]))

        return data

    def _send_and_receive(self, target, lun, netfn, cmdid, payload):
#        self._inc_sequence_number()

        header = IpmbHeader()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmd_id = cmdid

        cmd_data =  [ord(c) for c in payload]
        tx_data = self._encode_ipmb_msg_req(header, cmd_data)
        self._send_ipmi_msg(tx_data.tostring())
        msg = self._receive_ipmi_msg()
        print 'RX IPMI: %s' %(' '.join('%02x' % ord(b) for b in msg.data))

        return msg.data[6:-1]

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        return self._send_and_receive(target, lun, netfn, ord(raw_bytes[0]),
                raw_bytes[1:])

    def send_and_receive(self, msg):
        pass


if __name__ == '__main__':
    host = '10.0.114.12'
    s = Session()

    s.set_auth_type_user('admin', 'admin')
    r = Rmcp(host)
    r._debug = True
    r.ping()
    r.establish_session(s)
