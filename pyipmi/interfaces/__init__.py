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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from .ipmitool import Ipmitool
from .aardvark import Aardvark
from .mock import Mock

INTERFACES = [
        Ipmitool,
        Aardvark,
        Mock,
]

def create_interface(interface, *args, **kwargs):
    for intf in INTERFACES:
        if intf.NAME == interface:
            intf = intf(*args, **kwargs)
            return intf

    raise RuntimeError('unknown interface with name %s' % interface)

