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


import re

from subprocess import Popen, PIPE
from array import array

from ..session import Session
from ..errors import IpmiTimeoutError, IpmiConnectionError, IpmiLongPasswordError
from ..logger import log
from ..msgs import encode_message, decode_message, create_message
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

    def __init__(self, interface_type='lan', cipher=None):
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
        self._session = None

    def open(self):
        pass

    def close(self):
        pass

    def establish_session(self, session):
        self._session = session

    def close_session(self):
        pass

    def rmcp_ping(self):

        if self._interface_type == 'serial-terminal':
            raise RuntimeError(
                'rcmp_ping not supported on "serial-terminal" interface')

        # for now this uses impitool..
        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % self._session.rmcp_host)
        cmd += (' -p %s' % self._session.rmcp_port)
        if self._session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += (' -A NONE')
        elif self._session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += (' -U "%s"' % self._session.auth_username)
            cmd += (' -P "%s"' % self._session.auth_password)
        cmd += (' session info all')

        _, rc = self._run_ipmitool(cmd)
        if rc:
            raise IpmiTimeoutError()

    def is_ipmc_accessible(self, target):
        try:
            self.rmcp_ping()
            accessible = True
        except IpmiTimeoutError:
            accessible = False

        return accessible

    def _parse_output(self, output):
        cc, rsp = None, None
        hexstr = ''

        for line in py3dec_unic_bytes_fix(output).split('\n'):
            # Don't try to parse ipmitool error messages
            if 'failed' in line:
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

            hexstr += line.replace('\r', '').strip() + ' '

        hexstr = hexstr.strip()
        if len(hexstr):
            rsp = array('B', [
                int(value, 16) for value in hexstr.split(' ')
            ])

        return cc, rsp

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
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

    def send_and_receive(self, req):
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
    def _build_ipmitool_raw_data(lun, netfn, raw):
        cmd = ' -l {:d} raw '.format(lun)
        cmd += ' '.join(['0x%02x' % (d)
                         for d in [netfn] + array('B', raw).tolist()])
        return cmd

    @staticmethod
    def _build_ipmitool_target(target):
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

    def _build_ipmitool_priv_level(self, level):
        LEVELS = {
                   Session.PRIV_LEVEL_USER: 'USER',
                   Session.PRIV_LEVEL_OPERATOR: 'OPERATOR',
                   Session.PRIV_LEVEL_ADMINISTRATOR: 'ADMINISTRATOR'
                 }

        return (' -L %s' % LEVELS[level])

    def _build_ipmitool_cmd(self, target, lun, netfn, raw_bytes):
        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % self._session.rmcp_host)
        cmd += (' -p %s' % self._session.rmcp_port)

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

    def _build_serial_ipmitool_cmd(self, target, lun, netfn, raw_bytes):
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

    def _build_open_ipmitool_cmd(self, target, lun, netfn, raw_bytes):
        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)

        cmd += self._build_ipmitool_target(target)
        cmd += self._build_ipmitool_raw_data(lun, netfn, raw_bytes)
        cmd += (' 2>&1')

        return cmd

    @staticmethod
    def _run_ipmitool(cmd):
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
