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

import os
import codecs
import array
import struct
import collections
import hashlib
import time

from pyipmi.errors import DecodingError, CompletionCodeError, HpmError, TimeoutError
from pyipmi.msgs import create_request_by_name
from pyipmi.msgs import constants
from pyipmi.utils import check_completion_code, bcd_search, chunks


PROPERTY_GENERAL_PROPERTIES = 0
PROPERTY_CURRENT_VERSION = 1
PROPERTY_DESCRIPTION_STRING = 2
PROPERTY_ROLLBACK_VERSION = 3
PROPERTY_DEFERRED_VERSION = 4
PROPERTY_OEM = range(192, 255)

ACTION_BACKUP_COMPONENT = 0x00
ACTION_PREPARE_COMPONENT = 0x01
ACTION_UPLOAD_FOR_UPGRADE = 0x02
ACTION_UPLOAD_FOR_COMPARE = 0x03

LONG_DURATION_CMD_IN_PROGRESS_CC = 0x80

CC_GET_COMP_PROP_UPGRADE_NOT_SUPPORTED_OVER_INTF = 0x81
CC_GET_COMP_PROP_INVALID_COMPONENT = 0x82
CC_GET_COMP_PROP_INVALID_PROPERTIES_SELECTOR = 0x83

CC_INITIATE_UPGRADE_CMD_IN_PROGRESS = 0x80
CC_INITIATE_UPGRADE_INVALID_COMPONENT = 0x81

CC_QUERY_SELFTEST_COMPLETED = 0x00
CC_QUERY_SELFTEST_IN_PROGRESS = 0x80
CC_QUERY_SELFTEST_UPGRADE_NOT_SUPPORTED_OVER_INTF = 0x81
CC_QUERY_SELFTEST_NO_RESULTS_AVAILABLE = 0xD5

CC_ABORT_UPGRADE_CANNOT_ABORT = 0x80
CC_ABORT_UPGRADE_CANNOT_RESUME_OPERATION = 0x81

class Hpm:

    def _check_completion_code(self, rsp):
        check_completion_code(rsp.completion_code)

    def _get_component_count(self, components):
        """Return the number of components"""
        return bin(components).count('1')

    def get_target_upgrade_capabilities(self):
        req = create_request_by_name('GetTargetUpgradeCapabilities')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return TargetUpgradeCapabilities(rsp)

    def get_component_property(self, component_id, property_id):
        req = create_request_by_name('GetComponentProperties')
        req.id = component_id
        req.selector = property_id
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return ComponentProperty.create_from_id(property_id, rsp)

    def get_component_properties(self, component_id):
        properties = []
        for p in (PROPERTY_GENERAL_PROPERTIES, PROPERTY_CURRENT_VERSION,
                PROPERTY_DESCRIPTION_STRING, PROPERTY_ROLLBACK_VERSION,
                PROPERTY_DEFERRED_VERSION):
            property = self.get_component_property(component_id, p)
            if property is not None:
                properties.append(property)
        return properties

    def find_component_id_by_descriptor(self, descriptor):
        caps = self.get_target_upgrade_capabilities()
        for component_id in caps.components:
            property = self.get_component_property(component_id, PROPERTY_DESCRIPTION_STRING)
            if property is not None:
                if property.description == descriptor:
                    return component_id
        return None

    def abort_firmware_upgrade(self):
        req = create_request_by_name('AbortFirmwareUpgrade')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)

    def initiate_upgrade_action(self, components_mask, action):
        """ Initiate Upgrade Action
        components:
        action:
            ACTION_BACKUP_COMPONENT = 0x00
            ACTION_PREPARE_COMPONENT = 0x01
            ACTION_UPLOAD_FOR_UPGRADE = 0x02
            ACTION_UPLOAD_FOR_COMPARE = 0x03
        """

        if action in (ACTION_UPLOAD_FOR_UPGRADE, ACTION_UPLOAD_FOR_COMPARE):
            if self._get_component_count(components_mask) != 1:
                raise HpmError("more than 1 component not support for action")

        req = create_request_by_name('InitiateUpgradeAction')
        req.components = components_mask
        req.action = action

        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def initiate_upgrade_action_and_wait(self, components_mask, action,
            timeout=2, interval=0.1):
        """ Initiate Upgrade Action and wait for
            long running command. """
        try:
            self.initiate_upgrade_action(components_mask, action)
        except CompletionCodeError, e:
            if e.cc == LONG_DURATION_CMD_IN_PROGRESS_CC:
                self.wait_for_long_duration_command(
                        constants.CMDID_HPM_INITIATE_UPGRADE_ACTION,
                        timeout, interval)
            else:
                raise HpmError('initiate_upgrade_action CC=0x%02x' % e.cc)

    def upload_firmware_block(self, block_number, data):
        req = create_request_by_name('UploadFirmwareBlock')
        req.number = block_number
        req.data = data
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def _determine_max_block_size(self):
        #tbd
        return 22

    def upload_binary(self, binary, timeout=2, interval=0.1):
        """ Upload all firmware blocks from binary and wait for
            long running command. """
        block_number = 0
        block_size = self._determine_max_block_size()

        for chunk in chunks(binary, block_size):
            try:
                self.upload_firmware_block(block_number, chunk)
            except CompletionCodeError, e:
                if e.cc == LONG_DURATION_CMD_IN_PROGRESS_CC:
                    self.wait_for_long_duration_command(
                            constants.CMDID_HPM_UPLOAD_FIRMWARE_BLOCK,
                            timeout, interval)
                else:
                    raise HpmError('upload_firmware_block CC=0x%02x' % e.cc)
            block_number += 1
            block_number &= 0xff

    def finish_firmware_upload(self, component, length):
        req = create_request_by_name('FinishFirmwareUpload')
        req.component_id = component
        req.image_length = length
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def finish_upload_and_wait(self, component, length,
            timeout=2, interval=0.1):
        """ Finish the firmware upload process and wait for
            long running command. """
        try:
            rsp = self.finish_firmware_upload(component, length)
            check_completion_code(rsp.completion_code)
        except CompletionCodeError, e:
            if e.cc == LONG_DURATION_CMD_IN_PROGRESS_CC:
                self.wait_for_long_duration_command(
                            constants.CMDID_HPM_FINISH_FIRMWARE_UPLOAD,
                            timeout, interval)
            else:
                raise HpmError('finish_firmware_upload CC=0x%02x' % e.cc)

    def get_upgrade_status(self):
        req = create_request_by_name('GetUpgradeStatus')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return UpgradeStatus(rsp)

    def wait_for_long_duration_command(self, expected_cmd,
            timeout=5, interval=1):

        start_time = time.time()
        while time.time() < start_time + timeout:
            try:
                status = self.get_upgrade_status()
                if status.command_in_progress is not expected_cmd \
                        and status.command_in_progress is not 0x34:
                    #raise HpmError('unexpected cmd=0x%02x' \
                    #        % status.command_in_progress)
                    pass
                if status.last_completion_code == LONG_DURATION_CMD_IN_PROGRESS_CC:
                    time.sleep(interval)
                else:
                    return
            except TimeoutError:
                time.sleep(interval)


    def activate_firmware(self, rollback_override=None):
        req = create_request_by_name('ActivateFirmware')
        if rollback_override != None:
            req.rollback_override_policy = rollback_override
        rsp = self.send_message(req)
        self._check_completion_code(rsp)

    def activate_firmware_and_wait(self, rollback_override=None,
            timeout=2, interval=1):
        """ Activate the new uploaded firmware and wait for
            long running command. """
        try:
            self.activate_firmware(rollback_override)
        except CompletionCodeError, e:
            if e.cc == LONG_DURATION_CMD_IN_PROGRESS_CC:
                self.wait_for_long_duration_command(
                            constants.CMDID_HPM_ACTIVATE_FIRMWARE,
                            timeout, interval)
            else:
                raise HpmError('activate_firmware CC=0x%02x' % e.cc)
        except TimeoutError:
            # controller is in reset and flashed new firmware
            pass

    def query_selftest_results(self):
        req = create_request_by_name('QuerySelftestResults')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return SelfTestResult(rsp.data)

    def query_rollback_status(self):
        req = create_request_by_name('QueryRollbackStatus')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return RollbackStatus(rsp)

    def initiate_manual_rollback(self):
        req = create_request_by_name('InitiateManualRollback')
        rsp = self.send_message(req)
        self._check_completion_code(rsp)
        return RollbackStatus(rsp)

    def initiate_maunal_rollback_and_wait(self, timeout=2, interval=0.1):
        try:
            self.initiate_manual_rollback()
        except CompletionCodeError, e:
            if e.cc == LONG_DURATION_CMD_IN_PROGRESS_CC:
                self.wait_for_long_duration_command(
                            constants.CMDID_HPM_INITIATE_MANUAL_ROLLBACK,
                            60, interval)
            else:
                raise HpmError('activate_firmware CC=0x%02x' % e.cc)
        except TimeoutError:
            # controller is in reset and flashed new firmware
            pass

    def open_upgrade_image(self, filename):
        image = UpgradeImage(filename)
        return image

    def get_upgrade_version_from_file(self, filename):
        image = UpgradeImage(filename)
        for action in image.actions:
            if action.type == ACTION_UPLOAD_FOR_UPGRADE:
                return action.firmware_version
        return None

    def _do_upgrade_action_backup(self, image):
        for action in image.actions:
            if action.type == ACTION_BACKUP_COMPONENT:
                pass

    def _do_upgrade_action_prepare(self, image):
        for action in image.actions:
            if action.type == ACTION_PREPARE_COMPONENT:
                print "do ACTION_PREPARE_COMPONENT"

    def _do_upgrade_action_upload(self, image):
        for action in image.actions:
            if action.type == ACTION_UPLOAD_FOR_UPGRADE:
                print "do ACTION_UPLOAD_FOR_UPGRADE"


    def preparation_stage(self, image):
        ####################################################
        # match device ID, manfuacturer ID, etc.
        device_id = self.get_device_id()

        header = image.header

        if header.device_id != device_id.id:
            raise HpmError('Device ID: image=0x%x device=0x%x' \
                    % (header.device_id, device_id.id))
        if header.manufacturer_id != device_id.manufacturer_id:
            raise HpmError('Manufacturer ID: image=0x%x device=0x%x' \
                    % (header.manufacturer_id, device_id.manufacturer_id))
        if header.product_id != device_id.product_id:
            raise HpmError('Product ID: image=0x%x device=0x%x' \
                    % (header.product_id, device_id.product_id))

        # tbd check version

        ####################################################
        # compare current revision with upgrade image earlist comp rev
        targetCap = self.get_target_upgrade_capabilities()
        # tbd check version

        ####################################################
        # Match IPM Controller capabilities with Upgrade Image capabilities
        for imageComponent in header.components:
            if imageComponent in targetCap.components:
                support = True

        if support != True:
            raise HpmError('no supported component in image')

    def upgrade_stage(self, image, component):
        for action in image.actions:
            if action.components & (1 << component) == 0:
                continue
            self.initiate_upgrade_action_and_wait(1 << component, action.type)
            if action.type == ACTION_UPLOAD_FOR_UPGRADE:
                self.upload_binary(action.firmware_image_data)
                self.finish_upload_and_wait(component, action.firmware_length)

    def _activation_state_do_self_testing(self):
        pass

    def wait_until_new_firmware_comes_up(self, timeout, interval):
        start_time = time.time()
        while time.time() < start_time + timeout:
            try:
                status = self.get_upgrade_status()
                self.get_device_id()
            except TimeoutError:
                time.sleep(interval)
        time.sleep(5)

    def activation_stage(self, image, component):
        self.activate_firmware_and_wait(image.header.inaccessibility_timeout, 1)
        self.wait_until_new_firmware_comes_up(image.header.inaccessibility_timeout, 1)
        self._activation_state_do_self_testing()

    def install_component_from_image(self, image, component):
        self.abort_firmware_upgrade()
        if component not in image.header.components:
            raise HpmError('component=%d not in image' % component)
        self.preparation_stage(image)
        self.upgrade_stage(image, component)
        self.activation_stage(image, component)

    def install_component_from_file(self, filename, component):
        image = UpgradeImage(filename)
        self.install_component_from_image(image, component)


class UpgradeStatus:
    def __init__(self, rsp=None):
        if rsp:
            self._from_response(rsp)

    def _from_response(self, rsp):
        self.command_in_progress = rsp.command_in_progress
        self.last_completion_code = rsp.last_completion_code

    def __str__(self):
        str = []
        str.append("cmd=0x%02x cc=0x%02x" % \
                (self.command_in_progress, self.last_completion_code))
        return "\n".join(str)


class TargetUpgradeCapabilities:
    def __init__(self, rsp=None):
        if rsp:
            self._from_response(rsp)

    def _from_response(self, rsp):
        self.version = rsp.hpm_1_version
        self.components = []
        for i in range(8):
            if rsp.component_present & (1<<i):
                self.components.append(i)

    def __str__(self):
        str = []
        str.append("target upgrade capabilities %s" % self.components)
        str.append(" HPM.1 version: %s" % self.version)
        return "\n".join(str)


VERSION_FIELD_LEN = 6
class VersionField:
    def __init__(self, data=None):
        self.major = None
        self.minor = None
        if data:
            self.from_data(data)

    def from_data(self, data):
        if isinstance(data, str):
            data = array.array('B', [ord(c) for c in data])
        self.version = self._decode_version_string(data[0:2])
        if len(data) == 6:
            self.auxiliary = data[2:6]

    def __str__(self):
        str = []
        str.append('%s' % (self.version_to_string()))
        return '\n'.join(str)

    def _decode_version_string(self, data):
        """`data` is array.array
        """
        self.major = data[0]

        if data[1] is not 255:
            self.minor = data[1:2].tostring().decode('bcd+')
        else:
            self.minor = data[1]

    def version_to_string(self):
        return ''.join("%s.%s" % (self.major, self.minor))


codecs.register(bcd_search)

class ComponentProperty:
    def __init__(self, id):
        self.id = id

    @staticmethod
    def create_from_id(id, rsp):
        if id is PROPERTY_GENERAL_PROPERTIES:
            return ComponentPropertyGeneral(rsp.data)

        elif id is PROPERTY_CURRENT_VERSION:
            return ComponentPropertyCurrentVersion(rsp.data)

        elif id is PROPERTY_DESCRIPTION_STRING:
            return ComponentPropertyDescriptionString(rsp.data)

        elif id is PROPERTY_ROLLBACK_VERSION:
            return ComponentPropertyRollbackVersion(rsp.data)

        elif id is PROPERTY_DEFERRED_VERSION:
            return ComponentPropertyDeferredVersion(rsp.data)

        elif id in PROPERTY_OEM:
            raise NotImplementedError


class ComponentPropertyGeneral(ComponentProperty):
    def __init__(self, data=None):
        ComponentProperty.__init__(self, PROPERTY_GENERAL_PROPERTIES)
        if (data):
            self._from_data(data)

    def _from_data(self, data):
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
        self.general = support


class ComponentPropertyCurrentVersion(ComponentProperty):
    def __init__(self, data=None):
        ComponentProperty.__init__(self, PROPERTY_CURRENT_VERSION)
        if (data):
            self._from_msg_response(data)

    def _from_msg_response(self, data):
        self.version = VersionField(data)


class ComponentPropertyDescriptionString(ComponentProperty):
    def __init__(self, data=None):
        ComponentProperty.__init__(self, PROPERTY_DESCRIPTION_STRING)
        if (data):
            self._from_msg_response(data)

    def _from_msg_response(self, data):
        descr =  data.tostring().replace('\0', '')
        self.description = descr


class ComponentPropertyRollbackVersion(ComponentProperty):
    def __init__(self, data=None):
        ComponentProperty.__init__(self, PROPERTY_ROLLBACK_VERSION)
        if (data):
            self._from_msg_response(data)

    def _from_msg_response(self, data):
        self.version = VersionField(data)


class ComponentPropertyDeferredVersion(ComponentProperty):
    def __init__(self, data=None):
        ComponentProperty.__init__(self, PROPERTY_DEFERRED_VERSION)
        if (data):
            self._from_msg_response(data)

    def _from_msg_response(self, data):
        self.version = VersionField(data)


class ComponentPropertyOem(ComponentProperty):
    def __init__(self, data=None):
        if (data):
            self._from_msg_response(data)

    def _from_msg_response(self, data):
        raise NotImplementedError()


class SelfTestResult:
    def __init__(self, data=None):
        if data:
            self.from_data(data)

    def from_data(self, data):
        self.status = data[0]

        if self.status  != 0x57:
            self.fail.sel = (data[1] & 0x80) >> 7
            self.fail.sdrr = (data[1] & 0x40) >> 6
            self.fail.bmc_fru = (data[1] & 0x20) >> 5
            self.fail.ipmb = (data[1] & 0x10) >> 4
            self.fail.sdrr_empty = (data[1] & 0x08) >> 3
            self.fail.bmc_fru_interanl_area = (data[1] & 0x04) >> 2
            self.fail.bootblock = (data[1] & 0x02) >> 1
            self.fail.mc = (data[1] & 0x01) >> 0


class RollbackStatus:
    def __init__(self, rsp=None):
        if rsp:
            self.from_rsp(rsp)

    def from_rsp(self, rsp):

        if rsp.completion_estimate:
            self.percent_complete  = rsp.completion_estimate


ImageHeader = collections.namedtuple('ImageHeader', ['field_name', 'format', 'start', 'len'])

class UpgradeImageHeaderRecord:
    FORMAT  = [
        ImageHeader('format_version', 'B', 8, 1),
        ImageHeader('device_id', 'B', 9, 1),
        ImageHeader('product_id', '<H', 13, 2),
        ImageHeader('time', '<L', 15, 4),
        ImageHeader('capabilities', 'B', 19,1),
        #ImageHeader('components', 'B',  20, 1),
        ImageHeader('selftest_timeout', 'B', 21, 1),
        ImageHeader('rollback_timeout', 'B', 22, 1),
        ImageHeader('inaccessibility_timeout', 'B', 23, 1),
        ImageHeader('earliest_compatible_revision', '<H', 24, 2),
        ImageHeader('oem_data_length', '<H', 32, 2),
    ]

    def __init__(self, data=None):
        for a in self.FORMAT:
            setattr(self, a.field_name, None)
        if data:
            self.from_data(data)

    def from_data(self, data):
        self.signature = data[0:8]

        for a in self.FORMAT:
            setattr(self, a.field_name, struct.unpack(a.format, data[a.start:a.start+a.len])[0])
        self.manufacturer_id = ord(data[10]) | ord(data[11]) << 8|ord(data[12])<<16
        self.components = []
        for i in range(8):
            if ord(data[20]) & (1<<i):
                self.components.append(i)
        self.earliest_compatible_revision = VersionField(data[24:24+2])
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
        str.append(" Components:       %s" % self.components)
        str.append(" Selftest Timeout: %s" % self.selftest_timeout)
        str.append(" Rollback Timeout: %s" % self.rollback_timeout)
        str.append(" Inacc. Timeout:   %s" % self.inaccessibility_timeout)
        str.append(" Earliest comp.:   %s" % self.earliest_compatible_revision)
        str.append(" firmware Revision:%s" % self.firmware_revision)
        str.append(" OEM data len:     %s" % self.oem_data_length)
        return "\n".join(str)


class UpgradeActionRecord:

    ACTIONS = (
        "Backup",
        "Prepare",
        "Upload for Upgrade",
        "Upload for Compare"
    )

    def __init__(self, data=None):
        if data:
            (self.type, self.components, self.checksum) = struct.unpack('BBB', data[0:3])
            #self.components = struct.unpack('B', data[1:2])
            #self.checksum = struct.unpack('B', data[2:3])
            self.length = 3

    @staticmethod
    def create_from_data(data):
        type = ord(data[0])
        if type == ACTION_BACKUP_COMPONENT:
            return UpgradeActionRecordBackup(data)
        elif type == ACTION_PREPARE_COMPONENT:
            return UpgradeActionRecordPrepare(data)
        elif type == ACTION_UPLOAD_FOR_UPGRADE:
            return UpgradeActionRecordUploadForUpgrade(data)
        elif type == ACTION_UPLOAD_FOR_COMPARE:
            return UpgradeActionRecordUploadForCompare(data)
        else:
            raise HpmError('unsupported ActionRecord')

    def __str__(self):
        str = []
        str.append("Action Record Type: 0x%x (%s) " % (self.type, self.ACTIONS[self.type]))
        str.append(" Components: 0x%02x" % self.components)
        return "\n".join(str)


class UpgradeActionRecordBackup(UpgradeActionRecord):
    def __init__(self, data=None):
        if (data):
            UpgradeActionRecord.__init__(self, data)


class UpgradeActionRecordPrepare(UpgradeActionRecord):
    def __init__(self, data=None):
        if (data):
            UpgradeActionRecord.__init__(self, data)


class UpgradeActionRecordUploadForUpgrade(UpgradeActionRecord):
    def __init__(self, data=None):
        if (data):
            UpgradeActionRecord.__init__(self, data)

            ###################################################
            # PICMG HPM.1 R1.0 - Table 4-3
            #    Upgrade action recordThe following bytes 3:(34+m) are only present
            #   if the Upgrade action type = 02h (Upload Firmware Image)
            self.firmware_version = VersionField(data[3:3+VERSION_FIELD_LEN])
            self.firmware_description_string = data[9:30]
            self.firmware_length = struct.unpack('<L', data[30:34])[0]
            self.firmware_image_data = data[34:(34 + self.firmware_length)]
            self.length += 31 + self.firmware_length


class UpgradeActionRecordUploadForCompare(UpgradeActionRecord):
    def __init__(self, data=None):
        if (data):
            UpgradeActionRecord.__init__(self, data)


class ImageChecksumRecord:
    def __init__(self, data=None):
        if data:
            self._from_data(data)

    def _from_data(self, data):
        self.data = data[0:16]


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
        self.checksum_actual = summer.update(filedata[:-HPM_IMAGE_CHECKSUM_SIZE])
        self.checksum_expected = filedata[-HPM_IMAGE_CHECKSUM_SIZE:]

    def _from_file(self, filename):

        try:
            file = open(filename, "r")
        except IOError:
            print 'Error open file "%s"' % filename

        ################################
        # get file size
        file_size = os.stat(filename).st_size
        file_data = file.read(file_size)

        ################################
        # get image checksum
        self._check_md5_sum(file_data)
        # XXX verify checksum

        ################################
        # Upgrade Image Header
        self.header = UpgradeImageHeaderRecord(file_data)
        off = self.header.length

        ################################
        # Upgrade Actions
        self.actions = []
        while (off + HPM_IMAGE_CHECKSUM_SIZE) < len(file_data):
            action = UpgradeActionRecord.create_from_data(file_data[off:])
            self.actions.append(action)
            off += action.length

        ################################
        # Image checksum
        self.checksum = ImageChecksumRecord(file_data[off:file_size])

        #if self.checksum.data != self.checksum_actual:
        #    raise HpmError("hpm file checksum error")

        file.close()
