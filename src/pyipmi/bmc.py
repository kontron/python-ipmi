#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from errors import DecodingError, CompletionCodeError
from msgs import bmc, check_completion_code

class Helper:
    def get_device_id(self, fn):
        m = bmc.GetDeviceId()
        fn(m)
        check_completion_code(m.rsp.completion_code)
        return DeviceId(m.rsp)

    def cold_reset(self, fn):
        m = bmc.ColdReset()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def warm_reset(self, fn):
        m = bmc.WarmReset()
        fn(m)
        check_completion_code(m.rsp.completion_code)

class DeviceId:
    def __init__(self, rsp):
        if rsp:
            self.from_response(rsp)

    def __str__(self):
        s = 'Device ID: %d' % self.id
        s+= ' revision: %d' % self.revision
        s+= ' available: %d' % self.available
        s+= ' fw version: %d.%d' % (self.major_fw_revision, self.minor_fw_revision)
        s+= ' ipmi: %d' % self.ipmi_version
        s+= ' manuf: %d' % self.manufacturer_id
        s+= ' product: %d' % self.product_id
        return s

    def from_response(self, rsp):
        self.id = rsp.device_id
        self.revision = rsp.device_revision.device_revision
        self.provides_sdrs = rsp.device_revision.provides_device_sdrs
        self.available = rsp.firmware_revision.device_available
        self.major_fw_revision = rsp.firmware_revision.major_revision
        self.minor_fw_revision = rsp.minor_firmware_revision
        self.ipmi_version = rsp.ipmi_version

        self.support_sensor = rsp.additional_support.sensor
        self.support_sdrr = rsp.additional_support.sdr_repository
        self.support_sel = rsp.additional_support.sel
        self.support_fru = rsp.additional_support.fru_inventory
        self.support_event_receiver = rsp.additional_support.ipmb_event_receiver
        self.support_event_generator = rsp.additional_support.ipmb_event_generator
        self.support_bridge = rsp.additional_support.bridge
        self.support_chassis = rsp.additional_support.chassis

        self.manufacturer_id = rsp.manufacturer_id
        self.product_id = rsp.product_id
        self.aux0 = rsp.auxiliary_0
        self.aux1 = rsp.auxiliary_1
        self.aux2 = rsp.auxiliary_2
        self.aux3 = rsp.auxiliary_3
