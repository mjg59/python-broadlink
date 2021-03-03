"""Common functions and classes."""
import typing as t
import json

from . import exceptions as e


class State:
    """Helps to pack and unpack state for transport.

    This packet contains the length and checksum to prevent data
    corruption.
    """

    READ = 1
    WRITE = 2

    @staticmethod
    def pack(flag: int, obj: t.Any, eoh=0x0B) -> bytes:
        """Pack state to be sent over the Broadlink protocol."""
        if hasattr(obj, "decode"):
            obj = b"\x00" + obj
        else:
            obj = json.dumps(obj, separators=(",", ":")).encode()

        packet = bytearray(eoh-3) if eoh else bytearray(6)
        packet[0x02] = flag
        packet[0x03] = eoh
        packet[0x04:0x06] = len(obj).to_bytes(2, "little")
        packet.extend(obj)

        checksum = sum(packet, 0xC0AD) & 0xFFFF
        packet[0x00:0x02] = checksum.to_bytes(2, "little")
        return packet

    @staticmethod
    def unpack(packet: bytes) -> t.Tuple[int, t.Any]:
        """Unpack state received over the Broadlink protocol."""
        nom_checksum = int.from_bytes(packet[0x00:0x02], "little")
        real_checksum = sum(packet[0x02:], 0xC0AD) & 0xFFFF

        if nom_checksum != real_checksum:
            raise e.DataValidationError(
                f"Expected a checksum of {nom_checksum} and received {real_checksum}",
            )

        flag = packet[0x02]
        eoh = packet[0x03] or 0x09
        p_len = int.from_bytes(packet[0x04:0x06], "little")

        start = eoh-3
        try:
            payload = packet[start:start+p_len]
        except IndexError:
            raise e.DataValidationError(
                f"Expected a payload of {p_len} bytes and received {len(packet[start:])}",
            )

        if hasattr(payload, "decode"):
            return flag, payload[0x01:] if len(payload) else b""
        return flag, json.loads(payload)
