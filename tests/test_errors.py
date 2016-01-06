#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import raises

from pyipmi.errors import *

@raises(DecodingError)
def test_DecodingError():
    raise DecodingError()

@raises(EncodingError)
def test_EncodingError():
    raise EncodingError()

@raises(TimeoutError)
def test_TimeoutError():
    raise TimeoutError()

@raises(CompletionCodeError)
def test_CompletionCodeError():
    raise CompletionCodeError(cc=0x09)

@raises(NotSupportedError)
def test_NotSupportedError():
    raise NotSupportedError()

@raises(DescriptionError)
def test_DescriptionError():
    raise (DescriptionError)

@raises(RetryError)
def test_RetryError():
    raise (RetryError)

@raises(DataNotFound)
def test_DataNotFound():
    raise DataNotFound()

@raises(HpmError)
def test_HpmError_no_msg():
    raise HpmError()
