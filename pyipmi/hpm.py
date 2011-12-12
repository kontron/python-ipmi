#
# pyimpi
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import os
import codecs
import array
import struct
import collections
import hashlib

from pyipmi.errors import DecodingError, CompletionCodeError
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import constants
from pyipmi.utils import check_completion_code, bcd_search


PROPERTY_GENERAL_PROPERTIES = 0
PROPERTY_CURRENT_VERSION = 1
PROPERTY_DESCRIPTION_STRING = 2
PROPERTY_ROLLBACK_VERSION = 3
PROPERTY_DEFERRED_VERSION = 4

ACTION_BACKUP_COMPONENT = 0x00
ACTION_PREPARE_COMPONENT = 0x01
ACTION_UPLOAD_FIRMWARE_IMAGE = 0x02


class Hpm:
    def get_target_upgrade_capabilities(self):
        req = create_request_by_name('GetTargetUpgradeCapabilities')
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)
        return TargetUpgradeCapabilities(rsp)

    def get_component_properties(self, component_id):
        """Return ComponentProperties()
        """
        PROPERTIES = [
            PROPERTY_GENERAL_PROPERTIES,
            PROPERTY_CURRENT_VERSION,
            PROPERTY_DESCRIPTION_STRING,
            PROPERTY_ROLLBACK_VERSION,
            PROPERTY_DEFERRED_VERSION,
        ]

        req = create_request_by_name('GetComponentProperties')
        req.id = component_id
        properties = ComponentProperties()
        for p_id in PROPERTIES:
            req.selector = p_id
            rsp = self.send_message(req)
            if rsp.completion_code == constants.CC_OK:
                properties.decode_from_response(p_id, rsp.data)
        return properties

    def find_component_id_by_descriptor(self, descriptor):
        caps = self.get_target_upgrade_capabilities()
        for component_id in caps.components:
            properties = self.get_component_properties(component_id)
            if properties.description is not None:
                if properties.description == descriptor:
                    break
        return component_id

    def open_hpm_file(self, filename):
        return UpgradeImage(filename)

    def query_selftest_result(self):
        raise NotImplementedError()

    def upload_component_firmware(self):
        raise NotImplementedError()


class TargetUpgradeCapabilities:
    def __init__(self, rsp=None):
        if rsp:
            self._from_response(rsp)

    def __str__(self):
        str = []
        str.append("HPM target upgrade capabilities")
        return "\n".join(str)

    def _from_response(self, rsp):
        self.components = []
        for i in range(8):
            if rsp.component_present & (1<<i):
                self.components.append(i)

VERSION_FIELD_LEN = 6
class VersionField:
    def __init__(self, data=None):
        self.major = None
        self.minor = None
        if data:
            if isinstance(data, str):
                data = array.array('c', [chr(c)for c in [ord(c) for c in data]])
            self.version = self._decode_version_string(data[0:2])
            self.auxiliary = data[2:6]

    def __str__(self):
        str = []
        str.append('%s' % (self.version))
        return '\n'.join(str)

    def _decode_version_string(self, data):
        """`data` is array.array
        """
        self.major = data[0]
        self.minor = data[1]

        if data[1] is not 255:
            self.minor = data[1:2].tostring().decode('bcd+')

    def version_to_string(self):
        return ''.join("%s.%s" % (self.major, self.minor))


codecs.register(bcd_search)

class ComponentProperties:

    def __init__(self):
        self.general_properties = None
        self.current_version = None
        self.rollback_version = None
        self.deferred_version = None
        self.description = None

    def decode_from_response(self, id, data):
        """
        `id` is component id
        `data` is data as array
        """
        self.id = id
        if id is PROPERTY_GENERAL_PROPERTIES:
            ROLLBACK_SUPPORT_MASK = 0x03
            PREPARATION_SUPPORT_MASK = 0x04
            COMPARISON_SUPPORT_MASK = 0x08
            DEFERRED_ACTIVATION_SUPPORT_MASK = 0x10
            PAYLOAD_COLD_RESET_REQ_SUPPORT_MASK = 0x20

            support = []
            cap = data[0]
            if cap & ROLLBACK_SUPPORT_MASK == 0:
                support.append('rollback_backup_not_supported')
            elif cap & ROLLBACK_SUPPORT_MASK == 1:
                support.append('rollback_is_supported')
            elif cap & ROLLBACK_SUPPORT_MASK == 2:
                support.append('rollback_is_supported')
            elif cap & ROLLBACK_SUPPORT_MASK == 3:
                support.append('reserved')
            if cap & PREPARATION_SUPPORT_MASK:
                support.append('prepartion')
            if cap & COMPARISON_SUPPORT_MASK:
                support.append('comparison')
            if cap & DEFERRED_ACTIVATION_SUPPORT_MASK:
                support.append('deferred_activation')
            if cap & PAYLOAD_COLD_RESET_REQ_SUPPORT_MASK:
                support.append('payload_cold_reset_required')

            self.general_properties = support

        elif id is PROPERTY_CURRENT_VERSION:
            self.current_version = VersionField(data)
        elif id is PROPERTY_DESCRIPTION_STRING:
            # remove trailing '\0'
            descr =  data.tostring().replace('\0', '')
            self.description = descr
        elif id is PROPERTY_ROLLBACK_VERSION:
            self.rollback_version  = VersionField(data)
        elif id is PROPERTY_DEFERRED_VERSION:
            self.deferred_version = VersionField(data)


ImageHeader = collections.namedtuple('ImageHeader', ['field_name', 'format', 'start', 'len'])

class UpgradeImageHeaderRecord:
    def __init__(self, data=None):
        FORMAT  = [
            ImageHeader('format_version', 'B', 8, 1),
            ImageHeader('device_id', 'B', 9, 1),
            ImageHeader('product_id', '<H', 13, 2),
            ImageHeader('time', '<L', 15, 4),
            ImageHeader('capabilities', 'B', 19,1),
            ImageHeader('components', 'B',  20, 1),
            ImageHeader('selftest_timeout', 'B', 21, 1),
            ImageHeader('rollback_timeout', 'B', 22, 1),
            ImageHeader('inaccessibility_timeout', 'B', 23, 1),
            ImageHeader('earliest_compatible_revision', '<H', 24, 2),
            ImageHeader('oem_data_length', '<H', 32, 2),
        ]

        for a in FORMAT:
            setattr(self, a.field_name, None)
        if data:
            self.signature = data[0:8]
            for a in FORMAT:
                setattr(self, a.field_name, struct.unpack(a.format, data[a.start:a.start+a.len])[0])
            self.manufacturer_id = ord(data[10])|ord(data[11])<< 8|ord(data[12])<<16
            self.firmware_revision = VersionField(data[26:26+VERSION_FIELD_LEN])
            if self.oem_data_length != 0:
                self.oem_data = [ord(d) for d in data[34:-1]]
            # XXX checksum check
            self.checksum = data[34+self.oem_data_length]
            self.length = 34+self.oem_data_length+1

    def __str__(self):
        str = []
        str.append("HPM Upgrade Image header")
        str.append(" Signature:        %s" % self.signature)
        str.append(" Format Version:   %s" % self.format_version)
        str.append(" Device ID:        %s" % self.device_id)
        str.append(" Manufacturer:     %s" % self.manufacturer_id)
        str.append(" Product ID:       %s" % self.product_id)
        str.append(" Time:             %s" % self.time)
        str.append(" Image Cap:        0x%02x" % self.capabilities)
        str.append(" Components:       0x%02x" % self.components)
        str.append(" Selftest Timeout: %s" % self.selftest_timeout)
        str.append(" Rollback Timeout: %s" % self.rollback_timeout)
        str.append(" Inacc. Timeout:   %s" % self.inaccessibility_timeout)
        str.append(" Earliest comp.:   %s" % self.earliest_compatible_revision)
        str.append(" OEM data len:     %s" % self.oem_data_length)
        return "\n".join(str)



class UpgradeActionRecord:
    def __init__(self, data=None):
        if data:
            (self.upgrade_action_type, self.components, self.checksum) = \
                    struct.unpack('BBB', data[0:3])
            self.length = 3
            if self.upgrade_action_type is ACTION_UPLOAD_FIRMWARE_IMAGE:
                self.firmware_version = VersionField(data[3:3+VERSION_FIELD_LEN])
                self.firmware_description_string = data[9:30]
                self.firmware_length = struct.unpack('<L', data[30:34])[0]
                self.firmware_image_data = [ord(d) for d in data[34:34+self.firmware_length]]
                self.length += 31 + self.firmware_length

    def __str__(self):
        str = []
        str.append("Action Record:")
        str.append(" Action:     %s" % self.upgrade_action_type)
        str.append(" Components: 0x%02x" % self.components)
        if self.upgrade_action_type is ACTION_UPLOAD_FIRMWARE_IMAGE:
            str.append(" Description: %s" % self.firmware_description_string)
            str.append(" Image len  : %s" % self.firmware_length)
        return "\n".join(str)


HPM_IMAGE_CHECKSUM_SIZE = 16

class UpgradeImage:
    def __init__(self, filename=None):
        if filename:
            self._from_file(filename)

    def __str__(self):
        str = []
        return "\n".join(str)

    def _check_md5_sum(self, filedata):
        summer = hashlib.md5()
        checksum_actual = summer.update(filedata[:-HPM_IMAGE_CHECKSUM_SIZE])
        checksum_expected = filedata[-HPM_IMAGE_CHECKSUM_SIZE:]

    def _from_file(self, filename):

        try:
            f = open(filename, "r")
        except IOError:
            print 'Error open file "%s"' % filename

        # get file size
        file_size = os.stat(filename).st_size
        file_data = f.read(file_size)

        # get image checksum
        self._check_md5_sum(file_data)
        # XXX verify checksum

        # Upgrade Image Header
        self.header = UpgradeImageHeaderRecord(file_data)
        off = self.header.length

        # Upgrade Actions
        self.actions = []
        while off + HPM_IMAGE_CHECKSUM_SIZE < len(file_data):
            action = UpgradeActionRecord(file_data[off:])
            self.actions.append(action)
            off += action.length
