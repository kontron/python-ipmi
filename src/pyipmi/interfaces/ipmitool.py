#
# Kontron Ipmitool Interface
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

    def send_and_receive(self, target, msg):
        """Sends an IPMI request message and waits for its response.

        `msg` is a IPMI Message containing both the request and response.
        """

        log().debug('IPMI Request [%s]', msg.req)

        cmd = ('-l %d raw 0x%02x 0x%02x' % (msg.LUN, msg.NETFN, msg.CMDID))
        for byte in msg.req.encode():
            cmd += ' 0x%02x' % ord(byte)
        
        output, rc = self._run_ipmitool(target, cmd)
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
            output = output.replace('\n','').replace('\r','').strip()
            if len(output):
                for x in output.split(' '):
                    data.append(chr(int(x, 16)))
        
        msg.rsp.decode(data.tostring())
        log().debug('IPMI Response [%s])', msg.rsp)
 
    def _run_ipmitool(self, target, ipmitool_cmd):
        """Legacy call of ipmitool (will be removed in future).
        """

        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I lan')
        cmd += (' -H %s' % self._session._rmcp_host)

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

        cmd += (' -t 0x%02x' % target.target_address)

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

