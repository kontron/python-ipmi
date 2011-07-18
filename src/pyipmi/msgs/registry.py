from functools import partial
from pyipmi.errors import DescriptionError

class MessageRegistry:
    def __init__(self):
        self.registry = dict()

    def register_class(self, cls):
        # some sanity checks
        # (1) class name has to end in Req or Rsp
        if cls.__name__[-3:] not in ('Req', 'Rsp'):
            raise DescriptionError('Class name has to end in Req or Rsp')
        # (2) mandantory fields
        for attr in ('__cmdid__', '__netfn__', '__default_lun__'):
            if not hasattr(cls, attr):
                raise DescriptionError('Class has to have attribute "%s"' %
                        attr)
        # (3) netfn lsb has to be 0 for Req and 1 for Rsp
        if cls.__name__.endswith('Req') and cls.__netfn__ & 1 != 0:
            raise DescriptionError('LSB of NetFN of a Request must be 0')

        if cls.__name__.endswith('Rsp') and cls.__netfn__ & 1 != 1:
            raise DescriptionError('LSB of NetFN of a Request must be 1')

        # register name
        self.registry[cls.__name__] = cls
        # register (netfn, cmdid) tuple
        self.registry[(cls.__cmdid__, cls.__netfn__)] = cls

        # register
        return cls

    def create(self, netfn, cmdid, *args, **kwargs):
        return self.registry[(netfn, cmdid)](*args, **kwargs)

    def create_request_by_name(self, name, *args, **kwargs):
        return self.registry[name + "Req"](*args, **kwargs)

    def create_response_by_name(self, name, *args, **kwargs):
        return self.registry[name + "Rsp"](*args, **kwargs)

DEFAULT_REGISTRY = MessageRegistry()
register_message_class = partial(MessageRegistry.register_class,
        DEFAULT_REGISTRY)
create_message = partial(MessageRegistry.create, DEFAULT_REGISTRY)
create_request_by_name = partial(MessageRegistry.create_request_by_name,
        DEFAULT_REGISTRY)
create_response_by_name = partial(MessageRegistry.create_response_by_name,
        DEFAULT_REGISTRY)
