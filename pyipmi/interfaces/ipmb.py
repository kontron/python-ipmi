# Copyright (c) 2015  Kontron Europe GmbH
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

from builtins import object

import array


def checksum(data):
    csum = 0
    for b in data:
        csum += b
    return -csum % 256


class IpmbHeader(object):
    def __init__(self):
        self.rs_sa = None
        self.rs_lun = None
        self.rq_sa = None
        self.rq_lun = None
        self.netfn = None
        self.cmd_id = None

    def encode(self):
        data = array.array('B')
        data.append(self.netfn << 2 | self.rs_lun)
        data.append(checksum((self.rs_sa, data[0])))
        data.append(self.rq_sa)
        data.append(self.rq_seq << 2 | self.rq_lun)
        data.append(self.cmd_id)
        return data

