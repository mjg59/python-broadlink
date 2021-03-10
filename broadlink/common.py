"""Common functions and classes."""
import json
import typing as t

from . import exceptions as e


class JSONCommand:
    """Helps to pack and unpack JSON objects for transport.

    This packet contains the length and checksum to prevent data
    corruption.
    """

    @staticmethod
    def pack(cmd: int, obj: t.Any, eoh=0x0B) -> bytes:
        """Pack an object to be sent over the Broadlink protocol."""
        if hasattr(obj, "decode"):
            obj = b"\x00" + obj
        else:
            obj = json.dumps(obj, separators=(",", ":")).encode()

        packet = bytearray(eoh - 3) if eoh else bytearray(6)
        packet[0x02] = cmd
        packet[0x03] = eoh
        packet[0x04:0x06] = len(obj).to_bytes(2, "little")
        packet.extend(obj)

        checksum = sum(packet, 0xC0AD) & 0xFFFF
        packet[0x00:0x02] = checksum.to_bytes(2, "little")
        return packet

    @staticmethod
    def unpack(packet: bytes) -> t.Tuple[int, t.Any]:
        """Unpack an object received over the Broadlink protocol."""
        nom_checksum = int.from_bytes(packet[0x00:0x02], "little")
        real_checksum = sum(packet[0x02:], 0xC0AD) & 0xFFFF

        if nom_checksum != real_checksum:
            raise e.DataValidationError(
                f"Expected a checksum of {nom_checksum} and received {real_checksum}",
            )

        cmd = packet[0x02]
        eoh = packet[0x03] or 0x09
        p_len = int.from_bytes(packet[0x04:0x06], "little")

        start = eoh - 3
        try:
            payload = packet[start : start + p_len]
        except IndexError as err:
            raise e.DataValidationError(
                f"Expected a payload of {p_len} bytes and received {len(packet[start:])}",
            ) from err

        if not payload:
            return cmd, b""
        if payload.startswith(b"\x00"):
            return cmd, payload[0x01:]
        return cmd, json.loads(payload)
