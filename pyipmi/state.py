from __future__ import annotations

from .msgs import Message


class DefaultProperties(object):
    def __init__(self) -> None:
        if hasattr(self, '__properties__'):
            for prop in self.__properties__:
                setattr(self, prop[0], None)


class ResponseDecoder(object):
    def __init__(self, rsp: Message | None = None) -> None:
        if rsp:
            self._from_response(rsp)


class State(DefaultProperties, ResponseDecoder):
    """This is a container that represents a state.

    The state can have default
    properties that are created by init.
    """

    def __init__(self, rsp: Message | None = None) -> None:
        DefaultProperties.__init__(self)
        ResponseDecoder.__init__(self, rsp)
