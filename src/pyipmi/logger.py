import logging

def log():
    return logging.getLogger('pyipmi')

def add_log_handler(handler):
    log().addHandler(handler)

def set_log_level(level):
    log().setLevel(level)

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

add_log_handler(NullHandler())
