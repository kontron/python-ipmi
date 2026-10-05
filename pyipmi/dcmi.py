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

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .constants import (ENTITY_ID_DCMI_AIR_INLET, ENTITY_ID_DCMI_CPU,
                        ENTITY_ID_DCMI_BASEBOARD)
from .msgs import Message, create_request_by_name
from .utils import check_rsp_completion_code


PARAM_SUPPORTED_DCMI_CAPABILITIES = 1
PARAM_MANDATORY_PLATFORM_ATTRIBUTES = 2
PARAM_OPTIONAL_PLATFORM_ATTRIBUTES = 3
PARAM_MANAGEABILITY_ACCESS_ATTRIBUTES = 4
PARAM_ENHANCED_SYSTEM_POWER_STATISTICS_ATTRIBUTES = 5

CONF_PARAM_ACTIVATE_DHCP = 1
CONF_PARAM_DISCOVERY_CONFIGURATION = 2
CONF_PARAM_DHCP_TIMING_1 = 3
CONF_PARAM_DHCP_TIMING_2 = 4
CONF_PARAM_DHCP_TIMING_3 = 5

POWER_LIMIT_EXCEPTION_NO_ACTION = 0x00
POWER_LIMIT_EXCEPTION_HARD_POWER_OFF = 0x01
POWER_LIMIT_EXCEPTION_LOG_EVENT_TO_SEL = 0x11

# maximum number of bytes per asset tag/identifier string request
MAX_STRING_CHUNK_SIZE = 16
MAX_ASSET_TAG_LENGTH = 64
MAX_MC_ID_STRING_LENGTH = 64

DCMI_ENTITIES = (ENTITY_ID_DCMI_AIR_INLET, ENTITY_ID_DCMI_CPU,
                 ENTITY_ID_DCMI_BASEBOARD)


class Dcmi:
    def get_dcmi_capabilities(self, selector: int) -> Message:
        rsp = self.send_message_with_name('GetDcmiCapabilities',
                                          parameter_selector=selector)
        return rsp

    def get_power_reading(self, mode: int, attributes: int = 0) -> Message:
        rsp = self.send_message_with_name('GetPowerReading',
                                          mode=mode, attributes=attributes)
        return rsp

    def _get_all_instances(self, name: str, entity_id: int,
                           decode: Callable[[Message], list[tuple[int, Any]]]
                           ) -> list[Any]:
        """Request all instances of an entity.

        A response contains at most 8 instances, so the following instances
        are requested until all are received. `decode` returns a list of
        (key, item) tuples of a response. Items with an already received key
        are ignored in case the BMC counts the instance start differently.
        """
        keys: list[int] = []
        items: list[Any] = []
        start = 0
        while True:
            rsp = self.send_message_with_name(name,
                                              sensor_type=1,
                                              entity_id=entity_id,
                                              entity_instance=0,
                                              entity_instance_start=start)
            received = decode(rsp)
            new = [(k, i) for (k, i) in received if k not in keys]
            for (k, i) in new:
                keys.append(k)
                items.append(i)
            if not new or len(items) >= rsp.total_number_of_instances:
                break
            start += len(received)
        return items

    def get_dcmi_sensor_record_ids(self) -> list[int]:
        def decode(rsp: Message) -> list[tuple[int, int]]:
            # convert the returned raw data in a list of SDR record IDs
            ids = [msb << 8 | lsb for (lsb, msb) in
                   zip(rsp.record_ids[0::2], rsp.record_ids[1::2],
                       strict=False)]
            return [(i, i) for i in ids]

        record_ids = list()
        for entity_id in DCMI_ENTITIES:
            record_ids.extend(self._get_all_instances('GetDcmiSensorInfo',
                                                      entity_id, decode))
        return record_ids

    def get_temperature_readings(self, entity_id: int
                                 ) -> list[tuple[int, int]]:
        """Return the temperature readings of all instances of an entity.

        Returns a list of (entity instance, temperature in degree Celsius)
        tuples.
        """
        def decode(rsp: Message) -> list[tuple[int, tuple[int, int]]]:
            readings = []
            for (temp, instance) in zip(rsp.readings[0::2],
                                        rsp.readings[1::2], strict=False):
                value = temp & 0x7f
                if temp & 0x80:
                    value = -value
                readings.append((instance, (instance, value)))
            return readings

        return self._get_all_instances('GetTemperatureReadings', entity_id,
                                       decode)

    def get_power_limit(self) -> Message:
        return self.send_message_with_name('GetPowerLimit')

    def set_power_limit(self, power_limit: int, correction_time_limit: int,
                        statistics_sampling_period: int,
                        exception_actions: int =
                        POWER_LIMIT_EXCEPTION_NO_ACTION) -> None:
        """Set the power limit.

        power_limit: in watts
        correction_time_limit: in milliseconds
        statistics_sampling_period: in seconds
        """
        self.send_message_with_name(
                'SetPowerLimit',
                exception_actions=exception_actions,
                power_limit=power_limit,
                correction_time_limit=correction_time_limit,
                statistics_sampling_period=statistics_sampling_period)

    def activate_power_limit(self) -> None:
        self.send_message_with_name('ActivateDeactivatePowerLimit',
                                    activation=1)

    def deactivate_power_limit(self) -> None:
        self.send_message_with_name('ActivateDeactivatePowerLimit',
                                    activation=0)

    def get_thermal_limit(self, entity_id: int,
                          entity_instance: int) -> Message:
        return self.send_message_with_name('GetThermalLimit',
                                           entity_id=entity_id,
                                           entity_instance=entity_instance)

    def set_thermal_limit(self, entity_id: int, entity_instance: int,
                          temperature_limit: int, exception_time: int,
                          enable: bool = True, hard_power_off: bool = False,
                          log_event_to_sel: bool = False) -> None:
        """Set the thermal limit.

        temperature_limit: in degree Celsius
        exception_time: in seconds
        """
        req = create_request_by_name('SetThermalLimit')
        req.entity_id = entity_id
        req.entity_instance = entity_instance
        req.exception_actions.enable = int(enable)
        req.exception_actions.hard_power_off = int(hard_power_off)
        req.exception_actions.log_event_to_sel = int(log_event_to_sel)
        req.temperature_limit = temperature_limit
        req.exception_time = exception_time
        rsp = self.send_message(req)
        check_rsp_completion_code(rsp)

    def get_dcmi_configuration_parameters(self, selector: int,
                                          set_selector: int = 0) -> Message:
        return self.send_message_with_name('GetDcmiConfigurationParameters',
                                           parameter_selector=selector,
                                           set_selector=set_selector)

    def set_dcmi_configuration_parameters(self, selector: int, data: bytes,
                                          set_selector: int = 0) -> None:
        self.send_message_with_name('SetDcmiConfigurationParameters',
                                    parameter_selector=selector,
                                    set_selector=set_selector,
                                    parameter_data=data)

    def _get_dcmi_string(self, name: str, length_request_size: int) -> bytes:
        # the first request is only used to get the total length
        rsp = self.send_message_with_name(name, offset=0,
                                          number_of_bytes=length_request_size)
        total_length = rsp.total_length
        data = b''
        while len(data) < total_length:
            count = min(MAX_STRING_CHUNK_SIZE, total_length - len(data))
            rsp = self.send_message_with_name(name, offset=len(data),
                                              number_of_bytes=count)
            chunk = rsp.data.tobytes()
            if not chunk:
                break
            data += chunk[:count]
        return data

    def _set_dcmi_string(self, name: str, data: bytes) -> None:
        for offset in range(0, len(data), MAX_STRING_CHUNK_SIZE):
            chunk = data[offset:offset + MAX_STRING_CHUNK_SIZE]
            self.send_message_with_name(name, offset=offset,
                                        number_of_bytes=len(chunk),
                                        data=chunk)

    def get_asset_tag(self) -> str:
        data = self._get_dcmi_string('GetAssetTag', 0)
        return data.decode('utf-8', errors='replace')

    def set_asset_tag(self, asset_tag: str) -> None:
        data = asset_tag.encode('utf-8')
        if len(data) > MAX_ASSET_TAG_LENGTH:
            raise ValueError('asset tag is longer than %d bytes'
                             % MAX_ASSET_TAG_LENGTH)
        self._set_dcmi_string('SetAssetTag', data)

    def get_management_controller_id_string(self) -> str:
        data = self._get_dcmi_string('GetManagementControllerIdString', 1)
        # the string is null terminated
        return data.split(b'\x00', 1)[0].decode('ascii', errors='replace')

    def set_management_controller_id_string(self, id_string: str) -> None:
        # the string has to be null terminated
        data = id_string.encode('ascii') + b'\x00'
        if len(data) > MAX_MC_ID_STRING_LENGTH:
            raise ValueError('identifier string is longer than %d bytes'
                             % (MAX_MC_ID_STRING_LENGTH - 1))
        self._set_dcmi_string('SetManagementControllerIdString', data)
