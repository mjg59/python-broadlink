"""Helper functions."""
from ctypes import c_ushort


def crc16(sequence: bytes) -> int:
    """Calculate the CRC-16 of a byte string."""
    crc_table = []
    polynomial = 0xA001

    for dividend in range(0, 256):
        remainder = c_ushort(dividend).value
        for _ in range(0, 8):
            if remainder & 0x0001:
                remainder = c_ushort(remainder >> 1).value ^ polynomial
            else:
                remainder = c_ushort(remainder >> 1).value
        crc_table.append(hex(remainder))

    crc = 0xFFFF

    for item in sequence:
        index = (crc ^ item) & 0x00FF
        base = c_ushort(crc >> 8).value
        crc = base ^ int(crc_table[index], 0)

    return crc
