"""Parser of ipmitool.py as input for argparse-manpage.

The short description is already in the NAME section of the man page, the
DESCRIPTION section comes from ipmitool.py.1.include.
"""

import argparse

from pyipmi.ipmitool import build_parser as _build_parser


def build_parser() -> argparse.ArgumentParser:
    parser = _build_parser()
    parser.description = None
    return parser
