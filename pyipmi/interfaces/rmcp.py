import socket
import struct

from error import UnpackError
from utils import hexdump
import asf

CLASS_NORMAL_MSG = 0x00
CLASS_ACK_MSG = 0x80
CLASS_ASF = 0x06
CLASS_IPMI = 0x07
CLASS_OEM = 0x08

from error import UnpackError
from utils import MsgPPrinter

PRESENCE_PONG = 0x40
PRESENCE_PING = 0x80

class _Msg:
    HEADER_FORMAT = '!IBBxB'

    def __init__(self):
        self.iana_enterprise_number = 4542
        self.data = None
        self.tag = 0

    def pack(self):
        if self.data:
            data_len = len(data)
        else:
            data_len = 0

        sdu = struct.pack(self.HEADER_FORMAT,
                self.iana_enterprise_number,
                self.type, self.tag, data_len)
        if self.data:
            sdu += self.data

        return sdu

    def unpack(self, sdu):
        header_len = struct.calcsize(self.HEADER_FORMAT)

        header = sdu[:header_len]
        (self.iana_enterprise_number, self.type, self.tag, data_len) = \
                struct.unpack(self.HEADER_FORMAT, header)

        if len(sdu) < header_len + data_len:
            raise UnpackError('short SDU')
        elif len(sdu) > header_len + data_len:
            raise UnpackError('SDU has extra bytes')

        if data_len != 0:
            self.data = sdu[header_len:header_len + data_len]
        else:
            self.data = None

        if hasattr(self, 'check_header'):
            self.check_header()

class Ping(_Msg, MsgPPrinter):
    pp_fields = []

    def __init__(self):
        _Msg.__init__(self)
        self.type = PRESENCE_PING

    def check_header(self):
        if self.type != PRESENCE_PING:
            raise UnpackError('type does not match')
        if self.data:
            raise UnpackError('Data length is not zero')

class Pong(_Msg, MsgPPrinter):
    DATA_FORMAT = '!IIBB6x'
    pp_fields = [
                ('type', lambda i: '%02x' % i),
                ('oem_iana_enterprise_number', lambda i: '%04x' % i),
                ('oem_defined', lambda i: '%04x' % i),
                ('supported_entities', lambda i: '%02x' % i),
                ('supported_interactions', lambda i: '%02x' % i),
            ]

    def __init__(self):
        self.type = PRESENCE_PONG
        self.oem_iana_enterprise_number = 4542
        self.oem_defined = 0
        self.supported_entities = 0
        self.supported_interactions = 0

    def pack(self):
        header = _Msg.pack(self)
        data = struct.pack(DATA_FORMAT,
                self.oem_iana_enterprise_number,
                self.oem_defined,
                self.supported_entities,
                self.supported_interactions)

        return header + data

    def unpack(self, sdu):
        _Msg.unpack(self, sdu)
        header_len = struct.calcsize(self.HEADER_FORMAT)
        (self.oem_iana_enterprise_number, self.oem_defined,
                self.supported_entities, self.supported_interactions) = \
                        struct.unpack(self.DATA_FORMAT, self.data)

        self.check_data()

    def check_data(self):
        if self.oem_iana_enterprise_number == 4542 and self.oem_defined != 0:
            raise UnpackError('SDU malformed')
        if self.supported_interactions != 0:
            raise UnpackError('SDU malformed')

    def check_header(self):
        if self.type != PRESENCE_PONG:
            raise UnpackError('type does not match')
        if len(self.data) != struct.calcsize(self.DATA_FORMAT):
            raise UnpackError('Data length mismatch')


class Rmcp:
    HEADER_FORMAT = '!BxBB'

    def __init__(self, host):
        self.host = host
        self.port = 623
        self.version = 6
        self.seq_number = 255
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_timeout(2.0)
        self._debug = False

    def _send(self, sdu, class_of_msg):
        header = struct.pack(self.HEADER_FORMAT,
                self.version, self.seq_number, class_of_msg)
        pdu = header + sdu
        if self._debug:
            hexdump(pdu)
        self._sock.sendto(pdu, (self.host, self.port))
        if self.seq_number != 255:
            self.seq_number = (self.seq_number + 1) % 254

    def _receive(self):
        (data, _) = self._sock.recvfrom(4096)
        if self._debug:
            hexdump(data)
        header_len = struct.calcsize(self.HEADER_FORMAT)
        header = data[:header_len]
        (version, seq_number, class_of_msg) = \
                struct.unpack(self.HEADER_FORMAT, header)
        if version != self.version:
            raise UnpackException('invalid RMCP version field')
        return (seq_number, class_of_msg, data[header_len:])

    def set_timeout(self, timeout):
        self._sock.settimeout(timeout)

    def send_ipmi_pdu(self, pdu):
        self._send(pdu, CLASS_IPMI)

    def receive_ipmi_pdu(self):
        (_, class_of_msg, pdu) = self._receive()
        if class_of_msg != CLASS_IPMI:
            raise UnpackError('invalid class field in ASF message')
        return pdu

    def send_asf_msg(self, asf_msg):
        print asf_msg
        self._send(asf_msg.pack(), CLASS_ASF)

    def receive_asf_msg(self, type):
        (_, class_of_msg, data) = self._receive()
        if class_of_msg != CLASS_ASF:
            raise UnpackError('invalid class field in ASF message')
        msg = type()
        msg.unpack(data)
        return msg

    def ping(self):
        self.send_asf_msg(asf.Ping())
        pong = self.receive_asf_msg(asf.Pong)
        print pong

if __name__ == '__main__':
    host = '10.0.113.200'
    r = Rmcp(host)
    r.ping()
