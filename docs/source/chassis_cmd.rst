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
| Set System Boot Options       | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Get System Boot Options       | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Get POH Counter               | O   | Yes     | No  |
+-------------------------------+-----+---------+-----+

.. note::
 
   - O/M - Optional/Mandatory command as stated by the IPMI standard
   - Support - Supported command by **send_message_with_name** method
   - API - High level API support implemented in this library

Get Chassis Capabilities Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command returns information about which main chassis management functions are present on the :abbr:`IPMB (Intelligent Platform Management Bus)` and what addresses are used to access those functions. This command is used to find the devices that provide functions such as :abbr:`SEL (System Event Log)`, :abbr:`SDR (Snesor Data Record)`, and :abbr:`ICMB (Intelligent Chassis Management Bus)` Bridging so that theyt can be accessed via commands delivered via a physical or logical :abbr:`IPMB (Intelligent Platform Management Bus)`.

+-------------------------------------+
| **get_chassis_capabilities()**      |
+-------------------------------------+

**NOT IMPLEMENTED YET!!!**

Get Chassis Status Command
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command returns information regarding the high-level status of the system chassis and main power subsystem.

+--------------------------------------+
| **get_chassis_status()**             |
+--------------------------------------+

where the returned object has the following attributes shown in the order as they appear in the table of the `IPMI standard`_:

  * ``restore_policy``
  * ``control_fault``
  * ``fault``
  * ``interlock``
  * ``overload``
  * ``power_on``
  * ``last_event``
  * ``chassis_state``

For example:

.. code:: python

   chassis_status=ipmi.get_chassis_status()


Chassis Control Command
~~~~~~~~~~~~~~~~~~~~~~~

This command provides a mechanism for providing power up, power down, and reset control.

+-----------------------------------------+
| **chassis_control(option)**             |
+-----------------------------------------+

where the ``option`` argument can take the following integer values as defined in the standard:

 - CONTROL_POWER_DOWN = 0
 - CONTROL_POWER_UP = 1
 - CONTROL_POWER_CYCLE = 2
 - CONTROL_HARD_RESET = 3
 - CONTROL_DIAGNOSTIC_INTERRUPT = 4
 - CONTROL_SOFT_SHUTDOWN = 5


For example:

.. code:: python

   ipmi.chassis_control(option)

There are methods defined for each of the above options:

.. code:: python

   ipmi.chassis_control_power_down()
   ipmi.chassis_control_power_up()
   ipmi.chassis_control_power_cycle()
   ipmi.chassis_control_hard_reset()
   ipmi.chassis_control_diagnostic_interrupt()
   ipmi.chassis_control_soft_shutdown()


.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
