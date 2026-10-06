Chassis Commands
================

These commands are primarily to provide standardized chassis status and control functions for Remote Management Cards and Remote Consoles that access the :abbr:`BMC (Board Management Controller)`. The `IPMI standard`_ defines the following Chassis commands:

+-------------------------------+-----+---------+-----+
| Command                       | O/M | Support | API |
+===============================+=====+=========+=====+
| Get Chassis Capabilities      | M   | Yes     | No  |
+-------------------------------+-----+---------+-----+
| Get Chassis Status            | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Chassis Control               | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Chassis Reset                 | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Chassis Identify              | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set Front Panel Enables       | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set Chassis Capabilities      | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set Power Restore Policy      | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set Power Cycle Interval      | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Get System Restart Cause      | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set System Boot Options       | O   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Get System Boot Options       | O   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Get POH Counter               | O   | Yes     | No  |
+-------------------------------+-----+---------+-----+

.. note::

   - O/M - Optional/Mandatory command as stated by the IPMI standard
   - Support - Supported command by **send_message_with_name** method
   - API - High level API support implemented in this library

The methods and the returned classes are described in detail in the :doc:`api`.

Get Chassis Capabilities Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command returns information about which main chassis management functions are present on the :abbr:`IPMB (Intelligent Platform Management Bus)` and what addresses are used to access those functions. This command is used to find the devices that provide functions such as :abbr:`SEL (System Event Log)`, :abbr:`SDR (Sensor Data Record)`, and :abbr:`ICMB (Intelligent Chassis Management Bus)` Bridging so that they can be accessed via commands delivered via a physical or logical :abbr:`IPMB (Intelligent Platform Management Bus)`.

There is no high level API for this command, it is sent with the **send_message_with_name** method. The response has the following fields:

  * ``capabilities_flags`` with the bits ``intrusion_sensor``, ``frontpanel_lockout``, ``diagnostic_interrupt`` and ``power_interlock``
  * ``fru_info_device_address``
  * ``sdr_device_address``
  * ``sel_device_address``
  * ``system_management_device_address``
  * ``bridge_device_address``, None if the response does not contain it

For example:

.. code:: python

   rsp = ipmi.send_message_with_name('GetChassisCapabilities')
   if rsp.capabilities_flags.intrusion_sensor:
       print('chassis intrusion sensor present')
   print('SEL device address: 0x%02x' % rsp.sel_device_address)

Get Chassis Status Command
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command returns information regarding the high-level status of the system chassis and main power subsystem.

+--------------------------------------+
| **get_chassis_status()**             |
+--------------------------------------+

where the returned :class:`~pyipmi.chassis.ChassisStatus` object has the following attributes:

  * ``power_on``, ``overload``, ``interlock``, ``fault`` and ``control_fault``: the current power state as booleans
  * ``restore_policy``: the power restore policy after an AC power loss

    - 0: the chassis stays powered off
    - 1: the power is restored to the state before the AC power loss
    - 2: the chassis always powers up
    - 3: unknown

  * ``last_event``: a list with the causes of the last power event, the possible entries are ``'ac_failed'``, ``'overload'``, ``'interlock'``, ``'fault'`` and ``'power_on_via_ipmi'``
  * ``chassis_state``: a list with the active chassis states, the possible entries are ``'intrusion'``, ``'front_panel_lockout'``, ``'drive_fault'`` and ``'cooling_fault'``
  * ``id_cmd_state_info_support``: True if the chassis identify state is reported in ``chassis_id_state``
  * ``chassis_id_state``: the chassis identify state (0: off, 1: temporary on, 2: indefinite on)
  * ``front_panel_button_capabilities``: the optional front panel button capabilities and disable/enable status, None if the response does not contain them

For example:

.. code:: python

   status = ipmi.get_chassis_status()
   if status.power_on:
       print('the system power is on')
   if 'intrusion' in status.chassis_state:
       print('the chassis is open')


Chassis Control Command
~~~~~~~~~~~~~~~~~~~~~~~

This command provides a mechanism for providing power up, power down, and reset control.

+-----------------------------------------+
| **chassis_control(option)**             |
+-----------------------------------------+

where the ``option`` argument can take the following integer values as defined in the standard, the constants are defined in ``pyipmi.chassis``:

 - CONTROL_POWER_DOWN = 0
 - CONTROL_POWER_UP = 1
 - CONTROL_POWER_CYCLE = 2
 - CONTROL_HARD_RESET = 3
 - CONTROL_DIAGNOSTIC_INTERRUPT = 4
 - CONTROL_SOFT_SHUTDOWN = 5


For example:

.. code:: python

   from pyipmi.chassis import CONTROL_POWER_CYCLE

   ipmi.chassis_control(CONTROL_POWER_CYCLE)

There are methods defined for each of the above options:

.. code:: python

   ipmi.chassis_control_power_down()
   ipmi.chassis_control_power_up()
   ipmi.chassis_control_power_cycle()
   ipmi.chassis_control_hard_reset()
   ipmi.chassis_control_diagnostic_interrupt()
   ipmi.chassis_control_soft_shutdown()


Get/Set System Boot Options Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These commands read and write the boot option parameters, which tell the BIOS from which device the system boots.

The boot flags parameter is supported by a high level API:

+--------------------------------------------------------------------+
| **get_boot_device()**                                              |
+--------------------------------------------------------------------+
| **get_boot_mode()**                                                |
+--------------------------------------------------------------------+
| **get_boot_persistency()**                                         |
+--------------------------------------------------------------------+
| **set_boot_options(boot_device, boot_mode, boot_persistency)**     |
+--------------------------------------------------------------------+

where

  * ``boot_device`` is a :class:`~pyipmi.chassis.BootDevice`, the possible values are ``NO_OVERRIDE``, ``PXE``, ``DEFAULT_HDD``, ``DEFAULT_HDD_SAFE``, ``DIAGNOSTIC``, ``CD``, ``BIOS``, ``REMOTE_USB``, ``PRIMARY_REMOTE``, ``REMOTE_CD``, ``REMOTE_HDD`` and ``PRIMARY_USB``
  * ``boot_mode`` is ``'legacy'`` or ``'efi'``
  * ``boot_persistency`` is True if the boot options apply to all future boots, False if they apply to the next boot only

For example, boot from the network on the next boot only:

.. code:: python

   from pyipmi.chassis import BootDevice

   ipmi.set_boot_options(BootDevice.PXE, 'efi', False)

   device = ipmi.get_boot_device()      # BootDevice.PXE
   mode = ipmi.get_boot_mode()          # 'efi'
   persistent = ipmi.get_boot_persistency()  # False

The other boot option parameters are read and written as raw data. The parameter selectors are defined as ``BOOT_PARAMETER_*`` constants in ``pyipmi.chassis``:

+-----------------------------------------------------------------------------------+
| **get_system_boot_options(parameter_selector, set_selector=0, block_selector=0)** |
+-----------------------------------------------------------------------------------+
| **set_system_boot_options(parameter_selector, data, mark_parameter_invalid=0)**   |
+-----------------------------------------------------------------------------------+

For example:

.. code:: python

   from pyipmi.chassis import BOOT_PARAMETER_BOOT_INFO_ACKNOWLEDGE

   data = ipmi.get_system_boot_options(BOOT_PARAMETER_BOOT_INFO_ACKNOWLEDGE)


Get POH Counter Command
~~~~~~~~~~~~~~~~~~~~~~~

This command returns the Power-On Hours (POH) counter. There is no high level API for this command, it is sent with the **send_message_with_name** method. The response contains the ``counter_reading`` and the ``minutes_per_count``.

For example:

.. code:: python

   rsp = ipmi.send_message_with_name('GetPohCounter')
   hours = rsp.counter_reading * rsp.minutes_per_count / 60


.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
