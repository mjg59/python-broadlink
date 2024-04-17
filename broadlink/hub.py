"""Support for hubs."""
import struct
import json
from typing import Optional

from . import exceptions as e
from .device import Device


class s3(Device):
    """Controls a Broadlink S3."""

    TYPE = "S3"
    MAX_SUBDEVICES = 8

    def get_subdevices(self, step: int = 5) -> list:
        """Return a list of sub devices."""
        total = self.MAX_SUBDEVICES
        sub_devices = []
        seen = set()
        index = 0

        while index < total:
            state = {"count": step, "index": index}
            packet = self._encode(14, state)
            resp = self.send_packet(0x6A, packet)
            e.check_error(resp[0x22:0x24])
            resp = self._decode(resp)

            for device in resp["list"]:
                did = device["did"]
                if did in seen:
                    continue

                seen.add(did)
                sub_devices.append(device)

            total = resp["total"]
            if len(seen) >= total:
                break

            index += step

        return sub_devices

    def get_state(self, did: Optional[str] = None) -> dict:
        """Return the power state of the device."""
        state = {}
        if did is not None:
            state["did"] = did

        packet = self._encode(1, state)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def set_state(
        self,
        did: Optional[str] = None,
        pwr1: Optional[bool] = None,
        pwr2: Optional[bool] = None,
        pwr3: Optional[bool] = None,
    ) -> dict:
        """Set the power state of the device."""
        state = {}
        if did is not None:
            state["did"] = did
        if pwr1 is not None:
            state["pwr1"] = int(bool(pwr1))
        if pwr2 is not None:
            state["pwr2"] = int(bool(pwr2))
        if pwr3 is not None:
            state["pwr3"] = int(bool(pwr3))

        packet = self._encode(2, state)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a JSON packet."""
        # flag: 1 for reading, 2 for writing.
        packet = bytearray(12)
        data = json.dumps(state, separators=(",", ":")).encode()
        struct.pack_into(
            "<HHHBBI", packet, 0, 0xA5A5, 0x5A5A, 0, flag, 0x0B, len(data)
        )
        packet.extend(data)
        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x04:0x06] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a JSON packet."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        state = json.loads(payload[0x0C:0x0C+js_len])
        return state
