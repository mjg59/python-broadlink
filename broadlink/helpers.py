"""Helper functions."""
import typing as t

_crc16_cache = {}


def crc16(
    sequence: t.Sequence[int],
    polynomial: int = 0xA001,  # Default: Modbus CRC-16.
    init_value: int = 0xFFFF,
) -> int:
    """Calculate the CRC-16 of a sequence of integers."""
    global _crc16_cache

    try:
        crc_table = _crc16_cache[polynomial]
    except KeyError:
        crc_table = []
        for dividend in range(0, 256):
            remainder = dividend
            for _ in range(0, 8):
                if remainder & 1:
                    remainder = remainder >> 1 ^ polynomial
                else:
                    remainder = remainder >> 1
            crc_table.append(remainder)
        _crc16_cache[polynomial] = crc_table

    crc = init_value
    for item in sequence:
        crc = crc >> 8 ^ crc_table[(crc ^ item) & 0xFF]
    return crc
