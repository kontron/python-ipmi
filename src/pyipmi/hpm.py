#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import array
from struct import unpack

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import  hpm
from pyipmi.utils import check_completion_code

PROPERTY_GENERAL_COMPONENT_PROPERTIES = 0
PROPERTY_CURENT_VERION = 1
PROPERTY_DESCRIPTION_STRING = 2
PROPERTY_ROLLBACK_FIRMWARE_VERSION = 3
PROPERTY_DEFERRED_UPGRADE_FIRMWARE_VERSION = 4

class Helper:
    def get_target_upgrade_capabilities(self, fn, fru_id=0):
        m = pyipmi.msgs.hpm.GetTargetUpgradeCapabilities()
        fn(m)
        check_completion_code(m.rsp.completion_code)

    def open_hpm_file(self, fn, filename):
        print filename
        image = UpgradeImage(filename)


class UpgradeImageHeaderRecord:
    def __init__(self, data=None):
        if data:
            self.signature = data[0:8]
            self.format_version = unpack("B", data[8])[0]
            self.device_id = unpack("B", data[9])[0]
            tmp = data[10:13]
#            self.manufacturer_id = unpack("BBB", data[9:12])[0:3]
            self.product_id = unpack("<H", data[13:15])[0]
            self.time = unpack("<L", data[15:19])[0]
            self.image_capabilities = unpack("B", data[19])[0]
            self.components = unpack("B", data[20])[0]
            self.selftest_timeout = unpack("B", data[21])[0]
            self.rollback_timeout = unpack("B", data[22])[0]
            self.inaccessibility_timeout = unpack("B", data[23])[0]
            self.earliest_compatible_revision = unpack("<H", data[24:26])[0]

            self.oem_data_length = unpack("<H", data[32:34])[0]

    def __str__(self):
        str = []
        str.append("HPM Upgrade Image header")
        str.append(" Signature:        %s" % self.signature)
        str.append(" Format Version:   %s" % self.format_version)
        str.append(" Device ID:        %s" % self.device_id)
        str.append(" Product ID:       %s" % self.product_id)
        str.append(" Time:             %s" % self.time)
        str.append(" Image Cap:        0x%02x" % self.image_capabilities)
        str.append(" Components:       0x%02x" % self.components)
        str.append(" Selftest Timeout: %s" % self.selftest_timeout)
        str.append(" Rollback Timeout: %s" % self.rollback_timeout)
        str.append(" Inacc. Timeout:   %s" % self.inaccessibility_timeout)
        str.append(" Earliest comp.:   %s" % self.earliest_compatible_revision)
        str.append(" OEM data len:     %s" % self.oem_data_length)
        return "\n".join(str)


ACTION_BACKUP_COMPONENT = 0x00
ACTION_PREPARE_COMPONENT = 0x01
ACTION_UPLOAD_FIRMWARE_IMAGE = 0x02

class UpgradeActionRecord:

    def __init__(self, data=None):
        if data:
            self.upgrade_action_type = unpack("B", data[0])[0]
            self.components = unpack("B", data[1])[0]
            if self.upgrade_action_type is ACTION_UPLOAD_FIRMWARE_IMAGE:
                pass

    def __str__(self):
        str = []
        str.append("Action Record:")
        str.append(" Action:     %s" % self.upgrade_action_type)
        str.append(" Components: %s" % self.components)
        return "\n".join(str)


class UpgradeImage:
    def __init__(self, filename=None):
        if filename:
            self._from_file(filename)

    def __str__(self):
        str = []
        return "\n".join(str)

    def _from_file(self, filename):

        try:
            f = open(filename, "r")
        except IOError:
            print 'Error open file "%s"' % filename

        # Upgrade Image Header
        header_data = f.read(34)
        self.image_header = UpgradeImageHeaderRecord(header_data)
        print self.image_header

        # OEM Information
        f.seek(34+self.image_header.oem_data_length)
        self.image_header_checksum = f.read(1)

        # Header Checksum
        offset = f.tell()

        # Upgrade Actions
        while True:
            print "offset=%d" %offset
            action_data = f.read(34)
            action_record = UpgradeActionRecord(action_data)
            print action_record

            f.seek(offset+30)
            firmware_length = unpack("<L", f.read(4))[0]
            print firmware_length
            f.seek(offset)

            break

        # image checksum
        # tbd
