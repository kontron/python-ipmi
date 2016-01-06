#!/usr/bin/env python
#-*- coding: utf-8 -*-

from mock import MagicMock, call
from nose.tools import eq_

from pyipmi.helper import *

def test_clear_repository_helper():
    reserve_fn = MagicMock()
    reserve_fn.return_value = (0x1234)

    clear_fn = MagicMock()
    clear_fn.side_effect = [
        ERASURE_COMPLETED,
        ERASURE_IN_PROGRESS,
        ERASURE_COMPLETED,
    ]

    clear_repository_helper(reserve_fn, clear_fn)

    clear_calls = [
        call(INITIATE_ERASE, 0x1234),
        call(GET_ERASE_STATUS, 0x1234),
        call(GET_ERASE_STATUS, 0x1234),
    ]
    clear_fn.assert_has_calls(clear_calls)
    eq_(clear_fn.call_count, 3)
