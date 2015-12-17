#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
from nose.tools import raises

from pyipmi.errors import *

class TestErrors:
    @raises(DecodingError)
    def test_DecodingError(self):
        raise DecodingError()

    @raises(EncodingError)
    def test_EncodingError(self):
        raise EncodingError()

    @raises(TimeoutError)
    def test_TimeoutError(self):
        raise TimeoutError()

    @raises(CompletionCodeError)
    def test_CompletionCodeError(self):
        raise CompletionCodeError(cc=0x09)

    @raises(NotSupportedError)
    def test_NotSupportedError(self):
        raise NotSupportedError()

    @raises(DescriptionError)
    def test_DescriptionError(self):
        raise (DescriptionError)

    @raises(RetryError)
    def test_RetryError(self):
        raise (RetryError)

    @raises(DataNotFound)
    def test_DataNotFound(self):
        raise DataNotFound()

    @raises(HpmError)
    def test_HpmError_no_msg(self):
        raise HpmError()
