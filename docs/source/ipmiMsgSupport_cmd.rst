IPMI Messaging Support Commands
===============================

This section describes the commands used to support the system messaging interfaces. This includes control bits for using the :abbr:`BMC (Board Management Controller)` as an Event receiver and :abbr:`SEL (System Event Log)` Device. :abbr:`SMM (System Management Mode)` Messaging and Event Message Buffer support is optional. The `IPMI standard`_ defines the following IPMI Messaging Support commands:

+-----------------------------------------+-----+---------+-----+
| Command                                 | O/M | Support | API |
+=========================================+=====+=========+=====+
| Set BMC Global Enables                  | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Get BMC Global Enables                  | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Clear Message Flags                     | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Get Message Flags                       | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Enable Message Channel Receive          | O   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Get Message                             | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Send Message                            | M   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Read Event Message Buffer               | O   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Get System Interface Capabilities       | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get BT Interface Capabilities           | M   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Master Write-Read                       | M   | Yes     | Yes |
+-----------------------------------------+-----+---------+-----+
| Get System GUID                         | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set System Info                         | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get System Info                         | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get Channel Authentication Capabilities | O   | Yes     | Yes |
+-----------------------------------------+-----+---------+-----+
| Get Channel Cipher Suites               | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get Session Challenge                   | O   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Activate Session                        | O   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Set Session Privilege Level             | O   | Yes     | No  |
+-----------------------------------------+-----+---------+-----+
| Close Session                           | O   | Yes     | Yes |
+-----------------------------------------+-----+---------+-----+
| Get Session Info                        | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get AuthCode                            | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set Channel Access                      | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get Channel Access                      | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get Channel Info                        | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set Channel Security Keys               | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set User Access                         | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get User Access                         | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set User Name                           | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Get User Name                           | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+
| Set User Password                       | O   | No      | No  |
+-----------------------------------------+-----+---------+-----+

.. note::
 
   - O/M - Optional/Mandatory command as stated by the IPMI standard
   - Support - Supported command by **send_message_with_name** method
   - API - High level API support implemented in this library

Establish Session
~~~~~~~~~~~~~~~~~

This is not equivalent with a single IPMI command, but represents a high level API function using several IPMI commands. It is used to establish a session between the **Slave** and the **Target**. The method

+------------------------------+
| **establish()**              |
+------------------------------+

creates and activates a session of the ``ipmi.session`` instance with the given authentication and privilige level. Multiple IPMI commands are used to establish the session. The following steps are done during the session establishment for an RMCP interface:

  - ping the **Target** IP address
  - issue a **"Get Channel Authentication Capabilities"** command
  - issue a **"Get Session Challenge"** command
  - issue an **"Activate Session"** command
  - issue a **"Set Session Privilege Level"** command (privilige is set always to ADMINISTRATOR level)

If ``keep_alive_interval`` argument for the interface instantiation was set to a nonzero value then the channel is kept alive by regularly sending the **"Get Device ID"** IPMI command.

Example of establishing a session:

.. code:: python

  ipmi.session.establsih()

Get Channel Authentication Capabilities Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command is used to retrieve capability information about a particular channel.

+-----------------------------------------------------------------+
| **get_channel_authentication_capabilities(channel, priv_lvl)**  |
+-----------------------------------------------------------------+

You should pass the channel number to ``channel``, and the requested maximum privilige level to ``priv_lvl``.

Example:

.. code:: python

  ipmi.get_channel_authentication_capabilities(channel=0x0E,priv_lvl=1)


Master Write-Read Command
~~~~~~~~~~~~~~~~~~~~~~~~~

This command can be used for low level |I2C|/SMBus write, read, or write-read accesses to the IPMB or private busses behind a management controller. The command can also be used for providing low-level access to devices that provide an SMBus slave interface.

+---------------------------------------------------------------------------+
| **i2c_write_read(bus_type, bus_id, channel, address, count, data=None)**  |
+---------------------------------------------------------------------------+



Close Session Command
~~~~~~~~~~~~~~~~~~~~~

This command is used to immediately terminate a session in progress. The method

+------------------------------+
| **close()**                  |
+------------------------------+

closes the session of the ``ipmi.session`` instance. Example of closing a session:

.. code:: python

  ipmi.session.close()


.. _IPMI standard: https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
.. |I2C| replace:: I\ :sup:`2`\ C

