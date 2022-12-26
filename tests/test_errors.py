#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from pyipmi.errors import (DecodingError, EncodingError, CompletionCodeError,
                           NotSupportedError, DescriptionError, RetryError,
                           DataNotFound, HpmError)


def test_DecodingError():
    with pytest.raises(DecodingError):
        raise DecodingError()


def test_EncodingError():
    with pytest.raises(EncodingError):
        raise EncodingError()


def test_CompletionCodeError():
    with pytest.raises(CompletionCodeError):
        raise CompletionCodeError(cc=0x09)


def test_NotSupportedError():
    with pytest.raises(NotSupportedError):
        raise NotSupportedError()


def test_DescriptionError():
    with pytest.raises(DescriptionError):
        raise DescriptionError()


def test_RetryError():
    with pytest.raises(RetryError):
        raise RetryError()


def test_DataNotFound():
    with pytest.raises(DataNotFound):
        raise DataNotFound()


def test_HpmError_no_msg():
    with pytest.raises(HpmError):
        raise HpmError()
