import os
import select
import time
from array import array

from ..msgs import create_message, encode_message, decode_message
from ..errors import IpmiTimeoutError
from ..logger import log
from ..interfaces.ipmb import IpmbHeaderReq, checksum, rx_filter, encode_ipmb_msg


class IpmbDev(object):
    """This interface uses ipmb-dev-int linux driver."""

    NAME = 'ipmbdev'

    def __init__(self, slave_address=0x20, port='/dev/ipmb-0'):
        # TODO: slave address is currently not defined here
        self.slave_address = slave_address
        self.timeout = 0.25
        self.max_retries = 3
        self.next_sequence_number = 0

        self._dev = os.open(port, os.O_RDWR)

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

    def close_session(self):
        os.close(self._dev)

    def is_ipmc_accessible(self, target):
        header = IpmbHeaderReq()
        header.netfn = 6
        header.rs_lun = 0
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = 1
        self._send_raw(header, None)
        self._receive_raw(header)
        return True

    def _inc_sequence_number(self):
        self.next_sequence_number = (self.next_sequence_number + 1) % 64

    @staticmethod
    def _encode_ipmb_msg_req(header, cmd_data):
        data = header.encode()
        data.extend(cmd_data)
        data.append(checksum(data[2:]))

        return data

    def _send_raw(self, header, raw_bytes):
        raw_bytes = encode_ipmb_msg(header, raw_bytes)
        i2c_addr = header.rs_sa >> 1

        log().debug('I2C TX to %02Xh [%s]', i2c_addr,
                    ' '.join(['%02x' % b for b in raw_bytes]))
        os.write(self._dev, bytes([len(raw_bytes)]) + raw_bytes)

    def _receive_raw(self, header):
        start_time = time.time()
        rsp_received = False
        poll_returned_no_data = False
        while not rsp_received:
            timeout = self.timeout - (time.time() - start_time)

            if timeout <= 0 or poll_returned_no_data:
                raise IpmiTimeoutError()

            r, w, e = select.select([self._dev], [], [], timeout)
            if not self._dev in r:
                poll_returned_no_data = True
                continue

            rx_data = os.read(self._dev, 256)
            # ipmb-dev-int puts message length into first byte
            assert rx_data[0] == len(rx_data) - 1
            rx_data = rx_data[1:]

            rx_data = array('B', rx_data)
            log().debug('I2C RX from %02Xh [%s]', rx_data[3],
                        ' '.join(['%02x' % c for c in rx_data]))

            rsp_received = rx_filter(header, rx_data)
            rx_data = rx_data[1:]

        return rx_data

    def _send_and_receive(self, target, lun, netfn, cmdid, payload):
        """Send and receive data using ipmb-dev-int interface.

        target:
        lun:
        netfn:
        cmdid:
        payload: IPMI message payload as bytestring

        Returns the received data as bytestring
        """
        self._inc_sequence_number()

        # assemble IPMB header
        header = IpmbHeaderReq()
        header.netfn = netfn
        header.rs_lun = lun
        header.rs_sa = target.ipmb_address
        header.rq_seq = self.next_sequence_number
        header.rq_lun = 0
        header.rq_sa = self.slave_address
        header.cmdid = cmdid

        retries = 0
        while retries < self.max_retries:
            try:
                self._send_raw(header, payload)
                rx_data = self._receive_raw(header)
                break
            except IpmiTimeoutError:
                pass
            except IOError:
                pass

            retries += 1
            time.sleep(retries * 0.2)

        else:
            raise IpmiTimeoutError()

        return rx_data[5:-1]

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
        log().debug('IPMI Request [%s]', req)

        rx_data = self._send_and_receive(target=req.target,
                                         lun=req.lun,
                                         netfn=req.netfn,
                                         cmdid=req.cmdid,
                                         payload=encode_message(req))
        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rx_data)

        log().debug('IPMI Response [%s])', rsp)

        return rsp
