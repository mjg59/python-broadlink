"""Helper functions and classes."""
import typing as t


class CRC16:  # pylint: disable=R0903
    """Helps with CRC-16 calculation.

    CRC tables are cached for performance.
    """

    _cache = {}

    @classmethod
    def calculate(
        cls,
        sequence: t.Sequence[int],
        polynomial: int = 0xA001,  # Modbus CRC-16.
        init_value: int = 0xFFFF,
    ) -> int:
        """Calculate the CRC-16 of a sequence of integers."""
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

        crc = init_value
        for item in sequence:
            crc = crc >> 8 ^ crc_table[(crc ^ item) & 0xFF]
        return crc
