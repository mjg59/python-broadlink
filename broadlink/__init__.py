#!/usr/bin/env python3
"""The python-broadlink library."""
import socket
from typing import Generator, List, Tuple, Union

from .alarm import S1C
from .climate import hysen
from .cover import dooya
from .device import device, ping, scan
from .exceptions import exception
from .light import lb1
from .remote import rm, rm4, rm4mini, rm4pro, rmmini, rmminib, rmpro
from .sensor import a1
from .switch import bg1, mp1, sp1, sp2, sp2s, sp3, sp3s, sp4, sp4b

SUPPORTED_TYPES = {
    0x0000: (sp1, "SP1", "Broadlink"),
    0x2717: (sp2, "NEO", "Ankuoo"),
    0x2719: (sp2, "SP2-compatible", "Honeywell"),
    0x271A: (sp2, "SP2-compatible", "Honeywell"),
    0x2720: (sp2, "SP mini", "Broadlink"),
    0x2728: (sp2, "SP2-compatible", "URANT"),
    0x273E: (sp2, "SP mini", "Broadlink"),
    0x7530: (sp2, "SP2", "Broadlink (OEM)"),
    0x7539: (sp2, "SP2-IL", "Broadlink (OEM)"),
    0x753E: (sp2, "SP mini 3", "Broadlink"),
    0x7540: (sp2, "MP2", "Broadlink"),
    0x7544: (sp2, "SP2-CL", "Broadlink"),
    0x7546: (sp2, "SP2-UK/BR/IN", "Broadlink (OEM)"),
    0x7547: (sp2, "SC1", "Broadlink"),
    0x7918: (sp2, "SP2", "Broadlink (OEM)"),
    0x7919: (sp2, "SP2-compatible", "Honeywell"),
    0x791A: (sp2, "SP2-compatible", "Honeywell"),
    0x7D0D: (sp2, "SP mini 3", "Broadlink (OEM)"),
    0x2711: (sp2s, "SP2", "Broadlink"),
    0x2716: (sp2s, "NEO PRO", "Ankuoo"),
    0x271D: (sp2s, "Ego", "Efergy"),
    0x2736: (sp2s, "SP mini+", "Broadlink"),
    0x2733: (sp3, "SP3", "Broadlink"),
    0x7D00: (sp3, "SP3-EU", "Broadlink (OEM)"),
    0x9479: (sp3s, "SP3S-US", "Broadlink"),
    0x947A: (sp3s, "SP3S-EU", "Broadlink"),
    0x756C: (sp4, "SP4M", "Broadlink"),
    0x756F: (sp4, "MCB1", "Broadlink"),
    0x7579: (sp4, "SP4L-EU", "Broadlink"),
    0x7583: (sp4, "SP mini 3", "Broadlink"),
    0x7D11: (sp4, "SP mini 3", "Broadlink"),
    0xA56A: (sp4, "MCB1", "Broadlink"),
    0xA589: (sp4, "SP4L-UK", "Broadlink"),
    0x5115: (sp4b, "SCB1E", "Broadlink"),
    0x51E2: (sp4b, "AHC/U-01", "BG Electrical"),
    0x6111: (sp4b, "MCB1", "Broadlink"),
    0x6113: (sp4b, "SCB1E", "Broadlink"),
    0x618B: (sp4b, "SP4L-EU", "Broadlink"),
    0x6489: (sp4b, "SP4L-AU", "Broadlink"),
    0x648B: (sp4b, "SP4M-US", "Broadlink"),
    0x2737: (rmmini, "RM mini 3", "Broadlink"),
    0x278F: (rmmini, "RM mini", "Broadlink"),
    0x27C2: (rmmini, "RM mini 3", "Broadlink"),
    0x27C7: (rmmini, "RM mini 3", "Broadlink"),
    0x27CC: (rmmini, "RM mini 3", "Broadlink"),
    0x27CD: (rmmini, "RM mini 3", "Broadlink"),
    0x27D0: (rmmini, "RM mini 3", "Broadlink"),
    0x27D1: (rmmini, "RM mini 3", "Broadlink"),
    0x27D3: (rmmini, "RM mini 3", "Broadlink"),
    0x27DE: (rmmini, "RM mini 3", "Broadlink"),
    0x2712: (rmpro, "RM pro/pro+", "Broadlink"),
    0x272A: (rmpro, "RM pro", "Broadlink"),
    0x273D: (rmpro, "RM pro", "Broadlink"),
    0x277C: (rmpro, "RM home", "Broadlink"),
    0x2783: (rmpro, "RM home", "Broadlink"),
    0x2787: (rmpro, "RM pro", "Broadlink"),
    0x278B: (rmpro, "RM plus", "Broadlink"),
    0x2797: (rmpro, "RM pro+", "Broadlink"),
    0x279D: (rmpro, "RM pro+", "Broadlink"),
    0x27A1: (rmpro, "RM plus", "Broadlink"),
    0x27A6: (rmpro, "RM plus", "Broadlink"),
    0x27A9: (rmpro, "RM pro+", "Broadlink"),
    0x27C3: (rmpro, "RM pro+", "Broadlink"),
    0x5F36: (rmminib, "RM mini 3", "Broadlink"),
    0x6508: (rmminib, "RM mini 3", "Broadlink"),
    0x51DA: (rm4mini, "RM4 mini", "Broadlink"),
    0x6070: (rm4mini, "RM4C mini", "Broadlink"),
    0x610E: (rm4mini, "RM4 mini", "Broadlink"),
    0x610F: (rm4mini, "RM4C mini", "Broadlink"),
    0x62BC: (rm4mini, "RM4 mini", "Broadlink"),
    0x62BE: (rm4mini, "RM4C mini", "Broadlink"),
    0x6364: (rm4mini, "RM4S", "Broadlink"),
    0x648D: (rm4mini, "RM4 mini", "Broadlink"),
    0x6539: (rm4mini, "RM4C mini", "Broadlink"),
    0x653A: (rm4mini, "RM4 mini", "Broadlink"),
    0x6026: (rm4pro, "RM4 pro", "Broadlink"),
    0x61A2: (rm4pro, "RM4 pro", "Broadlink"),
    0x649B: (rm4pro, "RM4 pro", "Broadlink"),
    0x653C: (rm4pro, "RM4 pro", "Broadlink"),
    0x2714: (a1, "e-Sensor", "Broadlink"),
    0x4EB5: (mp1, "MP1-1K4S", "Broadlink"),
    0x4EF7: (mp1, "MP1-1K4S", "Broadlink (OEM)"),
    0x4F1B: (mp1, "MP1-1K3S2U", "Broadlink (OEM)"),
    0x4F65: (mp1, "MP1-1K3S2U", "Broadlink"),
    0x5043: (lb1, "SB800TD", "Broadlink (OEM)"),
    0x504E: (lb1, "LB1", "Broadlink"),
    0x60C7: (lb1, "LB1", "Broadlink"),
    0x60C8: (lb1, "LB1", "Broadlink"),
    0x6112: (lb1, "LB1", "Broadlink"),
    0x2722: (S1C, "S2KIT", "Broadlink"),
    0x4EAD: (hysen, "HY02B05H", "Hysen"),
    0x4E4D: (dooya, "DT360E-45/20", "Dooya"),
    0x51E3: (bg1, "BG800/BG900", "BG Electrical"),
}


def gendevice(
    dev_type: int,
    host: Tuple[str, int],
    mac: Union[bytes, str],
    name: str = None,
    is_locked: bool = None,
) -> device:
    """Generate a device."""
    try:
        dev_class, model, manufacturer = SUPPORTED_TYPES[dev_type]

    except KeyError:
        return device(host, mac, dev_type, name=name, is_locked=is_locked)

    return dev_class(
        host,
        mac,
        dev_type,
        name=name,
        model=model,
        manufacturer=manufacturer,
        is_locked=is_locked,
    )


def hello(
    host: str,
    port: int = 80,
    timeout: int = 10,
    local_ip_address: str = None,
) -> device:
    """Direct device discovery.

    Useful if the device is locked.
    """
    try:
        return next(xdiscover(timeout, local_ip_address, host, port))
    except StopIteration:
        raise exception(-4000)  # Network timeout.


def discover(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> List[device]:
    """Discover devices connected to the local network."""
    responses = scan(timeout, local_ip_address, discover_ip_address, discover_ip_port)
    return [gendevice(*resp) for resp in responses]


def xdiscover(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> Generator[device, None, None]:
    """Discover devices connected to the local network.

    This function returns a generator that yields devices instantly.
    """
    responses = scan(timeout, local_ip_address, discover_ip_address, discover_ip_port)
    for resp in responses:
        yield gendevice(*resp)


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
