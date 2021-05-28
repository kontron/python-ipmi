class Mock(object):
    """This interface is used as mock."""

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
