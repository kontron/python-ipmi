class DecodingError(Exception):
    pass


class TimeoutError(Exception):
    pass


class CompletionCodeError(Exception):
    def __init__(self, cc):
        self.cc = cc


class NotSupportedError(Exception):
    pass


class DescriptionError(Exception):
    pass


class EncodingError(Exception):
    pass


