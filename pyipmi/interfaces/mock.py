"""A dummy interface for tests."""

from __future__ import annotations

from typing import Any

from .. import Target
from ..msgs import Message
from .base import Interface


class Mock(Interface):
    """A dummy interface for tests.

    It sends nothing and all methods return None. The tests replace the
    methods they need, e.g. with a ``MagicMock``.
    """

    NAME = 'mock'

    def __init__(self) -> None:
        """Create the interface, it has no options."""

    def is_target_accessible(self, target: Target) -> Any:
        """Do nothing, return None.

        Args:
            target: Not used.
        """

    def send_and_receive_raw(self, target: Target, lun: int, netfn: int,
                             raw_bytes: bytes) -> Any:
        """Do nothing, return None.

        Args:
            target: Not used.
            lun: Not used.
            netfn: Not used.
            raw_bytes: Not used.
        """

    def send_and_receive(self, req: Message) -> Any:
        """Do nothing, return None.

        Args:
            req: Not used.
        """
