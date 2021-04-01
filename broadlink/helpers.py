"""Helper functions."""
import typing as t

def crc16(sequence: t.Sequence[int]) -> int:
    """Calculate the CRC-16 of a byte string."""
    crc_table = []
    polynomial = 0xA001

    for dividend in range(0, 256):
        remainder = dividend
        for _ in range(0, 8):
            if remainder & 0x0001:
                remainder = remainder >> 1 & 0xFFFF ^ polynomial
            else:
                remainder = remainder >> 1 & 0xFFFF
        crc_table.append(remainder)

    crc = 0xFFFF

    for item in sequence:
        index = (crc ^ item) & 0x00FF
        base = crc >> 8 & 0xFFFF
        crc = base ^ crc_table[index]

    return crc
