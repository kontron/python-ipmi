class DecodingError(Exception):
    """Error on message decoding."""
    pass


class EncodingError(Exception):
    """Error on message encoding."""
    pass


class TimeoutError(Exception):
    """Timeout occurred."""
    pass


class CompletionCodeError(Exception):
    """IPMI completion code not OK."""
    def __init__(self, cc):
        self.cc = cc

    def __str__(self):
        return "%s cc=0x%02x" % (self.__class__.__name__, self.cc)

class NotSupportedError(Exception):
    """Not supported yet."""
    pass


class DescriptionError(Exception):
    """Message description incorrect."""
    pass


class RetryError(Exception):
    """Maxium number of retries exceeded."""
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        if self.msg:
            return "%s msg=%s" % (self.__class__.__name__, self.msg)
        else:
            return "%s" % (self.__class__.__name__)
