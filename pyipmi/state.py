

from builtins import object

class DefaultProperties(object):
    def __init__(self):
        if hasattr(self, '__properties__'):
            for p in self.__properties__:
                setattr(self, p[0], None)

class ResponseDecoder(object):
    def __init__(self, rsp=None):
        if rsp:
            self._from_response(rsp)

class State(DefaultProperties, ResponseDecoder):
    """This is a container that represents a state. The state can have default
    properties that are created by init.
    """
    def __init__(self, rsp=None):
        DefaultProperties.__init__(self)
        ResponseDecoder.__init__(self, rsp)
