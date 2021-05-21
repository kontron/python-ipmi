import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '/Users/srmppn/Desktop/python-ipmi/')
import pyipmi
import pyipmi.interfaces

from pyipmi.msgs.chassis import BOOT_OPTION_LEGACY, BOOT_OPTION_EFI, BOOT_DEVICE_PXE, BOOT_DEVICE_DISK

# Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='lan')

connection = pyipmi.create_connection(interface)

connection.target = pyipmi.Target(0x20)

connection.session.set_session_type_rmcp('10.10.7.131', port=623)
connection.session.set_auth_type_user('admin', 'admin')
connection.session.establish()

device_id = connection.get_device_id()
connection.set_boot_options(persistent_boot_option = BOOT_OPTION_LEGACY, boot_device = BOOT_DEVICE_PXE)
result = connection.chassis_control_hard_reset()
