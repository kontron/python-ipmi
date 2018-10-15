# Copyright (c) 2014  Kontron Europe GmbH
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA


from functools import partial
from ..errors import DescriptionError


class MessageRegistry(object):
    def __init__(self):
        self.registry = dict()

    def register_class(self, cls):
        # some sanity checks
        # (1) class name has to end in Req or Rsp
        if cls.__name__[-3:] not in ('Req', 'Rsp'):
            raise DescriptionError('Class name has to end in Req or Rsp')
        # (2) mandantory fields
        for attr in ('__netfn__', '__cmdid__', '__default_lun__',
                     '__group_extension__'):
            if not hasattr(cls, attr):
                raise DescriptionError('Class has to have attribute "%s"' %
                                       attr)
        # (3) netfn lsb has to be 0 for Req and 1 for Rsp
        if cls.__name__.endswith('Req') and cls.__netfn__ & 1 != 0:
            raise DescriptionError('LSB of NetFN of a Request must be 0')

        if cls.__name__.endswith('Rsp') and cls.__netfn__ & 1 != 1:
            raise DescriptionError('LSB of NetFN of a Request must be 1')

        # (4) must not be registered before
        if cls.__name__ in self.registry:
            raise DescriptionError('Message %s already registered' %
                                   cls.__name__)
        msg_id = (cls.__netfn__, cls.__cmdid__, cls.__group_extension__)
        if msg_id in self.registry:
            raise DescriptionError('Message (%d,%d,%d) already registered (%s)'
                                   % (msg_id[0], msg_id[1], msg_id[2],
                                      self.registry[msg_id]))

        # register name
        self.registry[cls.__name__] = cls
        # register (netfn, cmdid, group_extension) tuple
        self.registry[msg_id] = cls

        # register
        return cls

    def create(self, netfn, cmdid, group_extension, *args, **kwargs):
        return self.registry[(netfn, cmdid, group_extension)](*args, **kwargs)

    def create_response(self, req):
        return self.create(self, req.netfn + 1, req.cmdid, req.group_extension)

    def create_request_by_name(self, name, *args, **kwargs):
        return self.registry[name + "Req"](*args, **kwargs)

    def create_response_by_name(self, name, *args, **kwargs):
        return self.registry[name + "Rsp"](*args, **kwargs)


DEFAULT_REGISTRY = MessageRegistry()
register_message_class = partial(MessageRegistry.register_class,
                                 DEFAULT_REGISTRY)
create_message = partial(MessageRegistry.create, DEFAULT_REGISTRY)
create_response_message = partial(MessageRegistry.create_response,
                                  DEFAULT_REGISTRY)
create_request_by_name = partial(MessageRegistry.create_request_by_name,
                                 DEFAULT_REGISTRY)
create_response_by_name = partial(MessageRegistry.create_response_by_name,
                                  DEFAULT_REGISTRY)
