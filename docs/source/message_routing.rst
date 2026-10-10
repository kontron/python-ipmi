IPMB Message Routing
====================

The IPMB interfaces (``aardvark``, ``ipmbdev`` and ``openipmblink``) are
nodes on the IPMB with their own slave address. They do not only send
requests and wait for the responses, they receive every message addressed
to them, including requests from other devices. A
:class:`~pyipmi.interfaces.router.MessageRouter` decides what happens with
these messages: it passes the responses to the waiting requests and
answers the requests with handlers you register. With it, a program can
act as an IPMB device, e.g. a BMC, an MMC or a test responder, and use the
same interface to send its own requests.

The other interfaces (``rmcp``, ``rmcpplus``, ``ipmitool``, ``ipmidev``)
only send requests and have no message router.

How the router works
--------------------

.. graphviz::

   digraph routing {
       rankdir=LR;
       node [shape=box, fontname="sans-serif", fontsize=10];
       edge [fontname="sans-serif", fontsize=9];

       bus [label="IPMB", shape=ellipse];
       rx [label="Receive thread\nof the interface"];
       router [label="MessageRouter\nhandle_frame()"];
       pending [label="Pending request\n(request() waits)"];
       worker [label="Worker thread\nof the router"];
       handler [label="Registered handler\n(netfn, cmdid,\ngroup extension)"];

       bus -> rx [label=" message"];
       rx -> router;
       router -> pending [label=" response:\n matched by address,\n netfn, cmd, seq, LUN"];
       router -> worker [label=" request:\n queued"];
       worker -> handler;
       handler -> bus [label=" response, sent on the\n interface that received\n the request", style=dashed];
   }

* **Responses** are matched to the pending request by the responder
  address, network function, command ID, sequence number and LUN, and
  returned by the waiting ``request()``. A response without a matching
  request is dropped.
* **Requests** are queued and handled one after the other by a worker
  thread of the router, never in the receive thread of the interface.
  The handler of the request's network function and command ID is
  called, and its response is sent back on the interface that received
  the request.
* **Requests without a handler** are answered with the completion code
  ``unhandled_cc`` of the router, 0xC1 (invalid command) by default, or
  ignored if it is ``None``.
* Messages that are too short or have a wrong checksum are dropped.

Without a router, an interface uses a default router that sends requests
and ignores all incoming requests.

Setting up a responder
----------------------

#. Create a router.
#. Register a handler for each command to answer.
#. Pass the router to the interface with ``router=``. The interface
   receives on its ``slave_address``, so set it to the address the
   device answers on.
#. Open the interface. From then on, requests are answered in the
   background.
#. Close the interface, then the router. The interface does not close a
   router that was passed to it.

The example answers Get Device ID requests to the address 0x72 on bus 0
of an openipmblink bridge:

.. code-block:: python

   import threading

   import pyipmi.interfaces
   from pyipmi.interfaces.router import MessageRouter
   from pyipmi.msgs import bmc, constants


   def get_device_id(req):
       rsp = bmc.GetDeviceIdRsp()
       rsp.completion_code = constants.CC_OK
       rsp.device_id = 0x12
       rsp.firmware_revision.major = 1
       rsp.firmware_revision.minor = 0x05
       rsp.ipmi_version = 0x02
       rsp.manufacturer_id = 15000
       rsp.product_id = 0x1234
       return rsp


   router = MessageRouter()
   router.register_handler(constants.NETFN_APP,
                           constants.CMDID_GET_DEVICE_ID, get_device_id)

   interface = pyipmi.interfaces.create_interface(
       'openipmblink', slave_address=0x72, port='/dev/ttyACM1', bus=0,
       router=router)
   interface.open()
   try:
       threading.Event().wait()    # answer requests until Ctrl-C
   except KeyboardInterrupt:
       pass
   finally:
       interface.close()
       router.close()

The interfaces receive on their address differently: the ``aardvark``
adapter is enabled as I2C slave with ``slave_address``, ``openipmblink``
sets the address on the bus of the bridge, and for ``ipmbdev`` the
address is configured in the ``ipmb-dev-int`` driver, not by
``slave_address``.

Handlers
--------

There are two kinds of handlers. Both are registered for a network
function and a command ID, and optionally a group extension.

**Message handlers**, registered with
:meth:`~pyipmi.interfaces.router.MessageRouter.register_handler`, get the
decoded request message, e.g. a ``GetDeviceIdReq``, and return a response
message:

* A response with completion code 0 is sent with all its fields.
* A response with another completion code is sent as the completion code
  only, so the other fields need not be set:

  .. code-block:: python

     from pyipmi.msgs import fru

     def read_fru_data(req):
         rsp = fru.ReadFruDataRsp()
         if req.fru_id != 0:
             rsp.completion_code = constants.CC_REQ_DATA_NOT_PRESENT
             return rsp
         ...

* ``None`` sends no response.

**Raw handlers**, registered with
:meth:`~pyipmi.interfaces.router.MessageRouter.register_raw_handler`, get
the interface, the IPMB header and the request data (after the command
ID, without the checksum), and return the response data starting with
the completion code, or ``None``. Use them for commands without a message
class, or to see the header, e.g. the requester address:

.. code-block:: python

   def oem_command(interface, header, data):
       print(f'request from 0x{header.rq_sa:02x}: {data.hex()}')
       return bytes([constants.CC_OK, 0x01, 0x02])

   router.register_raw_handler(0x2e, 0x01, oem_command)

For both kinds:

* If a handler raises an exception, the request is answered with the
  completion code 0xFF (unspecified error) and the exception is logged.
* The handlers run one after the other in the worker thread. A slow
  handler delays the following requests, but it does not block the
  receiving of responses, so a handler may send requests itself.
* :meth:`~pyipmi.interfaces.router.MessageRouter.unregister_handler`
  removes a handler.

**Group extensions.** The commands of PICMG, VITA and DCMI share the
network function 0x2C and are distinguished by the group extension, the
first data byte. Register their handlers with ``group_extension``; a
handler with a group extension is used before one without:

.. code-block:: python

   from pyipmi.msgs import picmg

   def get_picmg_properties(req):
       rsp = picmg.GetPicmgPropertiesRsp()
       rsp.completion_code = constants.CC_OK
       rsp.extension_version = 0x14    # PICMG 2.4 (AMC.0)
       rsp.max_fru_device_id = 0
       rsp.fru_device_id = 0
       return rsp

   router.register_handler(constants.NETFN_GROUP_EXTENSION,
                           constants.CMDID_GET_PICMG_PROPERTIES,
                           get_picmg_properties,
                           group_extension=picmg.PICMG_IDENTIFIER)

The group extension field of the response message has its default value
already.

Requester and responder at the same time
----------------------------------------

The router also handles the requests the interface sends, so a
connection can use an interface that answers requests at the same time.
The responses to the connection's requests go to the waiting requests,
the incoming requests to the handlers:

.. code-block:: python

   interface = pyipmi.interfaces.create_interface(
       'aardvark', slave_address=0x72, router=router)
   ipmi = pyipmi.create_connection(interface)
   ipmi.target = pyipmi.Target(ipmb_address=0x20)

   with ipmi:
       # the handlers answer requests to 0x72 in the background
       print(ipmi.get_device_id())    # request to the BMC at 0x20

Forwarding between buses
------------------------

One router can be shared by several interfaces, e.g. both buses of an
openipmblink bridge. A response is always sent on the interface the
request came from, and responses are matched per interface. Because the
handlers run in the worker thread, a handler can forward a request to a
device on another bus and return its response:

.. code-block:: python

   router = MessageRouter()

   bus0 = pyipmi.interfaces.create_interface(
       'openipmblink', slave_address=0x72, port='/dev/ttyACM1', bus=0,
       router=router)
   bus1 = pyipmi.interfaces.create_interface(
       'openipmblink', slave_address=0x20, port='/dev/ttyACM1', bus=1,
       router=router)

   device = pyipmi.create_connection(bus1)
   device.target = pyipmi.Target(ipmb_address=0x7a)

   def forward(interface, header, data):
       # a request to 0x72 on bus 0 is answered by 0x7a on bus 1
       return device.send_raw(header.rs_lun, header.netfn,
                              bytes([header.cmdid]) + data)

   router.register_raw_handler(constants.NETFN_APP,
                               constants.CMDID_GET_DEVICE_ID, forward)

   bus0.open()
   bus1.open()

Debugging
---------

With the log level ``DEBUG`` for ``pyipmi.interfaces``, the interfaces log
every sent and received message and the router logs the dropped messages,
e.g. responses without a pending request or messages with a wrong
checksum. With ``ipmitool.py`` use ``--log-level interfaces=DEBUG``.
