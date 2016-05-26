

from builtins import object

class Mock(object):
    """This interface uses the ipmitool raw command to "emulate" a RMCP
    session.

    It uses the session information to assemble the correct ipmitool
    parameters. Therefore, a session has to be established before any request
    can be sent.
    """

    NAME = 'mock'

    def __init__(self):
        pass

    def establish_session(self, session):
        pass

    def is_ipmc_accessible(self, target):
        pass

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        pass

    def send_and_receive(self, req):
        pass
