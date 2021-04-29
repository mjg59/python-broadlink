#!/usr/bin/env python3
import argparse

import broadlink
from broadlink.const import DEFAULT_BCAST_ADDR, DEFAULT_TIMEOUT
from broadlink.exceptions import StorageError

parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="timeout to wait for receiving discovery responses")
parser.add_argument("--ip", default=None, help="ip address to use in the discovery")
parser.add_argument("--dst-ip", default=DEFAULT_BCAST_ADDR, help="destination ip address to use in the discovery")
args = parser.parse_args()

print("Discovering...")
devices = broadlink.discover(timeout=args.timeout, local_ip_address=args.ip, discover_ip_address=args.dst_ip)
for device in devices:
    if device.auth():
        print("###########################################")
        print(device.type)
        print("# broadlink_cli --type {} --host {} --mac {}".format(hex(device.devtype), device.host[0],
                                                                    ''.join(format(x, '02x') for x in device.mac)))
        print("Device file data (to be used with --device @filename in broadlink_cli) : ")
        print("{} {} {}".format(hex(device.devtype), device.host[0], ''.join(format(x, '02x') for x in device.mac)))
        try:
            print("temperature = {}".format(device.check_temperature()))
        except (AttributeError, StorageError):
            pass
        print("")
    else:
        print("Error authenticating with device : {}".format(device.host))
