#
# pyipmi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import re
from subprocess import Popen, PIPE
from array import array
from pyipmi import Session
from pyipmi.errors import TimeoutError
from pyipmi.logger import log
from pyipmi.msgs import encode_message, decode_message, create_message

class Ipmitool:
    """This interface uses the ipmitool raw command to "emulate" a RMCP
    session.
    
    It uses the session information to assemble the correct ipmitool
    parameters. Therefore, a session has to be established before any request
    can be sent.
    """

    NAME = 'ipmitool'
    IPMITOOL_PATH = 'ipmitool'

    def __init__(self):
        self.re_err = re.compile(
                "Unable to send RAW command \(.*rsp=(0x[0-9a-f]+)\)")
        self.re_timeout = re.compile(
                "Unable to send RAW command \(.*cmd=0x[0-9a-f]+\)")

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

    def rmcp_ping(self):
        # for now this uses impitool..
        cmd = self.IPMITOOL_PATH
        cmd += (' -I lan')
        cmd += (' -H %s' % self._session._rmcp_host)
        cmd += (' -p %s' % self._session._rmcp_port)
        cmd += (' -A NONE')
        cmd += (' session info all')

        log().debug('Run ipmitool "%s"', cmd)
        child = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        child.communicate()

        log().debug('rc = %s' % child.returncode)
        if child.returncode:
            raise TimeoutError()

    def send_and_receive_raw(self, target, raw_data):
        cmd = '-l %d raw 0x%02x ' % (ord(raw_data[0]) & 0x3,
                (ord(raw_data[0]) >> 2) & 0x3f)
        cmd += ' '.join(['0x%02x' % ord(d) for d in raw_data[1:]])

        # run ipmitool
        output, rc = self._run_ipmitool(target, cmd)

        # check for errors
        match_err = self.re_err.match(output)
        match_timeout = self.re_timeout.match(output)
        data = array('c')
        if match_err:
            cc = int(match_err.group(1), 16)
            data.append(chr(cc))
        elif match_timeout:
            raise TimeoutError()
        else:
            if rc != 0:
                raise RuntimeError('ipmitool failed with rc=%d' % rc)
            # completion code
            data.append(chr(0))
            output_lines = output.split('\n')
            # strip 'Close Session command failed' lines
            output_lines = [ l for l in output_lines
                    if not l.startswith('Close Session command failed') ]
            output = ''.join(output_lines).replace('\r','').strip()
            if len(output):
                for x in output.split(' '):
                    data.append(chr(int(x, 16)))
        
        return data

    def send_and_receive(self, req):

        log().debug('IPMI Request [%s]', req)

        req_data = chr(req.netfn << 2 | req.lun)
        req_data += (chr(req.cmdid))
        req_data += encode_message(req)

        rsp_data = self.send_and_receive_raw(req.target, req_data)

        rsp = create_message(req.cmdid, req.netfn + 1)
        decode_message(rsp, rsp_data.tostring())
        log().debug('IPMI Response [%s])', rsp)

        return rsp
 
    def _run_ipmitool(self, target, ipmitool_cmd):
        """Legacy call of ipmitool (will be removed in future).
        """

        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I lan')
        cmd += (' -H %s' % self._session._rmcp_host)
        cmd += (' -p %s' % self._session._rmcp_port)

        if hasattr(target, 'routing'):
            # we have to do bridging here
            if len(target.routing) == 1:
                # ipmitool/shelfmanager does implicit bridging
                cmd += (' -b %d' % target.routing[0].bridge_channel)
            elif len(target.routing) == 2:
                cmd += (' -B %d' % target.routing[0].bridge_channel)
                cmd += (' -T 0x%02x' % target.routing[1].address)
                cmd += (' -b %d' % target.routing[1].bridge_channel)
            else:
                raise RuntimeError('The impitool interface at most double '
                       'briding')

        cmd += (' -t 0x%02x' % target.ipmb_address)

        if self._session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += ' -P ""'
        elif self._session.auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += (' -U "%s"' % self._session._auth_username)
            cmd += (' -P "%s"' % self._session._auth_password)
        else:
            raise RuntimeError('Session type %d not supported' %
                    self._session.auth_type)

        cmd += (' %s' % ipmitool_cmd)
        cmd += (' 2>&1')
        log().debug('Run ipmitool "%s"', cmd)

        child = Popen(cmd, shell=True, stdout=PIPE)
        output = child.communicate()[0]

        log().debug('return with rc=%d, output was:\n%s', child.returncode,
                output)

        return output, child.returncode

