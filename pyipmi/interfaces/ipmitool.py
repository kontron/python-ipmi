# Copyright (c) 2014  Kontron Europe GmbH
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


from __future__ import annotations

import re

from subprocess import Popen, PIPE
from array import array

from .. import Target
from ..session import Session
from ..errors import (
    IpmiTimeoutError,
    IpmiConnectionError,
    IpmiLongPasswordError,
    AuthenticationError,
)
from ..logger import log
from ..msgs import encode_message, decode_message, create_message, Message
from ..msgs.constants import CC_OK
from ..utils import py3dec_unic_bytes_fix, ByteBuffer, py3_array_tobytes


class Ipmitool(object):
    """This interface uses the ipmitool raw command.

    This "emulates" a RMCP session by using raw commands.

    It uses the session information to assemble the correct ipmitool
    parameters. Therefore, a session has to be established before any request
    can be sent.
    """

    NAME = 'ipmitool'
    IPMITOOL_PATH = 'ipmitool'
    supported_interfaces = ['lan', 'lanplus', 'serial-terminal', 'open']

    def __init__(self, interface_type: str = 'lan', cipher: int | None = None) -> None:
        if interface_type in self.supported_interfaces:
            self._interface_type = interface_type
        else:
            raise RuntimeError('interface type %s not supported' %
                               interface_type)
        if cipher is not None and int(cipher) not in range(0, 255):
            raise RuntimeError('cipher %s not in allowed range [0-255]' %
                               cipher)
        else:
            self._cipher = cipher

        self.re_completion_code = re.compile(
                r"Unable to send RAW command \(.*rsp=(0x[0-9a-f]+)\)")
        self.re_timeout = re.compile(
                r"Unable to send RAW command \(.*cmd=0x[0-9a-f]+\)")
        self.re_unable_establish = re.compile(
                r".*Unable to establish.*")
        self.re_could_not_open = re.compile(
                r".*Could not open device.*")
        self.re_long_password = re.compile(
                r".*password is longer than.*")
        self.re_authentication_error = re.compile(
                r".*RAKP [0-9]+ HMAC.*")
        self.re_raw_request = re.compile(
                r".*RAW REQUEST\s*\((\d+)\s*bytes?\)")
        self._session = None

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def establish_session(self, session: Session) -> None:
        self._session = session

    def close_session(self) -> None:
        pass

    def rmcp_ping(self) -> None:

        if self._interface_type == 'serial-terminal':
            raise RuntimeError(
                'rcmp_ping not supported on "serial-terminal" interface')

        # for now this uses impitool..
        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % self._session.rmcp_host)
        cmd += (' -p %s' % self._session.rmcp_port)
        cmd += (' -v')
        if self._session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += (' -A NONE')
        elif self._session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += (' -U "%s"' % self._session.auth_username)
            cmd += (' -P "%s"' % self._session.auth_password)
        cmd += (' session info all')

        _, rc = self._run_ipmitool(cmd)
        if rc:
            raise IpmiTimeoutError()

    def is_ipmc_accessible(self, target: Target) -> bool:
        try:
            self.rmcp_ping()
            accessible = True
        except IpmiTimeoutError:
            accessible = False

        return accessible

    def _parse_output(self, output: bytes) -> tuple[int | None, array | None]:
        cc, rsp = None, None
        values = []
        skip_bytes_remaining = 0

        for line in py3dec_unic_bytes_fix(output).split('\n'):
            # Don't try to parse ipmitool error messages
            if 'failed' in line:
                continue
            # Don't try to parse spurious ipmitool output
            if 'Received a response with unexpected ID' in line:
                continue

            # Check for timeout
            if self.re_timeout.match(line):
                raise IpmiTimeoutError()

            # Check for unable to establish session
            if self.re_unable_establish.match(line):
                raise IpmiConnectionError('ipmitool: {}'.format(line))

            # Check for completion code
            match_completion_code = self.re_completion_code.match(line)
            if match_completion_code:
                cc = int(match_completion_code.group(1), 16)
                break

            # Check for error opening ipmi device
            if self.re_could_not_open.match(line):
                raise RuntimeError('ipmitool failed: {}'.format(output))

            if self.re_long_password.match(line):
                raise IpmiLongPasswordError(line)

            if self.re_authentication_error.match(line):
                raise AuthenticationError('Authentication error')

            # With "-v" ipmitool echoes the outgoing request as its own
            # "RAW REQUEST (N bytes)" hex dump right before the actual
            # "RAW RSP" hex dump. Both look like plain hex lines, so we
            # must discard exactly the announced N request bytes -
            # otherwise they get prepended to the parsed response,
            # corrupting every multi-byte-payload command's response.
            match_raw_request = self.re_raw_request.match(line)
            if match_raw_request:
                skip_bytes_remaining = int(match_raw_request.group(1))
                continue

            line = line.replace('\r', '').strip()
            if not line:
                continue

            # With "-v" ipmitool interleaves plain-text debug lines
            # (e.g. "RAW REQ (...)", "Discovered IPMB address 0x0")
            # with the actual hex response line. Parse hex per-line
            # so one non-hex debug line doesn't discard already
            # parsed response bytes from other lines.
            try:
                line_values = [int(value, 16) for value in line.split()]
            except ValueError:
                continue
            if any(value > 0xff for value in line_values):
                continue

            if skip_bytes_remaining > 0:
                consumed = min(len(line_values), skip_bytes_remaining)
                skip_bytes_remaining -= consumed
                line_values = line_values[consumed:]
                if not line_values:
                    continue

            values.extend(line_values)

        if values:
            rsp = array('B', values)

        return cc, rsp

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> bytes:
        if self._interface_type in ['lan', 'lanplus']:
            cmd = self._build_ipmitool_cmd(target, lun, netfn, raw_bytes)
        elif self._interface_type in ['open']:
            cmd = self._build_open_ipmitool_cmd(target, lun, netfn, raw_bytes)
        elif self._interface_type in ['serial-terminal']:
            cmd = self._build_serial_ipmitool_cmd(target, lun, netfn,
                                                  raw_bytes)
        else:
            raise RuntimeError('interface type %s not supported' %
                               self._interface_type)

        output, rc = self._run_ipmitool(cmd)
        cc, rsp = self._parse_output(output)

        data = array('B')

        if cc is not None:
            data.append(cc)
        else:
            if rc != 0:
                raise RuntimeError('ipmitool failed with rc=%d' % rc)
            # completion code
            data.append(CC_OK)
            if rsp:
                data.extend(rsp)

        log().debug('IPMI RX: {:s}'.format(
            ''.join('%02x ' % b for b in array('B', data))))

        return py3_array_tobytes(data)

    def send_and_receive(self, req: Message) -> Message:
        log().debug('IPMI Request [%s]', req)

        req_data = ByteBuffer((req.cmdid,))
        req_data.push_string(encode_message(req))

        rsp_data = self.send_and_receive_raw(req.target, req.lun, req.netfn,
                                             py3_array_tobytes(req_data))

        rsp = create_message(req.netfn + 1, req.cmdid, req.group_extension)
        decode_message(rsp, rsp_data)
        log().debug('IPMI Response [%s])', rsp)

        return rsp

    @staticmethod
    def _build_ipmitool_raw_data(lun: int, netfn: int, raw: bytes) -> str:
        cmd = ' -l {:d} raw '.format(lun)
        cmd += ' '.join(['0x%02x' % (d)
                         for d in [netfn] + array('B', raw).tolist()])
        return cmd

    @staticmethod
    def _build_ipmitool_target(target: Target) -> str:
        cmd = ''
        if target is None:
            return ''
        if target.routing is not None:
            # we have to do bridging here
            if len(target.routing) == 1:
                pass
            if len(target.routing) == 2:
                # ipmitool/shelfmanager does implicit bridging
                cmd += (' -t 0x%02x' % target.routing[1].rs_sa)
                cmd += (' -b %d' % target.routing[0].channel)
            elif len(target.routing) == 3:
                cmd += (' -T 0x%02x' % target.routing[1].rs_sa)
                cmd += (' -B %d' % target.routing[0].channel)
                cmd += (' -t 0x%02x' % target.routing[2].rs_sa)
                cmd += (' -b %d' % target.routing[1].channel)
            else:
                raise RuntimeError('The impitool interface at most double '
                                   'briding %s' % target)

        elif target.ipmb_address:
            cmd += (' -t 0x%02x' % target.ipmb_address)

        return cmd

    def _build_ipmitool_priv_level(self, level: int) -> str:
        LEVELS = {
                   Session.PRIV_LEVEL_USER: 'USER',
                   Session.PRIV_LEVEL_OPERATOR: 'OPERATOR',
                   Session.PRIV_LEVEL_ADMINISTRATOR: 'ADMINISTRATOR'
                 }

        return (' -L %s' % LEVELS[level])

    def _build_ipmitool_cmd(self, target: Target, lun: int, netfn: int,
                            raw_bytes: bytes) -> str:
        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % self._session.rmcp_host)
        cmd += (' -p %s' % self._session.rmcp_port)
        cmd += (' -v')

        cmd += self._build_ipmitool_priv_level(self._session.priv_level)

        if self._cipher:
            cmd += (' -C %s' % self._cipher)
        if self._session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += ' -P ""'
        elif self._session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += (' -U "%s"' % self._session.auth_username)
            cmd += (' -P "%s"' % self._session.auth_password)
        else:
            raise RuntimeError('Session type %d not supported' %
                               self._session.auth_type)

        cmd += self._build_ipmitool_target(target)
        cmd += self._build_ipmitool_raw_data(lun, netfn, raw_bytes)
        cmd += (' 2>&1')

        return cmd

    def _build_serial_ipmitool_cmd(self, target: Target, lun: int, netfn: int,
                                   raw_bytes: bytes) -> str:
        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = '{path!s:s} -I {interface!s:s} -D {port!s:s}:{baud!s:s}'\
            .format(
                path=self.IPMITOOL_PATH,
                interface=self._interface_type,
                port=self._session.serial_port,
                baud=self._session.serial_baudrate
            )

        cmd += self._build_ipmitool_target(target)
        cmd += self._build_ipmitool_raw_data(lun, netfn, raw_bytes)

        return cmd

    def _build_open_ipmitool_cmd(self, target: Target, lun: int, netfn: int,
                                 raw_bytes: bytes) -> str:
        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)

        cmd += self._build_ipmitool_target(target)
        cmd += self._build_ipmitool_raw_data(lun, netfn, raw_bytes)
        cmd += (' 2>&1')

        return cmd

    @staticmethod
    def _run_ipmitool(cmd: str) -> tuple[bytes, int]:
        """Legacy call of ipmitool (will be removed in future)."""
        log().debug('Running ipmitool "%s"', cmd)

        child = Popen(cmd, shell=True, stdout=PIPE)
        output = child.communicate()[0]

        log().debug('return with rc=%d, output was:\n%s',
                    child.returncode,
                    output)

        if child.returncode == 127:
            raise RuntimeError('ipmitool command not found')

        return output, child.returncode
