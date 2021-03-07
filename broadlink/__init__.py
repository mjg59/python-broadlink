#!/usr/bin/env python3
"""The python-broadlink library."""
import socket
import time

from .alarm import S1C
from .climate import hysen
from .cover import dooya
from .discovery import SUPPORTED_TYPES, discover, gendevice, hello, xdiscover
from .light import lb1, lb27
from .remote import rm, rm4, rm4mini, rm4pro, rmmini, rmminib, rmpro
from .sensor import a1
from .switch import bg1, mp1, sp1, sp2, sp2s, sp3, sp3s, sp4, sp4b


def ping(address: str, port: int = 80) -> None:
    """Send a ping packet to an address.

    This packet feeds the watchdog timer of firmwares >= v53.
    Useful to prevent reboots when the cloud cannot be reached.
    It must be sent every 2 minutes in such cases.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        packet = bytearray(0x30)
        packet[0x26] = 1
        conn.sendto(packet, (address, port))


# Setup a new Broadlink device via AP Mode. Review the README to see how to enter AP Mode.
# Only tested with Broadlink RM3 Mini (Blackbean)
def setup(ssid: str, password: str, security_mode: int) -> None:
    """Set up a new Broadlink device via AP mode."""
    # Security mode options are (0 - none, 1 = WEP, 2 = WPA1, 3 = WPA2, 4 = WPA1/2)
    payload = bytearray(0x88)
    payload[0x26] = 0x14  # This seems to always be set to 14
    # Add the SSID to the payload
    ssid_start = 68
    ssid_length = 0
    for letter in ssid:
        payload[(ssid_start + ssid_length)] = ord(letter)
        ssid_length += 1
    # Add the WiFi password to the payload
    pass_start = 100
    pass_length = 0
    for letter in password:
        payload[(pass_start + pass_length)] = ord(letter)
        pass_length += 1

    payload[0x84] = ssid_length  # Character length of SSID
    payload[0x85] = pass_length  # Character length of password
    payload[0x86] = security_mode  # Type of encryption

    checksum = sum(payload, 0xBEAF) & 0xFFFF
    payload[0x20] = checksum & 0xFF  # Checksum 1 position
    payload[0x21] = checksum >> 8  # Checksum 2 position

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, ("255.255.255.255", 80))
    sock.close()
