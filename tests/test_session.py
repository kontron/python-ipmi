from pyipmi.session import Session
from subprocess import Popen, PIPE


def test_auth_username():
    username = 'ad$_min'
    password = 'password'
    session = Session()
    session.set_auth_type_user(username, password)
    child = Popen(f"echo {session.auth_username}", shell=True, stdout=PIPE)
    output = child.communicate()[0].decode('utf-8').strip()
    assert output == username


def test_auth_password():
    username = 'admin'
    password = 'pass$_word'
    session = Session()
    session.set_auth_type_user(username, password)
    child = Popen(f"echo {session.auth_password}", shell=True, stdout=PIPE)
    output = child.communicate()[0].decode('utf-8').strip()
    assert output == password
