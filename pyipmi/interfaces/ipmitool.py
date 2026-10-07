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

"""Interface which sends the requests with the ipmitool program.

:class:`Ipmitool` runs ``ipmitool raw`` for each request and parses its
output. The host, the credentials and the serial port are taken from the
session.

Example:
    Get the device ID of a BMC over LAN with ipmitool ``-I lanplus``::

        interface = pyipmi.interfaces.create_interface(
            'ipmitool', interface_type='lanplus')
        ipmi = pyipmi.create_connection(interface)
        ipmi.session.set_session_type_rmcp('10.0.0.1', port=623)
        ipmi.session.set_auth_type_user('admin', 'admin')
        ipmi.target = pyipmi.Target(ipmb_address=0x20)
        with ipmi:
            print(ipmi.get_device_id())
"""

from __future__ import annotations

import logging
import re
import shlex

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
from ..msgs.constants import CC_OK
from ..utils import py3dec_unic_bytes_fix, py3_array_tobytes
from .base import Interface

logger = logging.getLogger(__name__)


class Ipmitool(Interface):
    """This interface uses the ipmitool raw command.

    This "emulates" a RMCP session by using raw commands.

    It uses the session information to assemble the correct ipmitool
    parameters. Therefore, a session has to be established before any request
    can be sent.

    A target is addressed with the ipmitool options ``-t`` and ``-b`` for
    a routing with one bridge, and additionally ``-T`` and ``-B`` for a
    routing with two bridges.
    """

    NAME = 'ipmitool'
    IPMITOOL_PATH = 'ipmitool'
    supported_interfaces = ['lan', 'lanplus', 'serial-terminal', 'open']

    def __init__(self, interface_type: str = 'lan', cipher: int | None = None,
                 retries: int | None = None,
                 timeout: int | None = None) -> None:
        """Create the interface.

        `retries` and `timeout` are passed to ipmitool as `-R` (number of
        retries) and `-N` (timeout of each try in seconds) and are only
        supported by the lan and lanplus interface types. If not given the
        ipmitool defaults are used.

        Args:
            interface_type: The ipmitool interface (``-I``): ``'lan'``,
                ``'lanplus'``, ``'serial-terminal'`` or ``'open'``.
            cipher: The cipher suite ID (``-C``), the ipmitool default if
                not given.
            retries: The number of retries (``-R``).
            timeout: The timeout of each try in seconds (``-N``).

        Raises:
            RuntimeError: An argument is not supported or out of range.
        """
        if interface_type in self.supported_interfaces:
            self._interface_type = interface_type
        else:
            raise RuntimeError('interface type %s not supported' %
                               interface_type)
        if cipher is not None and int(cipher) not in range(256):
            raise RuntimeError('cipher %s not in allowed range [0-255]' %
                               cipher)
        else:
            self._cipher = cipher

        if (retries is not None or timeout is not None) and \
                interface_type not in ('lan', 'lanplus'):
            raise RuntimeError('retries and timeout are not supported by '
                               'interface type %s' % interface_type)
        if retries is not None and int(retries) < 0:
            raise RuntimeError('retries %s must not be negative' % retries)
        if timeout is not None and int(timeout) < 1:
            raise RuntimeError('timeout %s must be at least 1 second' %
                               timeout)
        self._retries = None if retries is None else int(retries)
        self._timeout = None if timeout is None else int(timeout)

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
        self._session: Session | None = None

    def establish_session(self, session: Session) -> None:
        """Keep the session for the ipmitool options.

        Nothing is sent, ipmitool establishes a session for each request.

        Args:
            session: The session with the host and the credentials.
        """
        self._session = session

    def _get_session(self) -> Session:
        if self._session is None:
            raise RuntimeError('Session needs to be set')
        return self._session

    def rmcp_ping(self) -> None:
        """Check if the BMC answers, with ``ipmitool session info all``.

        Raises:
            RuntimeError: The interface type is ``'serial-terminal'``, the
                session is not set or ipmitool is not found.
            IpmiTimeoutError: ipmitool failed.
        """
        if self._interface_type == 'serial-terminal':
            raise RuntimeError(
                'rmcp_ping not supported on "serial-terminal" interface')

        # for now this uses ipmitool..
        session = self._get_session()
        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % session.rmcp_host)
        cmd += (' -p %s' % session.rmcp_port)
        cmd += (' -v')
        cmd += self._build_ipmitool_retries()
        if session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += (' -A NONE')
        elif session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += self._build_ipmitool_credentials()
        cmd += (' session info all')

        _, rc = self._run_ipmitool(cmd)
        if rc:
            raise IpmiTimeoutError()

    def is_target_accessible(self, target: Target) -> bool:
        """Check if the BMC answers, see :meth:`rmcp_ping`.

        Args:
            target: Not used, the BMC of the session is checked.

        Returns:
            True if the BMC answers, False if ipmitool failed.
        """
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
                raise IpmiConnectionError(f'ipmitool: {line}')

            # Check for completion code
            match_completion_code = self.re_completion_code.match(line)
            if match_completion_code:
                cc = int(match_completion_code.group(1), 16)
                break

            # Check for error opening ipmi device
            if self.re_could_not_open.match(line):
                raise RuntimeError('ipmitool failed: '
                                   f'{py3dec_unic_bytes_fix(output)}')

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
        """Send a raw request with ``ipmitool raw``, return the response.

        Args:
            target: The target of the request.
            lun: The logical unit number.
            netfn: The network function.
            raw_bytes: The request, starting with the command ID.

        Returns:
            The response, starting with the completion code. If ipmitool
            reports no completion code, the completion code is 0.

        Raises:
            IpmiTimeoutError: ipmitool timed out.
            IpmiConnectionError: ipmitool could not establish a session.
            IpmiLongPasswordError: The password is too long for ipmitool.
            AuthenticationError: The authentication failed.
            RuntimeError: ipmitool failed otherwise, is not found, or the
                target or the session is not supported.
            ValueError: A bridge channel of the routing is None.
        """
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

        logger.debug('IPMI RX: {:s}'.format(
            ''.join('%02x ' % b for b in array('B', data))))

        return py3_array_tobytes(data)

    @staticmethod
    def _build_ipmitool_raw_data(lun: int, netfn: int, raw: bytes) -> str:
        cmd = f' -l {lun:d} raw '
        cmd += ' '.join(['0x%02x' % (d)
                         for d in [netfn] + array('B', raw).tolist()])
        return cmd

    @staticmethod
    def _routing_channel(target: Target, index: int) -> int:
        """Return the channel of a routing entry, ipmitool needs it."""
        assert target.routing is not None
        channel = target.routing[index].channel
        if channel is None:
            raise ValueError('the ipmitool interface needs the bridge channel '
                             'of routing entry %d, got None: %s'
                             % (index, target))
        return channel

    @staticmethod
    def _build_ipmitool_target(target: Target) -> str:
        cmd = ''
        if target is None:
            return ''
        if target.routing is not None:
            # we have to do bridging here
            if len(target.routing) == 1:
                # no bridging, the request goes to the BMC itself
                pass
            elif len(target.routing) == 2:
                # ipmitool/shelfmanager does implicit bridging
                cmd += (' -t 0x%02x' % target.routing[1].rs_sa)
                cmd += (' -b %d' % Ipmitool._routing_channel(target, 0))
            elif len(target.routing) == 3:
                cmd += (' -T 0x%02x' % target.routing[1].rs_sa)
                cmd += (' -B %d' % Ipmitool._routing_channel(target, 0))
                cmd += (' -t 0x%02x' % target.routing[2].rs_sa)
                cmd += (' -b %d' % Ipmitool._routing_channel(target, 1))
            else:
                raise RuntimeError('The ipmitool interface supports at most '
                                   'double bridging %s' % target)

        elif target.ipmb_address:
            cmd += (' -t 0x%02x' % target.ipmb_address)

        return cmd

    def _build_ipmitool_retries(self) -> str:
        cmd = ''
        if self._retries is not None:
            cmd += ' -R %d' % self._retries
        if self._timeout is not None:
            cmd += ' -N %d' % self._timeout
        return cmd

    def _build_ipmitool_credentials(self) -> str:
        # The command is executed by a shell, so the credentials have to be
        # quoted to prevent the shell from interpreting characters like
        # '$', '`', '"' or '\'.
        session = self._get_session()
        username = session.auth_username_bytes.decode()
        password = session.auth_password_bytes.decode()
        return (f' -U {shlex.quote(username)}'
                f' -P {shlex.quote(password)}')

    def _build_ipmitool_priv_level(self, level: int) -> str:
        LEVELS = {
                   Session.PRIV_LEVEL_USER: 'USER',
                   Session.PRIV_LEVEL_OPERATOR: 'OPERATOR',
                   Session.PRIV_LEVEL_ADMINISTRATOR: 'ADMINISTRATOR'
                 }

        return (' -L %s' % LEVELS[level])

    def _build_ipmitool_cmd(self, target: Target, lun: int, netfn: int,
                            raw_bytes: bytes) -> str:
        session = self._get_session()

        cmd = self.IPMITOOL_PATH
        cmd += (' -I %s' % self._interface_type)
        cmd += (' -H %s' % session.rmcp_host)
        cmd += (' -p %s' % session.rmcp_port)
        cmd += (' -v')

        cmd += self._build_ipmitool_priv_level(session.priv_level)

        if self._cipher is not None:
            cmd += (' -C %s' % self._cipher)
        cmd += self._build_ipmitool_retries()
        if session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += ' -P ""'
        elif session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += self._build_ipmitool_credentials()
        else:
            raise RuntimeError('Session type %d not supported' %
                               session.auth_type)

        cmd += self._build_ipmitool_target(target)
        cmd += self._build_ipmitool_raw_data(lun, netfn, raw_bytes)
        cmd += (' 2>&1')

        return cmd

    def _build_serial_ipmitool_cmd(self, target: Target, lun: int, netfn: int,
                                   raw_bytes: bytes) -> str:
        session = self._get_session()

        cmd = (f'{self.IPMITOOL_PATH} -I {self._interface_type} '
               f'-D {session.serial_port}:{session.serial_baudrate}')

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
        logger.debug('Running ipmitool "%s"', cmd)

        child = Popen(cmd, shell=True, stdout=PIPE)
        output = child.communicate()[0]

        logger.debug('return with rc=%d, output was:\n%s',
                     child.returncode,
                     output)

        if child.returncode == 127:
            raise RuntimeError('ipmitool command not found')

        return output, child.returncode
