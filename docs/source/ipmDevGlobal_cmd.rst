IPM Device "Global" Commands
============================

This section describes the high level :abbr:`API (Application Programming Interface)` for the commands that are common to all :abbr:`IPM (Intelligent Platform Management)` devices that follow the :abbr:`IPMI (Intelligent Platform Management Interface)` standard. The `IPMI standard`_ defines the following IPM Device "Global" commands:

+-------------------------------+-----+---------+-----+
| Command                       | O/M | Support | API |
+===============================+=====+=========+=====+
| Get Device ID                 | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Cold Reset                    | O   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Warm Reset                    | O   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Get Self Test Results         | M   | Yes     | No  |
+-------------------------------+-----+---------+-----+
| Manufacturing Test On         | O   | Yes     | No  |
+-------------------------------+-----+---------+-----+
| Get ACPI Power State          | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Set ACPI Power State          | O   | No      | No  |
+-------------------------------+-----+---------+-----+
| Get Device GUID               | O   | No      | No  |
+-------------------------------+-----+---------+-----+

.. note::
 
   - O/M - Optional/Mandatory command as stated by the IPMI standard
   - Support - Supported command by **send_message_with_name** method
   - API - High level API support implemented in this library

Get Device ID command:
~~~~~~~~~~~~~~~~~~~~~~

You can retrieve the Intelligent Devices's HW revision, FW/SW revision, and information regarding aditional logical device functionality with

+------------------------------+
| **get_device_id()**          |
+------------------------------+

where the returned object has the following attributes shown in the order as appear in the table of the `IPMI standard`_:

  * ``device_id``
  * ``provides_sdrs``
  * ``revision``
  * ``available``
  * ``fw_revision.minor (fw_revision.major, fw_revision.minor)``
  * ``ipmi_version (ipmi_version.major, ipmi_version.minor)``
  * ``supported_functions``
  * ``manufacturer_id``
  * ``product_id``
  * ``aux``

The returned object also has a method ``supports_function(func_name)`` where the argument can be one of the following (not case sensitive):

  * **'sensor'**
  * **'sdr_repository'**
  * **'sel'**
  * **'fru_inventory'**
  * **'ipmb_event_receiver'**
  * **'ipmb_event_generator'**
  * **'bridge'**
  * **'chassis'**

The method returns **'True'** if the given function is supported by the **Target**, otherwise is **'False'**.

For example:

.. code:: python

    device_id = ipmi.get_device_id()
    
    functions = (
            ('SENSOR', 'Sensor Device', 11),
            ('SDR_REPOSITORY', 'SDR Repository Device', 3),
            ('SEL', 'SEL Device', 14),
            ('FRU_INVENTORY', 'FRU Inventory Device', 4),
            ('IPMB_EVENT_RECEIVER', 'IPMB Event Receiver', 5),
            ('IPMB_EVENT_GENERATOR', 'IPMB Event Generator', 4),
            ('BRIDGE', 'Bridge', 18),
            ('CHASSIS', 'Chassis Device', 10))
    ChkBox=['[ ]','[X]']
    print('''\n
    Device ID:                  %(device_id)s
    Provides Device SDRs:       %(provides_sdrs)s
    Device Revision:            %(revision)s
    Device Available:           %(available)d
    Firmware Revision:          %(fw_revision)s
    IPMI Version:               %(ipmi_version)s
    Manufacturer ID:            %(manufacturer_id)d (0x%(manufacturer_id)04x)
    Product ID:                 %(product_id)d (0x%(product_id)04x)
    Aux Firmware Rev Info:      %(aux)s
    Additional Device Support: '''[1:-1] % device_id.__dict__)
    for n, s, l in functions:
        if device_id.supports_function(n):
            print('        %s%s%s' % (s,l*' ',ChkBox[1]))
        else:
            print('        %s%s%s' % (s,l*' ',ChkBox[0]))


Cold Reset command:
~~~~~~~~~~~~~~~~~~~

This command directs the **Target** to perform a 'Cold Reset' of itself. The device reinitalizes its event, communcation, and sensor funtioncs. Self Test, if implemented, will be also run.

+------------------------------+
| **cold_reset()**             |
+------------------------------+

For example:

.. code:: python

   ipmi.cold_reset()

Warm Reset command:
~~~~~~~~~~~~~~~~~~~

This command directs the **Target** to perform a 'Warm Reset' of itself. Communication interfaces are reset, but current configurations of interrupt enables, thresholds, etc. will be left alone, and no Selft Test initiated.

+------------------------------+
| **warm_reset()**             |
+------------------------------+

For example:

.. code:: python

   ipmi.warm_reset()

.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
