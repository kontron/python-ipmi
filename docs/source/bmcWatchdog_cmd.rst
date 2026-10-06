BMC Watchdog Timer Commands
===========================

The :abbr:`BMC (Board Management Controller)` implements a standardized **'Watchdog Timer'** that can be used for a number of system timeout functions by system management software or by the :abbr:`BIOS (Basic Input Output System)`. Setting a timeout value of '0' allows the selected timeout action to occur immediately. This provides a standardized means for devices on the :abbr:`IPMB (Intelligent Platform Management Bus)` to perform emergency recovery actions. The `IPMI standard`_ defines the following BMC Watchdog Timer commands:

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

The methods and the returned classes are described in detail in the :doc:`api`.

Watchdog Timer Settings
~~~~~~~~~~~~~~~~~~~~~~~

The settings of the watchdog timer are the attributes of a :class:`~pyipmi.bmc.Watchdog` object. They are returned by ``get_watchdog_timer`` and passed to ``set_watchdog_timer``. The attributes are listed in the order as they appear in the table of the `IPMI standard`_:

  * ``timer_use``: the use of the timer, one of the constants

    - ``Watchdog.TIMER_USE_BIOS_FRB2`` = 1
    - ``Watchdog.TIMER_USE_BIOS_POST`` = 2
    - ``Watchdog.TIMER_USE_OS_LOAD`` = 3
    - ``Watchdog.TIMER_USE_SMS_OS`` = 4
    - ``Watchdog.TIMER_USE_OEM`` = 5

  * ``dont_stop``: only used by ``set_watchdog_timer``, True to keep a running timer running, False to stop it
  * ``is_running``: only returned by ``get_watchdog_timer``, True if the timer is running
  * ``dont_log``: True to not log the timer expiration in the :abbr:`SEL (System Event Log)`
  * ``timeout_action``: the action on the timer expiration, one of the constants

    - ``Watchdog.TIMEOUT_ACTION_NO_ACTION`` = 0
    - ``Watchdog.TIMEOUT_ACTION_HARD_RESET`` = 1
    - ``Watchdog.TIMEOUT_ACTION_POWER_DOWN`` = 2
    - ``Watchdog.TIMEOUT_ACTION_POWER_CYCLE`` = 3

  * ``pre_timeout_interrupt``: the interrupt before the timeout action, 0 for none, 1 for SMI, 2 for NMI / diagnostic interrupt, 3 for a messaging interrupt
  * ``pre_timeout_interval``: the time in seconds before the timeout action at which the pre-timeout interrupt is generated
  * ``timer_use_expiration_flags``: a bit mask with one bit per timer use, bit 1 for BIOS FRB2 up to bit 5 for OEM. ``get_watchdog_timer`` returns the timer uses whose timer expired, ``set_watchdog_timer`` clears the flags of the set bits.
  * ``initial_countdown``: the countdown value in 100 ms units
  * ``present_countdown``: only returned by ``get_watchdog_timer``, the present countdown value in 100 ms units

Reset Watchdog Timer Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command is used for starting and restarting the **Watchdog Timer** from the initial countdown value that was specified with the ``set_watchdog_timer`` method (see next command). If the timer was not set before, the BMC returns the completion code 0x80, which raises a ``CompletionCodeError``.

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

where ``watchdog_timer`` has the settings described above. All settings except ``is_running`` and ``present_countdown`` have to be set.

For example, configure the timer to reset the system after 60 seconds, then start it:

.. code:: python

   from pyipmi.bmc import Watchdog

   watchdog_timer = Watchdog()
   watchdog_timer.timer_use = Watchdog.TIMER_USE_SMS_OS
   watchdog_timer.dont_stop = False
   watchdog_timer.dont_log = False
   watchdog_timer.timeout_action = Watchdog.TIMEOUT_ACTION_HARD_RESET
   watchdog_timer.pre_timeout_interrupt = 0
   watchdog_timer.pre_timeout_interval = 0
   watchdog_timer.timer_use_expiration_flags = 0
   watchdog_timer.initial_countdown = 600   # 100 ms units
   ipmi.set_watchdog_timer(watchdog_timer)

   ipmi.reset_watchdog_timer()   # start the timer

The settings returned by ``get_watchdog_timer`` can be changed and set again. ``dont_stop`` is not returned, so set it to keep a running timer running:

.. code:: python

   watchdog_timer = ipmi.get_watchdog_timer()
   watchdog_timer.initial_countdown = 1200
   watchdog_timer.dont_stop = watchdog_timer.is_running
   ipmi.set_watchdog_timer(watchdog_timer)

Get Watchdog Timer Command
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command retrieves the current settings and present countdown of the watchdog timer.

+------------------------------+
| **get_watchdog_timer()**     |
+------------------------------+

where the returned :class:`~pyipmi.bmc.Watchdog` object has the settings described above.

For example:

.. code:: python

    watchdog_timer = ipmi.get_watchdog_timer()

    timer_uses = {1: 'BIOS FRB2', 2: 'BIOS/POST', 3: 'OS Load',
                  4: 'SMS/OS', 5: 'OEM'}
    interrupts = ['None', 'SMI', 'NMI', 'Msg intr']
    actions = ['No action', 'Hard Reset', 'Power Down', 'Power Cycle']
    expired = [name for bit, name in timer_uses.items()
               if watchdog_timer.timer_use_expiration_flags & (1 << bit)]

    print('Timer use:              ', timer_uses.get(watchdog_timer.timer_use))
    print('Timer is running:       ', watchdog_timer.is_running)
    print("Don't log:              ", watchdog_timer.dont_log)
    print('Timeout action:         ', actions[watchdog_timer.timeout_action])
    print('Pre-timeout interrupt:  ',
          interrupts[watchdog_timer.pre_timeout_interrupt])
    print('Pre-timeout interval:    %d s' % watchdog_timer.pre_timeout_interval)
    print('Expired timer uses:     ', ', '.join(expired) or 'none')
    print('Initial countdown:       %.1f s'
          % (watchdog_timer.initial_countdown / 10))
    print('Present countdown:       %.1f s'
          % (watchdog_timer.present_countdown / 10))


.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
