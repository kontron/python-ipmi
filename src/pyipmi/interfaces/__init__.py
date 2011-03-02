from ipmitool import Ipmitool

INTERFACES = [ Ipmitool ]

def create_interface(interface, *args, **kwargs):
    for intf in INTERFACES:
        if intf.NAME == interface:
            intf = intf(*args, **kwargs)
            return intf

    raise RuntimeError('unknown interface with name %s' % interface)

