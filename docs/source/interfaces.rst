Commands and Interfaces
=======================

This page describes how the IPMI commands of :class:`pyipmi.Ipmi`
reach a device: the layers a request passes through, what each layer is
responsible for, and the contract between the connection and the
interfaces. Read it to understand where a request is encoded, where the
target and its routing are applied, and where errors and retries are
handled, or to implement a new interface.

Layers
------

.. graphviz::

   digraph layers {
       rankdir=TB;
       node [shape=box, fontname="sans-serif", fontsize=10];
       edge [fontname="sans-serif", fontsize=9];

       commands [label="Command groups\n(bmc.Bmc, sdr.Sdr, sel.Sel, sensor.Sensor, ...)\nget_device_id(), get_sel_entry(), ..."];
       messaging [label="Messaging API of pyipmi.Ipmi\nsend_message_by_name(), send_message(), send_raw()"];
       msgs [label="Messages (pyipmi.msgs)\nGetSelInfoReq / GetSelInfoRsp, __fields__", shape=note];
       interface [label="Interface (pyipmi.interfaces.base.Interface)\nsend_and_receive(), send_and_receive_raw()"];
       transport [label="Transport\nRMCP/RMCP+ (UDP), ipmitool, /dev/ipmi0,\nIPMB (Aardvark, ipmb-dev, openipmblink)"];
       session [label="Session\n(pyipmi.session.Session)", shape=note];

       commands -> messaging [label=" request by name, fields"];
       messaging -> interface [label=" Message with target, requester"];
       interface -> transport [label=" raw bytes, addressed by\n target / routing"];
       messaging -> msgs [style=dashed, arrowhead=none];
       interface -> msgs [style=dashed, arrowhead=none, label=" encode / decode"];
       session -> interface [style=dashed, label=" establish_session()"];
   }

**Command groups.** The IPMI commands are not methods of a single
class. Each module (:mod:`pyipmi.bmc`, :mod:`pyipmi.sdr`,
:mod:`pyipmi.sel`, ...) defines a command group class derived from
``pyipmi.mixin.IpmiMixin``, and :class:`pyipmi.Ipmi` inherits from all
of them. A command method builds a request, sends it through the
messaging API and turns the response into a return value, e.g. a
:class:`pyipmi.bmc.DeviceId`. Command groups know nothing about the
transport.

**Messaging API.** :class:`pyipmi.Ipmi` provides three ways to send a
request, all of them to :attr:`pyipmi.Ipmi.target`:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Method
     - Input / output
     - Checks
   * - :meth:`~pyipmi.Ipmi.send_message_by_name`
     - message name and fields / response message
     - raises ``CompletionCodeError`` if the completion code is not
       successful
   * - :meth:`~pyipmi.Ipmi.send_message`
     - request message / response message
     - retries while the target is busy, the completion code is not
       checked
   * - :meth:`~pyipmi.Ipmi.send_raw`
     - LUN, network function and bytes / bytes
     - none, the bytes are passed through

Most command groups use :meth:`~pyipmi.Ipmi.send_message_by_name`.
Commands that handle a completion code themselves, e.g. the partial
reads of SDR and SEL entries, use :meth:`~pyipmi.Ipmi.send_message` and
check the code.

**Messages.** A request and its response are classes in
:mod:`pyipmi.msgs`, e.g. ``GetSelInfoReq`` and ``GetSelInfoRsp``,
registered with ``@register_message_class``. Their ``__fields__``
describe the encoding, and ``encode_message()`` and ``decode_message()``
convert between a message and its bytes. A message carries the network
function, command ID, LUN and group extension the interface needs to
address it.

**Interface.** An interface sends a request to the target and returns
the response. It is the only layer that knows the transport: how to
reach the target, how to apply its routing and how to establish a
session.

The path of a request
---------------------

Reading the number of SEL entries shows every step:

#. ``ipmi.get_sel_entries_count()`` (:mod:`pyipmi.sel`) calls
   ``send_message_by_name('GetSelInfo')``.
#. :meth:`~pyipmi.Ipmi.send_message_by_name` creates a ``GetSelInfoReq``
   from the message registry, sets the given fields as attributes and
   calls :meth:`~pyipmi.Ipmi.send_message`.
#. :meth:`~pyipmi.Ipmi.send_message` attaches the target and the
   requester of the connection to the request and calls
   :meth:`~pyipmi.interfaces.base.Interface.send_and_receive` of the
   interface.
#. The default
   :meth:`~pyipmi.interfaces.base.Interface.send_and_receive` encodes the
   request (the command ID followed by the encoded fields) and calls
   :meth:`~pyipmi.interfaces.base.Interface.send_and_receive_raw` with
   the target, LUN and network function of the request.
#. The interface sends the bytes over its transport, applying the
   address and the routing of the target (see `Targets and routing`_),
   and returns the response bytes, starting with the completion code.
#. :meth:`~pyipmi.interfaces.base.Interface.send_and_receive` decodes
   them into a ``GetSelInfoRsp``, found by the network function + 1, the
   command ID and the group extension of the request.
#. Back in the messaging API, :meth:`~pyipmi.Ipmi.send_message` retries
   if the target was busy, and
   :meth:`~pyipmi.Ipmi.send_message_by_name` checks the completion code.
#. The command returns ``rsp.entries``.

:meth:`~pyipmi.Ipmi.send_raw` (``ipmitool.py raw``) skips the message
layer and calls
:meth:`~pyipmi.interfaces.base.Interface.send_and_receive_raw` directly.

The interface contract
----------------------

:class:`pyipmi.interfaces.base.Interface` defines the methods the
connection and the session call. A new interface implements at least
:meth:`~pyipmi.interfaces.base.Interface.send_and_receive_raw`, the
others have defaults.

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Method or attribute
     - Called or read by
     - Default
   * - ``send_and_receive_raw()``
     - :meth:`~pyipmi.interfaces.base.Interface.send_and_receive`,
       :meth:`~pyipmi.Ipmi.send_raw`
     - none, every interface implements it
   * - ``send_and_receive()``
     - :meth:`~pyipmi.Ipmi.send_message`
     - encodes the request, calls ``send_and_receive_raw()`` and decodes
       the response
   * - ``open()``, ``close()``
     - :meth:`~pyipmi.Ipmi.open`, :meth:`~pyipmi.Ipmi.close`
     - nothing
   * - ``establish_session()``, ``close_session()``
     - :meth:`pyipmi.session.Session.establish`,
       :meth:`pyipmi.session.Session.close`
     - nothing, for interfaces without a session
   * - ``is_target_accessible()``
     - :meth:`~pyipmi.Ipmi.is_target_accessible`
     - raises ``NotImplementedError``
   * - ``is_system_interface()``
     - commands whose request differs on the system interface, e.g. the
       Generator ID of a Platform Event request in :mod:`pyipmi.sensor`
     - ``False``
   * - ``MAX_REQUEST_DATA_SIZE``
     - commands that split large data, e.g. the HPM.1 upgrade blocks in
       :mod:`pyipmi.hpm`
     - ``None``, the IPMB limit applies
   * - ``NAME``
     - :func:`pyipmi.interfaces.create_interface`
     - ``None``

The capabilities let a command adapt to the transport without knowing
which interface is used: it asks
``self.interface.is_system_interface(self.target)`` instead of checking
the class of the interface.

Connection lifecycle
--------------------

The connection is a context manager. ``with ipmi:`` calls
:meth:`~pyipmi.Ipmi.open`, which opens the interface and then calls
:meth:`pyipmi.session.Session.establish`. The session holds the host and
the credentials, set by ``set_session_type_rmcp()`` and
``set_auth_type_user()``, and passes itself to ``establish_session()``
of the interface. Leaving the block closes the session and then the
interface.

Only some interfaces use the session: :class:`~pyipmi.interfaces.Rmcp`
and :class:`~pyipmi.interfaces.RmcpPlus` run the session setup and keep
the session alive, and :class:`~pyipmi.interfaces.Ipmitool` turns it
into the command line options of ``ipmitool``. The other interfaces
ignore it.

Targets and routing
-------------------

A request goes to :attr:`pyipmi.Ipmi.target`, a :class:`pyipmi.Target`
with an IPMB address and an optional routing, a list of
:class:`pyipmi.Routing` hops (see :meth:`pyipmi.Target.set_routing`). The
command groups and the messaging API pass the target on unchanged, and
each interface decides how to reach it:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Interface
     - How the target and its routing are used
   * - ``rmcp``, ``rmcpplus``
     - Without routing, the request is sent to the IPMB address of the
       target. With a routing, it is wrapped in one Send Message request
       per bridge (``encode_bridged_message()`` in
       :mod:`pyipmi.interfaces.ipmb`), for any number of hops. The Send
       Message responses are unwrapped and their completion codes
       checked.
   * - ``ipmitool``
     - The routing becomes the bridging options of ipmitool: ``-t`` and
       ``-b`` for one bridge, additionally ``-T`` and ``-B`` for two. A
       routing of one hop addresses the BMC itself. Without routing,
       ``-t`` is the IPMB address of the target.
   * - ``ipmidev``
     - The BMC (``0x20``, not bridged) is addressed through the system
       interface, other targets by an IPMB address on a channel, with at
       most one bridge.
   * - ``ipmbdev``, ``aardvark``, ``openipmblink``
     - The interface is a node on the IPMB itself: the request is sent
       directly to the IPMB address of the target, the routing is not
       used. A ``MessageRouter`` (:mod:`pyipmi.interfaces.router`) matches
       the responses to the requests and can also answer incoming
       requests.
   * - ``mock``
     - Nothing is sent, the tests replace the methods.

Errors and retries
------------------

Requests are retried in two layers, for different reasons:

* **The interface** retries when no response arrives (timeouts, lost
  packets or frames) and raises an error when it gives up:
  ``RetryError`` for the RMCP interfaces, ``IpmiTimeoutError`` for the
  IPMB interfaces. A failed Send Message request of a bridged request
  raises ``CompletionCodeError``.
* **The connection** retries when the target answers that it is busy:
  :meth:`~pyipmi.Ipmi.send_message` repeats the request while the
  interface raises ``CompletionCodeError`` with "node busy", and raises
  ``RetryError`` after the last try.

Any other completion code is part of the response:
:meth:`~pyipmi.Ipmi.send_message` returns it unchecked, and
:meth:`~pyipmi.Ipmi.send_message_by_name` raises ``CompletionCodeError``
for it.

Implementing an interface
-------------------------

#. Derive from :class:`pyipmi.interfaces.base.Interface`, set ``NAME``
   and implement ``send_and_receive_raw()``: send the request bytes to
   the target, LUN and network function, and return the response bytes,
   starting with the completion code. Apply the routing of the target,
   or reject a routing the transport cannot follow.
#. Override ``open()`` and ``close()`` for the transport, and
   ``establish_session()`` and ``close_session()`` if it has a session.
#. Implement ``is_target_accessible()``, and ``is_system_interface()``
   if requests can reach the BMC over the system interface.
#. For an IPMB node, derive from ``pyipmi.interfaces.ipmb.IpmbInterface``
   instead: implement ``send_frame()`` and pass every received message to
   ``_receive_frame()``, or implement ``_read_frame()`` and start the
   receive thread. The encoding, the sequence numbers and the matching of
   the responses are done by the base class.
#. Add the class to ``INTERFACES`` in :mod:`pyipmi.interfaces`, so that
   :func:`~pyipmi.interfaces.create_interface` finds it by its name.

The tests of the command groups need no interface:
``tests/ipmi_helper.create_ipmi()`` creates a connection whose interface
answers with canned responses and records the encoded requests.
