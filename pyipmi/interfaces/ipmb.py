# Copyright (c) 2015  Kontron Europe GmbH
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

from array import array

from ..logger import log
from ..msgs import (create_message, create_request_by_name,
                    encode_message, decode_message, constants)
from ..utils import check_completion_code
from ..utils import py3_array_tobytes, py3_array_frombytes


def checksum(data):
    """Calculate the checksum."""
    csum = 0
    for b in data:
        csum += b
    return -csum % 256


class IpmbHeader(object):
    """Representation of the IPMI message header.

    Request:
    *-------*--------------*----------*-------*---------------*-------*
    | rs_sa | netfn/rs_lun | checksum | rq_sa | rq_seq/rq_lun | cmdid |
    *-------*--------------*----------*-------*---------------*-------*

    Response:
    *-------*--------------*----------*-------*---------------*-------*
    | rq_sa | netfn/rq_lun | checksum | rs_sa | rq_seq/rs_lun | cmdid |
    *-------*--------------*----------*-------*---------------*-------*
    """

    def __init__(self, data=None):
        if data:
            self.decode(data)

    rs_sa = None
    rs_lun = None
    rq_sa = None
    rq_lun = None
    rq_seq = None
    netfn = None
    cmdid = None
    checksum = None


class IpmbHeaderReq(IpmbHeader):
    """Representation of the IPMI request message header."""

    def encode(self):
        """Encode the header."""
        data = array('B')
        data.append(self.rs_sa)
        data.append(self.netfn << 2 | self.rs_lun)
        data.append(checksum((self.rs_sa, data[1])))
        data.append(self.rq_sa)
        data.append(self.rq_seq << 2 | self.rq_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data):
        """Decode the header."""
        msg = array('B')
        py3_array_frombytes(msg, data)
        self.rs_sa = msg[0]
        self.netfn = msg[1] >> 2
        self.rs_lun = msg[1] & 3
        self.checksum = msg[2]
        self.rq_sa = msg[3]
        self.rq_seq = msg[4] >> 2
        self.rq_lun = msg[4] & 3
        self.cmdid = msg[5]


class IpmbHeaderRsp(IpmbHeader):
    """Representation of the IPMI response message header."""

    def encode(self):
        """Encode the header."""
        data = array('B')
        data.append(self.rq_sa)
        data.append(self.netfn << 2 | self.rq_lun)
        data.append(checksum((self.rq_sa, data[1])))
        data.append(self.rs_sa)
        data.append(self.rq_seq << 2 | self.rs_lun)
        data.append(self.cmdid)
        return py3_array_tobytes(data)

    def decode(self, data):
        """Decode the header."""
        data = array('B', data)
        self.rq_sa = data[0]
        self.netfn = data[1] >> 2
        self.rq_lun = data[1] & 3
        self.checksum = data[2]
        self.rs_sa = data[3]
        self.rq_seq = data[4] >> 2
        self.rs_lun = data[4] & 3
        self.cmdid = data[5]

    def from_req_header(self, req_header):
        self.rs_lun = req_header.rq_lun
        self.rs_sa = req_header.rq_sa
        self.rq_seq = req_header.rq_seq
        self.rq_lun = req_header.rs_lun
        self.rq_sa = req_header.rs_sa
        self.netfn = req_header.netfn
        self.cmdid = req_header.cmdid


def encode_ipmb_msg(header, data):
    """Encode an IPMB message.

    header: IPMB header object
    data: IPMI message data as bytestring

    Returns the message as bytestring.
    """
    msg = array('B')
    py3_array_frombytes(msg, header.encode())
    if data is not None:
        a = array('B')
        py3_array_frombytes(a, data)
        msg.extend(a)
    msg.append(checksum(msg[3:]))
    return py3_array_tobytes(msg)


def encode_send_message(payload, rq_sa, rs_sa, channel, seq, tracking=1):
    """Encode a send message command and embedd the message to be send.

    payload: the message to be send as bytestring
    rq_sa: the requester source address
    rs_sa: the responder source address
    channel: the channel
    seq: the sequence number
    tracking: tracking

    Returns an encode send message as bytestring
    """
    req = create_request_by_name('SendMessage')
    req.channel.number = channel
    req.channel.tracking = tracking
    data = encode_message(req)

    header = IpmbHeaderReq()
    header.netfn = req.__netfn__
    header.rs_lun = 0
    header.rs_sa = rs_sa
    header.rq_seq = seq
    header.rq_lun = 0
    header.rq_sa = rq_sa
    header.cmdid = req.__cmdid__

    return encode_ipmb_msg(header, data + payload)


def encode_bridged_message(routing, header, payload, seq):
    """Encode a (multi-)bridged command and embedd the message to be send.

    routing:
    payload: the message to be send as bytestring
    header:
    seq: the sequence number

    Returns the encoded send message as bytestring
    """
    # change header requester addresses for bridging
    header.rq_sa = routing[-1].rq_sa
    header.rs_sa = routing[-1].rs_sa
    tx_data = encode_ipmb_msg(header, payload)

    for bridge in reversed(routing[:-1]):
        tx_data = encode_send_message(tx_data,
                                      rq_sa=bridge.rq_sa,
                                      rs_sa=bridge.rs_sa,
                                      channel=bridge.channel,
                                      seq=seq)

    return tx_data


def decode_bridged_message(rx_data):
    """Decode a (multi-)bridged command.

    rx_data: the received message as bytestring

    Returns the decoded message as bytestring
    """
    while array('B', rx_data)[5] == constants.CMDID_SEND_MESSAGE:
        rsp = create_message(constants.NETFN_APP + 1,
                             constants.CMDID_SEND_MESSAGE, None)
        decode_message(rsp, rx_data[6:])
        check_completion_code(rsp.completion_code)
        rx_data = rx_data[7:-1]

        if len(rx_data) < 6:
            break
    return rx_data


def rx_filter(header, data):
    """Check if the message in rx_data matches to the information in header.

    The following checks are done:
      - Header checksum
      - Payload checksum
      - NetFn matching
      - LUN matching
      - Command Id matching

    header: the header to compare with
    data: the received message as bytestring
    """
    rsp_header = IpmbHeaderRsp(data=data)

    data = array('B', data)

    checks = [
        (checksum(data[0:3]), 0, 'Header checksum failed'),
        (checksum(data[3:]), 0, 'payload checksum failed'),
        # rsp_header.rq_sa, header.rq_sa, 'slave address mismatch'),
        (rsp_header.netfn, header.netfn | 1, 'NetFn mismatch'),
        # rsp_header.rs_sa, header.rs_sa, 'target address mismatch'),
        # rsp_header.rq_lun, header.rq_lun, 'request LUN mismatch'),
        (rsp_header.rs_lun, header.rs_lun, 'responder LUN mismatch'),
        (rsp_header.rq_seq, header.rq_seq, 'sequence number mismatch'),
        (rsp_header.cmdid, header.cmdid, 'command id mismatch'),
    ]

    match = True

    for left, right, msg in checks:
        if left != right:
            log().debug('{:s}: {:d} {:d}'.format(msg, left, right))
            match = False

    return match
