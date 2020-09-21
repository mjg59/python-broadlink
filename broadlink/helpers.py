"""Helper functions."""
from ctypes import c_ushort
import socket

from .exceptions import exception


def get_local_ip() -> str:
    """Try to determine the local IP address of the machine."""
    # Useful for VPNs.
    try:
        local_ip_address = socket.gethostbyname(socket.gethostname())
        if not local_ip_address.startswith('127.'):
            return local_ip_address
    except socket.gaierror:
        raise exception(-4013)  # DNS Error

    # Connecting to UDP address does not send packets.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 53))
        return s.getsockname()[0]


def calculate_crc16(input_data: bytes) -> int:
    """Calculate the CRC-16 of a byte string."""
    crc16_tab = []
    crc16_constant = 0xA001

    for i in range(0, 256):
        crc = c_ushort(i).value
        for j in range(0, 8):
            if crc & 0x0001:
                crc = c_ushort(crc >> 1).value ^ crc16_constant
            else:
                crc = c_ushort(crc >> 1).value
        crc16_tab.append(hex(crc))

    crcValue = 0xFFFF

    for c in input_data:
        tmp = crcValue ^ c
        rotated = c_ushort(crcValue >> 8).value
        crcValue = rotated ^ int(crc16_tab[(tmp & 0x00FF)], 0)

    return crcValue
