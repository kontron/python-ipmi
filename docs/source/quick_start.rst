Quick start
===========

Importing the library
---------------------

After you successfully installed the **python-ipmi** library, import it in your python environment:

.. code:: python
  
  import pyipmi
  import pyipmi.interfaces

Creating the session
--------------------

Authenticated :abbr:`IPMI (Intelligent Platform Management Interface)` communication to the :abbr:`BMC (Board Management Controller)` is accomplished by establishing a session. Once established, a session is identified by a Session ID. The Session ID identifies a connection between a given remote user and :abbr:`BMC (Board Management Controller)`, using either the :abbr:`LAN (Local Area Network)` or Serial/Modem connection.

Before establishing the session the interface type shall be defined. There are 4 interface types included in this library:

  * **'rmcp'** - using native :abbr:`RMCP (Remote Management Control Protocol)` encapsulation over :abbr:`LAN (Local Area Network)` (so called :abbr:`IPMI (Intelligent Platform Management Interface)` over :abbr:`LAN (Local Area Network)`). This interface requires only common python libraries.
  * **'ipmitool'** - so called legacy :abbr:`RMCP (Remote Management Control Protocol)`, still an :abbr:`IPMI (Intelligent Platform Management Interface)` over :abbr:`LAN (Local Area Network)`, but requires IPMITOOL as backend. This interface requires `ipmitool`_  compiled and installed, and each time an ipmitool command is issued a new session is established with the Target (left for legacy purposes; used before native rmcp was not implemented yet).
  * **'aardvark'** - :abbr:`IPMB (Intelligent Platform Management Bus)` interface (using the `Total Phase`_ Aardvark)
  * **'mock'** - This interface uses the ipmitool raw command to "emulate" an :abbr:`RMCP (Remote Management Control Protocol)` session. It uses the session information to assemble the correct ipmitool parameters. Therefore, a session must be established before any request can be sent.

Then you create an instance of the ``pyipmi.Ipmi`` object using the ``interface`` instance just created, and set also the required parameters of the interface type. You should also set the :abbr:`IPMI (Intelligent Platform Management Interface)` **Target**, otherwise different runtime errors shall be expected later on when invoking methods of this library. Finally, you can try to establish a session. If there is a connection problem (no response), then you get the following error during session establishment: 

.. error::

  timeout: timed out 

This runtime error occurs anytime with any method in case of no response.

Native RMCP interface
*********************

Here is an example to create a native :abbr:`RMCP (Remote Management Control Protocol)` interface:

.. code:: python 

  interface = pyipmi.interfaces.create_interface(interface='rmcp',
                                               slave_address=0x81,
                                               host_target_address=0x20,
                                               keep_alive_interval=1)
  ipmi = pyipmi.create_connection(interface)
  ipmi.session.set_session_type_rmcp(host='10.0.114.199', port=623)
  ipmi.session.set_auth_type_user(username='admin', password='admin')
  
  ipmi.target = pyipmi.Target(ipmb_address=0x20)

  ipmi.session.establish()
  device_id = ipmi.get_device_id()

  # Below code used only to print out the device ID information
  print('''
  Device ID:          %(device_id)s
  Device Revision:    %(revision)s
  Firmware Revision:  %(fw_revision)s
  IPMI Version:       %(ipmi_version)s
  Manufacturer ID:    %(manufacturer_id)d (0x%(manufacturer_id)04x)
  Product ID:         %(product_id)d (0x%(product_id)04x)
  Device Available:   %(available)d
  Provides SDRs:      %(provides_sdrs)d
  Additional Device Support:
  '''[1:-1] % device_id.__dict__)
  functions = (
          ('SENSOR', 'Sensor Device'),
          ('SDR_REPOSITORY', 'SDR Repository Device'),
          ('SEL', 'SEL Device'),
          ('FRU_INVENTORY', 'FRU Inventory Device'),
          ('IPMB_EVENT_RECEIVER', 'IPMB Event Receiver'),
          ('IPMB_EVENT_GENERATOR', 'IPMB Event Generator'),
          ('BRIDGE', 'Bridge'),
          ('CHASSIS', 'Chassis Device')
  )
  for n, s in functions:
      if device_id.supports_function(n):
          print('  %s' % s)
  if device_id.aux is not None:
      print('Aux Firmware Rev Info:  [%s]' % (
              ' '.join('0x%02x' % d for d in device_id.aux)))

For ``create_interface`` method the first argument tells that a native RMCP interface shall be created, while for the rest of the arguments the default values are shown. After creating an instance of the ``interface`` object the interface parameters shall be set with ``set_session_type_rmcp`` and ``set_auth_type_user`` methods of the session as shown above. If authentication fails during session establishment an error of the following form shall be expected:

.. error::

  CompletionCodeError: CompletionCodeError cc=0x81 desc=Unknown error description


Legacy RMCP interface with IPMITOOL as backend
**********************************************

An example showing how to setup the interface and the connection using the ipmitool as backend with network interface:

.. code:: python

  interface = pyipmi.interfaces.create_interface(interface='ipmitool', 
                                                 interface_type='lan')
  ipmi = pyipmi.create_connection(interface)
  ipmi.session.set_session_type_rmcp('10.0.0.1', port=623)
  ipmi.session.set_auth_type_user('admin', 'admin')

  ipmi.target = pyipmi.Target(ipmb_address=0x82, routing=[(0x81,0x20,0),(0x20,0x82,7)])

  ipmi.session.establish()
  ipmi.get_device_id()

where in the ``create_interface`` method the supported interface types for ipmitool are **'lan'** , **'lanplus'**, and **'serial-terminal'**. When setting the **Target**, the ``ipmb_address`` argument represents the :abbr:`IPMI (Intelligent Platform Management Interface)` target address, and ``routing`` argument represents the bridging information over which a target is reachable. The path is given as a list of tuples in the form (address, bridge_channel). Here are three examples to have a better understanding about the format of the routing:

* **Example #1**: access to an :abbr:`ATCA (Advanced Telecommunication Computing Architecture)` blade in a chassis

  - slave = 0x81, target = 0x82
  - routing = [(0x81,0x20,0),(0x20,0x82,None)]


.. graphviz::

    digraph g{
      rankdir=LR;
    
      nd1 [label="0x81"]
      nd2 [label="0x20"]
      nd3 [label="0x82"]
      nd4 [label="0x20"]
     
      nd1 -> nd2 [label="channel=0"]
      nd2 -> nd3 -> nd4
      
      subgraph cluster0 {
        label="Slave"
        nd1;
      }
      subgraph cluster3 {
        label="Chassis"
        subgraph cluster1 {
          label="ATCA Blade (Target)"
          nd3;
          nd4;
        }
        nd2;
        }
      }
    }


* **Example #2**: access to an :abbr:`MMC (Module Management Controller)` of an :abbr:`AMC (Advanced Mezzanine Card)` plugged into a :abbr:`CM (Carrier Module)` in a :abbr:`uTCA (Micro Telecommunication Computing Architecture)`-:abbr:`MCH (MicroTCA Carrier Hub)` chassis with :abbr:`ShMC (Shelf Management Controller)`

  - slave = 0x81, target = 0x72
  - routing = [(0x81,0x20,0),(0x20,0x82,7),(0x20,0x72,None)]

.. graphviz::

    digraph g{
      rankdir=LR;
    
      nd1 [label="0x81"]
      nd2 [label="0x20"]
      nd3 [label="0x82"]
      nd4 [label="0x20"]
      nd5 [label="0x72"]
    
      nd1 -> nd2 [label="channel=0"]
      nd2 -> nd3 -> nd4
      nd4 -> nd5 [label="channel=7"]
      
      subgraph cluster0 {
        label="Slave"
        nd1;
      }
      subgraph cluster3 {
        label="uTCA - MCH"
        subgraph cluster1 {
          label="CM"
          nd3;
          nd4;
        }
        subgraph cluster2 {
          label="ShMC"
          nd2;
        }
      }
      subgraph cluster5 {
        label="AMC (Target)"
        subgraph cluster4 {
          label="MMC"
          nd5;
        }
      }
    }


* **Example #3**: access to an :abbr:`MMC (Module Management Controller)` of an :abbr:`AMC (Advanced Mezzanine Card)` plugged into :abbr:`ATCA (Advanced Telecommunication Computing Architecture)` :abbr:`AMC (Advanced Mezzanine Card)` carrier

  - slave = 0x81, target = 0x72
  - routing = [(0x81,0x20,0),(0x20,0x8e,7),(0x20,0x80,None)]

.. graphviz::

    digraph g{
      rankdir=LR;
    
      nd1 [label="0x81"]
      nd2 [label="0x20"]
      nd3 [label="0x8E"]
      nd4 [label="0x20"]
      nd5 [label="0x80"]
    
      nd1 -> nd2 [label="channel=0"]
      nd2 -> nd3 -> nd4
      nd4 -> nd5 [label="channel=7"]
     
      subgraph cluster0 {
        label="Slave"
        nd1;
      }
      subgraph cluster3 {
        label="ATCA"
        subgraph cluster1 {
          label="AMC Carrier"
          nd3;
          nd4;
        }
        nd2;
      }
      subgraph cluster5 {
        label="AMC (Target)"
        subgraph cluster4 {
          label="MMC"
          nd5;
        }
      }
    }


ipmitool command:

.. code:: shell

    ipmitool -I lan -H 10.0.0.1 -p 623 -U "admin" -P "admin" -t 0x82 -b 0 -l 0 raw 0x06 0x01

An example that shows how to setup the interface and the connection using the ipmitool as backend with serial interfaces:

.. code:: python

  interface = pyipmi.interfaces.create_interface(interface='ipmitool', 
                                                 interface_type='serial-terminal')
  ipmi = pyipmi.create_connection(interface)
  ipmi.session.set_session_type_serial('/dev/tty2', 115200)

  ipmi.target = pyipmi.Target(0xb2)

  ipmi.session.establish()
  ipmi.get_device_id()

ipmitool command:

.. code:: shell

    ipmitool -I serial-terminal -D /dev/tty2:115200 -t 0xb2 -l 0 raw 0x06 0x01

System interface with the Linux IPMI driver
*******************************************

The ``ipmidev`` interface uses the Linux IPMI driver (``ipmi_devintf`` with e.g. ``ipmi_si`` for KCS, SMIC and BT or ``ipmi_ssif``) to access the system interface of the BMC via ``/dev/ipmi0``. No session is needed.

.. code:: python

  interface = pyipmi.interfaces.create_interface('ipmidev', port='/dev/ipmi0')
  ipmi = pyipmi.create_connection(interface)
  ipmi.target = pyipmi.Target(0x20)
  ipmi.open()
  ipmi.get_device_id()

Requests to the BMC (no target address or ``0x20``) are sent to the system interface. Requests to other targets are bridged by the BMC: either to the target IPMB address on channel 0 or, with a routing of one bridge, on the given channel, e.g. ``pyipmi.Target(0x72, routing=[(0x20, 0x20, 7), (0x20, 0x72, None)])``. Bridging over more than one hop is not supported.

ipmitool command:

.. code:: shell

    ipmitool.py -I ipmidev bmc info

IPMB with openipmblink
**********************

For :abbr:`IPMB (Intelligent Platform Management Bus)` interface with the openipmblink bridge, pass the bridge's data serial port and the IPMB bus number (0 or 1). The own IPMB address of that bus is set to ``slave_address`` when the interface is opened.

.. code:: python

  interface = pyipmi.interfaces.create_interface('openipmblink',
                                               slave_address=0x20,
                                               port='/dev/ttyACM1',
                                               bus=0)
  ipmi = pyipmi.create_connection(interface)
  ipmi.target = pyipmi.Target(ipmb_address=0xb4)
  ipmi.open()
  device_id = ipmi.get_device_id()

Both buses of the bridge can be used at the same time; the interfaces share the serial port.

The interface also answers requests addressed to its own IPMB address. This works the same way for all IPMB interfaces (``openipmblink``, ``aardvark`` and ``ipmbdev``), each takes a ``router`` argument. Incoming messages are passed to a ``MessageRouter``: responses are matched to the pending requests, requests are passed to the handler registered for their NetFn and command. Requests without a handler get completion code ``0xC1`` (invalid command). Without a router, incoming requests are ignored.

.. code:: python

  from pyipmi.interfaces.router import MessageRouter
  from pyipmi.msgs import bmc, constants

  def get_device_id(req):
      rsp = bmc.GetDeviceIdRsp()
      rsp.completion_code = constants.CC_OK
      rsp.device_id = 0x12
      return rsp

  router = MessageRouter()
  router.register_handler(constants.NETFN_APP, constants.CMDID_GET_DEVICE_ID,
                          get_device_id)
  interface = pyipmi.interfaces.create_interface('openipmblink',
                                               slave_address=0x20,
                                               port='/dev/ttyACM1',
                                               bus=0,
                                               router=router)
  interface.open()

Handlers run in a worker thread of the router. ``register_raw_handler()`` registers a handler that gets the interface, the IPMB header and the raw request data and returns the raw response data. See ``examples/interface_openipmblink.py`` for the bridge self-test.

The ``port`` can also be a pyserial URL, e.g. ``socket://localhost:5555`` for a bridge shared over TCP. ``examples/bmc_openipmblink.py`` runs a BMC on bus 1 and shares the bridge this way, so ``ipmitool.py`` can send requests from bus 0:

.. code:: shell

  ipmitool.py -I openipmblink -o port=socket://localhost:5555,bus=0,address=0x24 -t 0x20 bmc info

IPMB with Aardvark
******************

For :abbr:`IPMB (Intelligent Platform Management Bus)` interface with Aardvark tool you should use the following code:

.. code:: python

  interface = pyipmi.interfaces.create_interface('aardvark',
                                               slave_address=0x20,
                                               serial_number='2237-523145')
  ipmi = pyipmi.create_connection(interface)
  ipmi.target = pyipmi.Target(ipmb_address=0xb4)
  device_id = ipmi.get_device_id()

  # Below code used only to print out the device ID information
  print('''
  Device ID:          %(device_id)s
  Device Revision:    %(revision)s
  Firmware Revision:  %(fw_revision)s
  IPMI Version:       %(ipmi_version)s
  Manufacturer ID:    %(manufacturer_id)d (0x%(manufacturer_id)04x)
  Product ID:         %(product_id)d (0x%(product_id)04x)
  Device Available:   %(available)d
  Provides SDRs:      %(provides_sdrs)d
  Additional Device Support:
  '''[1:-1] % device_id.__dict__)

  functions = (
          ('SENSOR', 'Sensor Device'),
          ('SDR_REPOSITORY', 'SDR Repository Device'),
          ('SEL', 'SEL Device'),
          ('FRU_INVENTORY', 'FRU Inventory Device'),
          ('IPMB_EVENT_RECEIVER', 'IPMB Event Receiver'),
          ('IPMB_EVENT_GENERATOR', 'IPMB Event Generator'),
          ('BRIDGE', 'Bridge'),
          ('CHASSIS', 'Chassis Device')
  )
  for n, s in functions:
      if device_id.supports_function(n):
          print('  %s' % s)

  if device_id.aux is not None:
      print('Aux Firmware Rev Info:  [%s]' % (
              ' '.join('0x%02x' % d for d in device_id.aux)))

Sending IPMI commands
---------------------

You can send an :abbr:`IPMI (Intelligent Platform Management Interface)` message using the predefined command name

+------------------------------------------------------------+
| **send_message_with_name(name, *args, **kwargs)**          |
+------------------------------------------------------------+

where the ``name`` argument represents the string name of the command as listed in the last column of table from `commands`_. For commands which do not require data to be sent name is the only argument to be passed.
The returned value is on object which types depend on the name of the issued command.

The following example requests the device ID:

.. code:: python

  ipmi.send_message_with_name('GetDeviceId')

.. note::

  The returned object in this case is different from the one shown for the native :abbr:`RMCP (Remote Management Control Protocol)` example shown above.

Closing the session
-------------------

When you finish, close your session with ``session_close`` method.

.. code:: python

  ipmi.session.close()

As a beginner, you might find useful the debugging capabilities of this library. You can use the logging of the **python-ipmi** library by setting the following lines:

.. code:: python

  import logging
  logging.basicConfig(filename='ipmi_debug.log', filemode='w', level=logging.DEBUG)

in which case debug, info and warning messages are all recorded in the **'ipmi_debug.log'** file.

.. note::

  It is assumed in all code examples that the instantiation of the ``pyipmi.Ipmi`` object is called **ipmi**, thus **ipmi** will proceed all the methods and attributes of the ``pyipmi.Ipmi`` object.

.. _Total Phase: http://www.totalphase.com
.. _ipmitool: http://sourceforge.net/projects/ipmitool/
.. _commands: https://github.com/kontron/python-ipmi/blob/master/docs/commands.rst
