#!/usr/bin/env python3
"""Simple event receiver on an IPMB bus, using an Aardvark adapter.

The event receiver answers the Platform Event (Event Message) requests
addressed to its IPMB address (default 0x20) and prints the decoded
events. All other requests are answered with completion code 0xC1
(invalid command).

On the IPMB, the Platform Event request has no Generator ID byte: the
requester address and LUN of the message are the Generator ID.

    ./bmc_event_receiver.py -s 2237-523145

Send an event from another IPMB device, e.g. from a second adapter at
0x24 (temperature sensor 0x05, upper critical going high asserted, with
trigger reading 0x50 and threshold 0x4b):

    interface = pyipmi.interfaces.create_interface(
        'aardvark', slave_address=0x24, serial_number='2237-523146')
    with pyipmi.Ipmi(interface=interface,
                     target=pyipmi.Target(ipmb_address=0x20)) as ipmi:
        ipmi.send_platform_event(0x01, 0x05, 0x01,
                                 event_data=[0x59, 0x50, 0x4b])
"""

import argparse
import logging
import threading

import pyipmi.interfaces
from pyipmi.interfaces.router import MessageRouter
from pyipmi.msgs import constants, decode_message
from pyipmi.msgs.sensor import PlatformEventReq
from pyipmi.sensor import (EVENT_READING_TYPE_CODE_THRESHOLD,
                           event_offset_to_string,
                           event_reading_type_to_string,
                           sensor_type_to_string)


class EventReceiver:
    """Device that receives the event messages of the IPMB."""

    def register(self, router):
        """Register the command handler of the event receiver at the router."""
        # a raw handler, to get the requester address (the Generator ID)
        router.register_raw_handler(constants.NETFN_SENSOR_EVENT,
                                    constants.CMDID_PLATFORM_EVENT,
                                    self.platform_event)

    def platform_event(self, interface, header, data):
        req = PlatformEventReq()
        try:
            decode_message(req, data)
        except Exception as e:
            logging.warning('invalid Platform Event request [%s]: %s',
                            data.hex(' '), e)
            return bytes((constants.CC_REQ_DATA_INV_LENGTH,))

        self.print_event(header.rq_sa, header.rq_lun, req)
        return bytes((constants.CC_OK,))

    @staticmethod
    def print_event(generator_address, generator_lun, req):
        event_type = req.event_type.type
        event_data = bytes(req.event_data)
        offset = event_data[0] & 0x0f if event_data else 0

        description = event_offset_to_string(event_type, req.sensor_type,
                                             offset)
        if description is None:
            description = f'offset {offset}'
        direction = 'Deasserted' if req.event_type.dir else 'Asserted'

        logging.info('Event from 0x%02x LUN %d, sensor 0x%02x (%s), '
                     '%s: %s %s',
                     generator_address, generator_lun, req.sensor_number,
                     sensor_type_to_string(req.sensor_type),
                     event_reading_type_to_string(event_type),
                     description, direction)

        details = [f'event message revision 0x{req.event_message_rev:02x}',
                   f'event type 0x{event_type:02x}',
                   f'event data [{event_data.hex(" ")}]']
        if (event_type == EVENT_READING_TYPE_CODE_THRESHOLD
                and len(event_data) == 3):
            # event data 2/3 contain the trigger reading/threshold if the
            # bits 7:6/5:4 of event data 1 are 01b
            if (event_data[0] >> 6) & 3 == 1:
                details.append(f'trigger reading 0x{event_data[1]:02x}')
            if (event_data[0] >> 4) & 3 == 1:
                details.append(f'trigger threshold 0x{event_data[2]:02x}')
        logging.info('  %s', ', '.join(details))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-p', '--port', type=int, default=0,
                        help='port number of the adapter (default 0)')
    parser.add_argument('-s', '--serial',
                        help='serial number of the adapter, used instead '
                             'of the port')
    parser.add_argument('-a', '--address', type=lambda s: int(s, 16),
                        default=0x20,
                        help='own IPMB address, 8-bit, hex (default 20)')
    parser.add_argument('--pullups', action='store_true',
                        help='enable the I2C pull-up resistors')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print the IPMB messages')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s')
    if args.verbose:
        logging.getLogger('pyipmi').setLevel(logging.DEBUG)

    router = MessageRouter()
    EventReceiver().register(router)

    interface = pyipmi.interfaces.create_interface(
        'aardvark', slave_address=args.address, port=args.port,
        serial_number=args.serial, enable_i2c_pullups=args.pullups,
        router=router)
    interface.open()

    logging.info('event receiver at 0x%02x, stop with Ctrl-C', args.address)

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        interface.close()
        router.close()


if __name__ == '__main__':
    main()
