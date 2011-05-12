class DecodingError(Exception):
    pass


class EncodingError(Exception):
    pass


class TimeoutError(Exception):
    pass


class CompletionCodeError(Exception):
    def __init__(self, cc):
        self.cc = cc

    def __str__(self):
        return "%s cc=0x%02x" % (self.__class__.__name__, self.cc)

class NotSupportedError(Exception):
    pass


class DescriptionError(Exception):
    pass
