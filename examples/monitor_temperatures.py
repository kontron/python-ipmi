#!/usr/bin/env python3
r"""Monitor the temperature sensors of a BMC.

The temperature sensors are searched once, then read every interval for
the given time. Each sample is printed as one row with the values of all
sensors, the minimum and maximum of each sensor at the end.

Example:
    Monitor the CPU temperatures for 5 minutes, every 10 seconds::

        ./monitor_temperatures.py -H 10.0.0.1 -U admin -P admin \
            --time 300 --interval 10 'CPU*'
"""

import argparse
import time

import pyipmi
import pyipmi.interfaces
from pyipmi.errors import CompletionCodeError


def parse_args():
    parser = argparse.ArgumentParser(
        description='Monitor the temperature sensors of a BMC')
    parser.add_argument('name', nargs='?', default='*',
                        help="glob pattern of the sensor names, ignoring "
                             "case, e.g. 'CPU*' (default: all)")
    parser.add_argument('-H', '--host', required=True,
                        help='host name or IP address of the BMC')
    parser.add_argument('-p', '--port', type=int, default=623,
                        help='RMCP port (default 623)')
    parser.add_argument('-U', '--user', default='', help='user name')
    parser.add_argument('-P', '--password', default='', help='password')
    parser.add_argument('-I', '--interface', default='rmcpplus',
                        choices=('rmcp', 'rmcpplus'),
                        help='interface (default rmcpplus)')
    parser.add_argument('-t', '--time', type=float, default=60,
                        help='monitoring time in seconds (default 60)')
    parser.add_argument('-i', '--interval', type=float, default=2,
                        help='interval between the readings in seconds '
                             '(default 2)')
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error('the interval must be greater than 0')
    return args


def connect(args):
    interface = pyipmi.interfaces.create_interface(args.interface,
                                                   keep_alive_interval=0)
    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(ipmb_address=0x20)
    ipmi.session.set_session_type_rmcp(args.host, args.port)
    ipmi.session.set_auth_type_user(args.user, args.password)
    return ipmi


def read_temperatures(ipmi, records):
    """Return the temperature of each sensor, None if it cannot be read."""
    values = []
    for record in records:
        try:
            values.append(ipmi.read_sensor(record).value)
        except CompletionCodeError:
            # e.g. 0xcb, the sensor is not present
            values.append(None)
    return values


def format_row(label, values, widths):
    """Return a table row, the values with one decimal place."""
    cells = ['na' if value is None else f'{value:.1f}' for value in values]
    return f'{label:>7} | ' + ' | '.join(
        f'{cell:>{width}}' for cell, width in zip(cells, widths, strict=True))


def main():
    args = parse_args()

    with connect(args) as ipmi:
        # reading the sensor records is slow, they are searched only once
        records = ipmi.find_sensors(name=args.name,
                                    sensor_type='temperature')
        if not records:
            raise SystemExit(f'No temperature sensor matches {args.name!r}')

        names = [str(record.device_id_string) for record in records]
        widths = [max(len(name), 6) for name in names]
        sensors = 'sensor' if len(records) == 1 else 'sensors'
        print(f'Monitoring {len(records)} temperature {sensors} for '
              f'{args.time:g} s, every {args.interval:g} s (degrees C)')
        print(f'{"Time":>7} | ' + ' | '.join(
            f'{name:>{w}}' for name, w in zip(names, widths, strict=True)))

        minimum = [None] * len(records)
        maximum = [None] * len(records)
        start = time.monotonic()
        sample = 0
        try:
            while True:
                elapsed = time.monotonic() - start
                values = read_temperatures(ipmi, records)
                print(format_row(f'{elapsed:.1f}', values, widths),
                      flush=True)
                for (n, value) in enumerate(values):
                    if value is None:
                        continue
                    if minimum[n] is None or value < minimum[n]:
                        minimum[n] = value
                    if maximum[n] is None or value > maximum[n]:
                        maximum[n] = value

                # the readings are scheduled from the start, so the time
                # of the reading itself does not add up
                sample += 1
                next_reading = start + sample * args.interval
                if next_reading - start > args.time:
                    break
                time.sleep(max(0, next_reading - time.monotonic()))
        except KeyboardInterrupt:
            print()

        print(format_row('Min', minimum, widths))
        print(format_row('Max', maximum, widths))


if __name__ == '__main__':
    main()
