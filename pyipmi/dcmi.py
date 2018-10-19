# Copyright (c) 2018  Kontron Europe GmbH
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

from .constants import (ENTITY_ID_DCMI_AIR_INLET, ENTITY_ID_DCMI_CPU,
                        ENTITY_ID_DCMI_BASEBOARD)


PARAM_SUPPORTED_DCMI_CAPABILITIES = 1
PARAM_MANDATORY_PLATFORM_ATTRIBUTES = 2
PARAM_OPTIONAL_PLATFORM_ATTRIBUTES = 3
PARAM_MANAGEABILITY_ACCESS_ATTRIBUTES = 4
PARAM_ENHANCED_SYSTEM_POWER_STATISTICS_ATTRIBUTES = 5


class Dcmi(object):
    def get_dcmi_capabilities(self, selector):
        rsp = self.send_message_with_name('GetDcmiCapabilities',
                                          parameter_selector=selector)
        return rsp

    def get_power_reading(self, mode, attributes=0):
        rsp = self.send_message_with_name('GetPowerReading',
                                          mode=mode, attributes=attributes)
        return rsp

    def get_dcmi_sensor_record_ids(self):

        record_ids = list()

        DCMI_ENTITIES = (ENTITY_ID_DCMI_AIR_INLET, ENTITY_ID_DCMI_CPU,
                         ENTITY_ID_DCMI_BASEBOARD)

        for entity_id in DCMI_ENTITIES:
            rsp = self.send_message_with_name('GetDcmiSensorInfo',
                                              sensor_type=1,
                                              entity_id=entity_id,
                                              entity_instance=0,
                                              entity_instance_start=0)
            # convert the returned raw data in a list of SDR record IDs
            ids = [msb << 8 | lsb for (lsb, msb) in
                   zip(rsp.record_ids, rsp.record_ids[1:])[::2]]
            record_ids.extend(ids)

        return record_ids
