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

from __future__ import print_function
from builtins import range
from builtins import object

import os
import codecs
import array
import struct
import collections
import hashlib
import time

from .errors import CompletionCodeError, HpmError, TimeoutError
from .msgs import create_request_by_name
from .msgs import constants
from .utils import check_completion_code, bcd_search, chunks
from .utils import py3dec_unic_bytes_fix, bytes2 as bytes #overwrites system bytes
from .state import State
from .fields import VersionField


PROPERTY_GENERAL_PROPERTIES = 0
PROPERTY_CURRENT_VERSION = 1
PROPERTY_DESCRIPTION_STRING = 2
PROPERTY_ROLLBACK_VERSION = 3
PROPERTY_DEFERRED_VERSION = 4
PROPERTY_OEM = list(range(192, 255))

ACTION_BACKUP_COMPONENT = 0x00
ACTION_PREPARE_COMPONENT = 0x01
ACTION_UPLOAD_FOR_UPGRADE = 0x02
ACTION_UPLOAD_FOR_COMPARE = 0x03

CC_LONG_DURATION_CMD_IN_PROGRESS = 0x80

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


class Hpm(object):

    def _get_component_count(self, components):
        """Return the number of components"""
        return bin(components).count('1')

    def get_target_upgrade_capabilities(self):
        rsp = self.send_message_with_name('GetTargetUpgradeCapabilities')
        return TargetUpgradeCapabilities(rsp)

    def get_component_property(self, component_id, property_id):
        rsp = self.send_message_with_name('GetComponentProperties',
                id=component_id, selector=property_id)
        return ComponentProperty.from_data(property_id, rsp.data)

    def get_component_properties(self, component_id):
        properties = []
        for p in (PROPERTY_GENERAL_PROPERTIES, PROPERTY_CURRENT_VERSION,
                  PROPERTY_DESCRIPTION_STRING, PROPERTY_ROLLBACK_VERSION,
                  PROPERTY_DEFERRED_VERSION):
            try:
                property = self.get_component_property(component_id, p)
                if property is not None:
                    properties.append(property)
            except CompletionCodeError as e:
                if e.cc == CC_GET_COMP_PROP_INVALID_PROPERTIES_SELECTOR:
                    continue
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
        self.send_message_with_name('AbortFirmwareUpgrade')

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

        self.send_message_with_name('InitiateUpgradeAction',
                   components=components_mask, action=action)

    def initiate_upgrade_action_and_wait(self, components_mask, action,
            timeout=2, interval=0.1):
        """ Initiate Upgrade Action and wait for
            long running command. """
        try:
            self.initiate_upgrade_action(components_mask, action)
        except CompletionCodeError as e:
            if e.cc == CC_LONG_DURATION_CMD_IN_PROGRESS:
                self.wait_for_long_duration_command(
                        constants.CMDID_HPM_INITIATE_UPGRADE_ACTION,
                        timeout, interval)
            else:
                raise HpmError('initiate_upgrade_action CC=0x%02x' % e.cc)

    def upload_firmware_block(self, block_number, data):
        self.send_message_with_name('UploadFirmwareBlock', number=block_number,
                data=data)

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
            except CompletionCodeError as e:
                if e.cc == CC_LONG_DURATION_CMD_IN_PROGRESS:
                    self.wait_for_long_duration_command(
                            constants.CMDID_HPM_UPLOAD_FIRMWARE_BLOCK,
                            timeout, interval)
                else:
                    raise HpmError('upload_firmware_block CC=0x%02x' % e.cc)
            block_number += 1
            block_number &= 0xff

    def finish_firmware_upload(self, component, length):
        return self.send_message_with_name('FinishFirmwareUpload',
                component_id=component, image_length=length)

    def finish_upload_and_wait(self, component, length,
                               timeout=2, interval=0.1):
        """ Finish the firmware upload process and wait for
            long running command. """
        try:
            rsp = self.finish_firmware_upload(component, length)
            check_completion_code(rsp.completion_code)
        except CompletionCodeError as e:
            if e.cc == CC_LONG_DURATION_CMD_IN_PROGRESS:
                self.wait_for_long_duration_command(
                            constants.CMDID_HPM_FINISH_FIRMWARE_UPLOAD,
                            timeout, interval)
            else:
                raise HpmError('finish_firmware_upload CC=0x%02x' % e.cc)

    def get_upgrade_status(self):
        return UpgradeStatus(self.send_message_with_name('GetUpgradeStatus'))

    def wait_for_long_duration_command(self, expected_cmd, timeout, interval):

        start_time = time.time()
        while time.time() < start_time + timeout:
            try:
                status = self.get_upgrade_status()
                if status.command_in_progress is not expected_cmd \
                        and status.command_in_progress is not 0x34:
                    pass
                if status.last_completion_code == CC_LONG_DURATION_CMD_IN_PROGRESS:
                    time.sleep(interval)
                else:
                    return
            except TimeoutError:
                time.sleep(interval)

    def activate_firmware(self, rollback_override=None):
        req = create_request_by_name('ActivateFirmware')
        if rollback_override is not None:
            req.rollback_override_policy = rollback_override
        rsp = self.send_message(req)
        check_completion_code(rsp.completion_code)

    def activate_firmware_and_wait(self, rollback_override=None,
                                   timeout=2, interval=1):
        """ Activate the new uploaded firmware and wait for
            long running command. """
        try:
            self.activate_firmware(rollback_override)
        except CompletionCodeError as e:
            if e.cc == CC_LONG_DURATION_CMD_IN_PROGRESS:
                self.wait_for_long_duration_command(
                            constants.CMDID_HPM_ACTIVATE_FIRMWARE,
                            timeout, interval)
            else:
                raise HpmError('activate_firmware CC=0x%02x' % e.cc)
        except TimeoutError:
            # controller is in reset and flashed new firmware
            pass

    def query_selftest_results(self):
        return SelfTestResult(self.send_message_with_name('QuerySelftestResults'))

    def query_rollback_status(self):
        return RollbackStatus(self.send_message_with_name('QueryRollbackStatus'))

    def initiate_manual_rollback(self):
        return RollbackStatus(self.send_message_with_name('InitiateManualRollback'))

    def initiate_manual_rollback_and_wait(self, timeout=2, interval=0.1):
        try:
            self.initiate_manual_rollback()
        except CompletionCodeError as e:
            if e.cc == CC_LONG_DURATION_CMD_IN_PROGRESS:
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
            if type(action) == UpgradeActionRecordUploadForUpgrade:
                return action.firmware_version
        return None

    def _do_upgrade_action_backup(self, image):
        for action in image.actions:
            if type(action) == UpgradeActionRecordBackup:
                pass

    def _do_upgrade_action_prepare(self, image):
        for action in image.actions:
            if type(action) == UpgradeActionRecordPrepare:
                print("do ACTION_PREPARE_COMPONENT")

    def _do_upgrade_action_upload(self, image):
        for action in image.actions:
            if type(action) == UpgradeActionRecordUploadForUpgrade:
                print("do ACTION_UPLOAD_FOR_UPGRADE")

    def preparation_stage(self, image):
        ####################################################
        # match device ID, manfuacturer ID, etc.
        device_id = self.get_device_id()

        header = image.header

        if header.device_id != device_id.device_id:
            raise HpmError('Device ID: image=0x%x device=0x%x' \
                    % (header.device_id, device_id.device_id))
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
        support = False
        for imageComponent in header.components:
            if imageComponent in targetCap.components:
                support = True

        if support != True:
            raise HpmError('no supported component in image')

    def upgrade_stage(self, image, component):
        for action in image.actions:
            if action.components & (1 << component) == 0:
                continue
            self.initiate_upgrade_action_and_wait(1 << component, action.action_type)
            if type(action) == UpgradeActionRecordUploadForUpgrade:
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


class UpgradeStatus(State):

    def _from_response(self, rsp):
        self.command_in_progress = rsp.command_in_progress
        self.last_completion_code = rsp.last_completion_code

    def __str__(self):
        str = []
        str.append("cmd=0x%02x cc=0x%02x" % \
                (self.command_in_progress, self.last_completion_code))
        return "\n".join(str)


class TargetUpgradeCapabilities(State):

    def _from_response(self, rsp):
        self.version = rsp.hpm_1_version
        self.components = []
        for i in range(8):
            if rsp.component_present & (1<<i):
                self.components.append(i)

    def __str__(self):
        str = []
        str.append("Target Upgrade Capabilities")
        str.append(" HPM.1 version: %s" % self.version)
        str.append(" Components: %s" % self.components)
        return "\n".join(str)

codecs.register(bcd_search)


class ComponentProperty(object):
    def __init__(self, data=None):
        if (data):
            self._from_rsp_data(data)

    @staticmethod
    def from_data(component_id, data):
        if isinstance(data, str):
            data = [ord(c) for c in data]

        if component_id is PROPERTY_GENERAL_PROPERTIES:
            return ComponentPropertyGeneral(data)
        elif component_id is PROPERTY_CURRENT_VERSION:
            return ComponentPropertyCurrentVersion(data)
        elif component_id is PROPERTY_DESCRIPTION_STRING:
            return ComponentPropertyDescriptionString(data)
        elif component_id is PROPERTY_ROLLBACK_VERSION:
            return ComponentPropertyRollbackVersion(data)
        elif component_id is PROPERTY_DEFERRED_VERSION:
            return ComponentPropertyDeferredVersion(data)
        elif component_id in PROPERTY_OEM:
            raise NotImplementedError


class ComponentPropertyGeneral(ComponentProperty):

    ROLLBACK_SUPPORT_MASK = 0x03
    PREPARATION_SUPPORT_MASK = 0x04
    COMPARISON_SUPPORT_MASK = 0x08
    DEFERRED_ACTIVATION_SUPPORT_MASK = 0x10
    PAYLOAD_COLD_RESET_REQ_SUPPORT_MASK = 0x20

    def _from_rsp_data(self, data):
        support = []
        cap = data[0]

        if cap & self.ROLLBACK_SUPPORT_MASK == 0:
            support.append('rollback_backup_not_supported')
        elif cap & self.ROLLBACK_SUPPORT_MASK == 1:
            support.append('rollback_is_supported')
        elif cap & self.ROLLBACK_SUPPORT_MASK == 2:
            support.append('rollback_is_supported')
        elif cap & self.ROLLBACK_SUPPORT_MASK == 3:
            support.append('reserved')

        if cap & self.PREPARATION_SUPPORT_MASK:
            support.append('prepartion')
        if cap & self.COMPARISON_SUPPORT_MASK:
            support.append('comparison')
        if cap & self.DEFERRED_ACTIVATION_SUPPORT_MASK:
            support.append('deferred_activation')
        if cap & self.PAYLOAD_COLD_RESET_REQ_SUPPORT_MASK:
            support.append('payload_cold_reset_required')

        self.general = support


class ComponentPropertyCurrentVersion(ComponentProperty):

    def _from_rsp_data(self, data):
        self.version = VersionField(data)


class ComponentPropertyDescriptionString(ComponentProperty):

    def _from_rsp_data(self, data):
        self.description = py3dec_unic_bytes_fix(array.array('B', data).tostring())
        self.description = self.description.replace('\0', '')


class ComponentPropertyRollbackVersion(ComponentProperty):

    def _from_rsp_data(self, data):
        self.version = VersionField(data)


class ComponentPropertyDeferredVersion(ComponentProperty):

    def _from_rsp_data(self, data):
        self.version = VersionField(data)


class ComponentPropertyOem(ComponentProperty):

    def _from_rsp_data(self, data):
        self.oem_data = data


class SelfTestResult(State):

    CORRUPTED_OR_INACCESSIBLE_DATA_OR_DEVICES = 0x57

    def _from_response(self, rsp):
        self.status = rsp.selftest_result_1

        result2 = rsp.selftest_result_2

        if self.status != self.CORRUPTED_OR_INACCESSIBLE_DATA_OR_DEVICES:
            self.fail_sel = (result2 & 0x80) >> 7
            self.fail_sdrr = (result2 & 0x40) >> 6
            self.fail_bmc_fru = (result2 & 0x20) >> 5
            self.fail_ipmb = (result2 & 0x10) >> 4
        self.fail_sdrr_empty = (result2 & 0x08) >> 3
        self.fail_bmc_fru_interanl_area = (result2 & 0x04) >> 2
        self.fail_bootblock = (result2 & 0x02) >> 1
        self.fail_mc = (result2 & 0x01) >> 0


class RollbackStatus(object):
    def __init__(self, rsp=None):
        if rsp:
            self._from_rsp(rsp)

    def _from_rsp(self, rsp):

        if rsp.completion_estimate:
            self.percent_complete  = rsp.completion_estimate


image_header = collections.namedtuple('image_header', ['field_name', 'format', 'start', 'len'])


class UpgradeImageHeaderRecord(object):
    FORMAT  = [
        image_header('format_version', 'B', 8, 1),
        image_header('device_id', 'B', 9, 1),
        image_header('product_id', '<H', 13, 2),
        image_header('time', '<L', 15, 4),
        image_header('capabilities', 'B', 19,1),
        image_header('selftest_timeout', 'B', 21, 1),
        image_header('rollback_timeout', 'B', 22, 1),
        image_header('inaccessibility_timeout', 'B', 23, 1),
        image_header('earliest_compatible_revision', '<H', 24, 2),
        image_header('oem_data_length', '<H', 32, 2),
    ]

    def __init__(self, data=None):
        for a in self.FORMAT:
            setattr(self, a.field_name, None)
        if data:
            self._from_data(data)

    def _from_data(self, data):
        self.signature = data[0:8]

        for a in self.FORMAT:
            setattr(self, a.field_name, struct.unpack(
                    a.format, data[a.start:a.start+a.len])[0])

        if isinstance(data, str):
            data = [ord(c) for c in data]

        self.manufacturer_id = data[10] | data[11] << 8 | data[12] << 16
        self.components = []
        for i in range(8):
            if data[20] & (1 << i):
                self.components.append(i)
        self.earliest_compatible_revision = VersionField(data[24:24 +
                VersionField.VERSION_FIELD_LEN])
        self.firmware_revision = VersionField(data[26:26 + VersionField.VERSION_WITH_AUX_FIELD_LEN])

        if self.oem_data_length:
            self.oem_data = data[34:-1]
        # XXX checksum check
        self.checksum = data[34 + self.oem_data_length]
        self.length = 34 + self.oem_data_length+1

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


class UpgradeActionRecord(object):

    ACTIONS = (
        "Backup",
        "Prepare",
        "Upload for Upgrade",
        "Upload for Compare"
    )

    def __init__(self, data=None):
        self.action_type = ord(data[0])
        if data:
            (self.action, self.components, self.checksum) \
                = struct.unpack('BBB', bytes(data[0:3], 'raw_unicode_escape'))
            self.length = 3

    @staticmethod
    def create_from_data(data):
        action_type = ord(data[0])
        if action_type == ACTION_BACKUP_COMPONENT:
            return UpgradeActionRecordBackup(data)
        elif action_type == ACTION_PREPARE_COMPONENT:
            return UpgradeActionRecordPrepare(data)
        elif action_type == ACTION_UPLOAD_FOR_UPGRADE:
            return UpgradeActionRecordUploadForUpgrade(data)
        elif action_type == ACTION_UPLOAD_FOR_COMPARE:
            return UpgradeActionRecordUploadForCompare(data)
        else:
            raise HpmError('unsupported ActionRecord')

    def __str__(self):
        str = []
        str.append("Action Record Type: 0x%x (%s) " %
            (self.action, self.ACTIONS[self.action]))
        str.append(" Components: 0x%02x" % self.components)
        return "\n".join(str)


class UpgradeActionRecordBackup(UpgradeActionRecord):
    pass


class UpgradeActionRecordPrepare(UpgradeActionRecord):
    pass


class UpgradeActionRecordUploadForUpgrade(UpgradeActionRecord):
    def __init__(self, data=None):
        UpgradeActionRecord.__init__(self, data)
        if data:
            data = bytes(data, 'raw_unicode_escape')
            self.firmware_version = VersionField(data[3:3 +
            VersionField.VERSION_WITH_AUX_FIELD_LEN])
            self.firmware_description_string = py3dec_unic_bytes_fix(data[9:30])
            self.firmware_length = struct.unpack('<L', data[30:34])[0]
            self.firmware_image_data = data[34:(34 + self.firmware_length)]
            self.length += 31 + self.firmware_length


class UpgradeActionRecordUploadForCompare(UpgradeActionRecord):
    pass


class ImageChecksumRecord(object):
    def __init__(self, data=None):
        if data:
            self._from_data(data)

    def _from_data(self, data):
        self.data = data[0:16]


HPM_IMAGE_CHECKSUM_SIZE = 16

class UpgradeImage(object):
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
            print('Error open file "%s"' % filename)

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
