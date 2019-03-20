BMC Watchdog Timer Commands
===========================

The :abbr:`BMC (Board Management Controller)` implements a standardized **'Watchdog Timer'** that can be used for a number of system timeout functions by system management software or by the :abbr:`BIOS (Basic Input Output System)`. Setting a timeout value of '0' allows the selected timeout action to occur immediately. This provides a standardized means for devices on the :abbr:`IPMB (Intelligent Platform Management Bus)` to performs emergency recovery actions. The `IPMI standard`_ defines the following BMC Watchdog Timer commands:

+-------------------------------+-----+---------+-----+
| Command                       | O/M | Support | API |
+===============================+=====+=========+=====+
| Reset Watchdog Timer          | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Set Watchdog Timer            | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+
| Get Watchdog Timer            | M   | Yes     | Yes |
+-------------------------------+-----+---------+-----+

.. note::
 
   - O/M - Optional/Mandatory command as stated by the IPMI standard
   - Support - Supported command by **send_message_with_name** method
   - API - High level API support implemented in this library

Reset Watchdog Timer Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command is used for starting and restarting the **Watchdog Timer** from the initial countdown value that was specified with ``set_watchdog_timer`` method (see next command). 

+------------------------------+
| **reset_watchdog_timer()**   |
+------------------------------+

For example:

.. code:: python

    ipmi.reset_watchdog_timer()
    
Set Watchdog Timer Command
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command is used to initialize and configure the **Watchdog Timer**. This command is also used for stopping the timer.

+----------------------------------------------+
| **set_watchdog_timer(watchdog_timer)**       |
+----------------------------------------------+

For example:

.. code:: python

   ipmi.set_watchdog_timer(watchdog_timer)

where the ``watchdog_timer`` has the attributes shown bellow for the next command.

Get Watchdog Timer Command
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command retrieves the current settings and present countdown of the watchdog timer.

+------------------------------+
| **get_watchdog_timer()**     |
+------------------------------+

where the returned object has the following attributes shown in the order as they appear in the table of the `IPMI standard`_:

  * ``dont_log``
  * ``is_running`` (``dont_stop``)
  * ``timer_use``
  * ``pre_timeout_interrupt``
  * ``timeout_action``
  * ``pre_timeout_interval``
  * ``timer_use_expiration_flags``
  * ``initial_countdown``
  * ``present_countdown``

The ``dont_stop`` attribute is not changed by the ``get_watchdog_timer`` method and used only by the ``set_watchdog_timer`` method.
 
For example:

.. code:: python

    watchdog_timer=ipmi.get_watchdog_timer()

    print("--- Printing Watchdog Timer ---")
    timer_use_const=['BIOS FRB2','BIOS/POST','OS Load','SMS/OS','OEM']
    pretime_intr_const=['None','SMI','NMI','Msg intr']
    timeout_act_const=['No action','Hard Reset','Power Down','Power Cycle']
    print("""
    Don't log:                  {0[dont_log]:}
    Timer is running:           {0[is_running]:}
    Pre-timout interval:        {0[pre_timeout_interval]:d}
    Initial countdown value:    {0[initial_countdown]:d}
    Present countdown value:    {0[present_countdown]:d}
    """[1:-1].format(wd_timer.__dict__),end='')
    print("    Timer use:                 ",
          timer_use_const[watchdog_timer.__dict__['timer_use']-1])
    print("    Timer use expiration flag: ",
          timer_use_const[watchdog_timer.__dict__['timer_use_expiration_flags']-1])
    print("    Pre-timeout interrupt:     ",
          pretime_intr_const[watchdog_timer.__dict__['pre_timeout_interval']])
    print("    Time out action:           ",
          timeout_act_const[watchdog_timer.__dict__['timeout_action']])


.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
