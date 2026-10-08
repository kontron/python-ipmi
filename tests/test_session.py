#!/usr/bin/env python3

import pytest

from pyipmi.session import Session


def test_session_object():
    session = Session()
    assert session.sid == 0
    assert session.sequence_number == 0
    assert session.activated is False


def test_session_interface():
    session = Session()
    assert session.interface is None
    # set to something to check setter/getter
    session.interface = True
    assert session.interface is True


def test_session_auth_type():
    session = Session()
    assert session.auth_type == session.AUTH_TYPE_NONE
    session.auth_type = session.AUTH_TYPE_OEM
    assert session.auth_type == session.AUTH_TYPE_OEM


def test_session_increment_sequence_number():
    session = Session()
    assert session.sequence_number == 0
    session.increment_sequence_number()
    assert session.sequence_number == 1
    session.increment_sequence_number()
    assert session.sequence_number == 2

    # test wrap around
    session.sequence_number = 0xffffffff
    session.increment_sequence_number()
    assert session.sequence_number == 1


def test_set_priv_level():
    session = Session()
    assert session.priv_level == session.PRIV_LEVEL_ADMINISTRATOR
    session.set_priv_level('user')
    assert session.priv_level == session.PRIV_LEVEL_USER
    session.set_priv_level('operator')
    assert session.priv_level == session.PRIV_LEVEL_OPERATOR
    session.set_priv_level('administrator')
    assert session.priv_level == session.PRIV_LEVEL_ADMINISTRATOR


def test_string():
    session = Session()
    str(session)


def test_set_priv_level_ignores_case():
    session = Session()
    session.set_priv_level('USER')
    assert session.priv_level == session.PRIV_LEVEL_USER


@pytest.mark.parametrize('level', ['oem', 'admin', ''])
def test_set_priv_level_invalid(level):
    session = Session()
    with pytest.raises(ValueError, match='unknown privilege level'):
        session.set_priv_level(level)
    assert session.priv_level == session.PRIV_LEVEL_ADMINISTRATOR
