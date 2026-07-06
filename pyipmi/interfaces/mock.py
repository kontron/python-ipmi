from __future__ import annotations

from typing import Any

from .. import Target
from ..msgs import Message
from ..session import Session


class Mock(object):
    """This interface is used as mock."""

    NAME = 'mock'

    def __init__(self) -> None:
        pass

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def establish_session(self, session: Session) -> None:
        pass

    def is_ipmc_accessible(self, target: Target) -> Any:
        pass

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> Any:
        pass

    def send_and_receive(self, req: Message) -> Any:
        pass
