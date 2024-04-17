"""Helper functions and classes."""
from typing import Dict, List, Sequence


class CRC16:
    """Helps with CRC-16 calculation.

    CRC tables are cached for performance.
    """

    _cache: Dict[int, List[int]] = {}

    @classmethod
    def get_table(cls, polynomial: int) -> List[int]:
        """Return the CRC-16 table for a polynomial."""
        try:
            crc_table = cls._cache[polynomial]
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
            cls._cache[polynomial] = crc_table
        return crc_table

    @classmethod
    def calculate(
        cls,
        sequence: Sequence[int],
        polynomial: int = 0xA001,  # CRC-16-ANSI.
        init_value: int = 0xFFFF,
    ) -> int:
        """Calculate the CRC-16 of a sequence of integers."""
        crc_table = cls.get_table(polynomial)
        crc = init_value
        for item in sequence:
            crc = crc >> 8 ^ crc_table[(crc ^ item) & 0xFF]
        return crc
