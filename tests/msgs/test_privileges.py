#!/usr/bin/env python

from pyipmi.msgs import constants
from pyipmi.msgs import privileges
from pyipmi.msgs.registry import DEFAULT_REGISTRY
from pyipmi.msgs.privileges import (ADMINISTRATOR, LOCAL_INTERFACE, NONE,
                                    OPERATOR, SYSTEM_INTERFACE, USER,
                                    required_privilege)

APP = constants.NETFN_APP
GROUP = constants.NETFN_GROUP_EXTENSION


def test_appendix_g():
    # samples of IPMI v2.0 Table G-1
    for (netfn, cmd, level) in (
            (APP, 0x01, USER),                          # Get Device ID
            (APP, 0x02, ADMINISTRATOR),                 # Cold Reset
            (APP, 0x34, USER),                          # Send Message
            (APP, 0x37, NONE),                          # Get System GUID
            (APP, 0x38, NONE),                          # Get Channel Auth Caps
            (APP, 0x3c, privileges.CALLBACK),           # Close Session
            (APP, 0x3f, OPERATOR),                      # Get AuthCode
            (APP, 0x52, OPERATOR),                      # Master Write-Read
            (constants.NETFN_CHASSIS, 0x02, OPERATOR),  # Chassis Control
            (constants.NETFN_CHASSIS, 0x0a, ADMINISTRATOR),
            (constants.NETFN_SENSOR_EVENT, 0x00, ADMINISTRATOR),
            (constants.NETFN_SENSOR_EVENT, 0x02, OPERATOR),  # Platform Event
            (constants.NETFN_SENSOR_EVENT, 0x13, OPERATOR),  # Get PEF Config
            (constants.NETFN_SENSOR_EVENT, 0x17, NONE),  # PET Acknowledge
            (constants.NETFN_STORAGE, 0x47, OPERATOR),  # Clear SEL
            (constants.NETFN_TRANSPORT, 0x01, ADMINISTRATOR),
            (constants.NETFN_TRANSPORT, 0x02, OPERATOR)):
        assert required_privilege(netfn, cmd) == level, (netfn, cmd)


def test_interface_only_commands():
    # the device SDR commands, Get Message: no session has them
    assert required_privilege(constants.NETFN_SENSOR_EVENT, 0x21) == \
        LOCAL_INTERFACE
    assert required_privilege(APP, 0x33) == SYSTEM_INTERFACE
    assert min(LOCAL_INTERFACE, SYSTEM_INTERFACE) > ADMINISTRATOR


def test_group_extensions():
    # PICMG HPM.1 Table 6-2 and VITA 46.11 Table 10.1.2-2
    assert required_privilege(GROUP, 0x2e, 0x00) == USER
    assert required_privilege(GROUP, 0x31, 0x00) == OPERATOR
    assert required_privilege(GROUP, 0x0a, 0x03) == ADMINISTRATOR
    assert required_privilege(GROUP, 0x03, 0x03) == OPERATOR
    # the same command of another group extension, unknown ones
    assert required_privilege(GROUP, 0x0a, 0x00) == OPERATOR
    assert required_privilege(GROUP, 0x01, 0xdc) is None


def test_response_and_unknown():
    # the network function of the response
    assert required_privilege(constants.NETFN_STORAGE | 1, 0x47) == OPERATOR
    # the group is ignored for the other network functions
    assert required_privilege(APP, 0x01, 0x03) == USER
    # OEM commands are defined by the OEM
    assert required_privilege(0x30, 0x01) is None


# the requests without a level: their specifications (DCMI, PICMG 3.0 and
# MicroTCA, HPM.2) were not at hand when the levels were added; give one
# when it is checked
UNCHECKED = {
    # DCMI
    'ActivateDeactivatePowerLimit', 'GetAssetTag', 'GetDcmiCapabilities',
    'GetDcmiConfigurationParameters', 'GetDcmiSensorInfo',
    'GetManagementControllerIdString', 'GetPowerLimit', 'GetPowerReading',
    'GetTemperatureReadings', 'GetThermalLimit', 'SetAssetTag',
    'SetDcmiConfigurationParameters', 'SetManagementControllerIdString',
    'SetPowerLimit', 'SetThermalLimit',
    # PICMG 3.0, MicroTCA
    'GetPowerChannelStatus', 'GetTelcoAlarmCapability', 'SendPmHeartbeat',
    'SendPowerChannelControl', 'SetSignalingClass',
    # PICMG HPM.2
    'GetLanAttachCapabilities',
}


def requests():
    return {name[:-3]: cls for (name, cls) in DEFAULT_REGISTRY.registry.items()
            if isinstance(name, str) and name.endswith('Req')}


def test_every_request_has_a_level():
    # a new request message gets its level with its definition
    missing = sorted(name for (name, cls) in requests().items()
                     if cls.__privilege__ is None and name not in UNCHECKED)
    assert missing == []
    assert all(cls.__privilege__ in privileges.NAMES
               for cls in requests().values()
               if cls.__privilege__ is not None)
    # the list of exceptions shrinks
    assert UNCHECKED <= set(requests())
    assert all(requests()[name].__privilege__ is None for name in UNCHECKED)


def test_without_messages():
    # a command gets its level from its message once there is one
    registered = {key for key in DEFAULT_REGISTRY.registry
                  if isinstance(key, tuple)}
    assert not set(privileges.WITHOUT_MESSAGES) & registered
    assert all(level in privileges.NAMES
               for level in privileges.WITHOUT_MESSAGES.values())
