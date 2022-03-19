"""Support for hubs."""
import struct
import json

from . import exceptions as e
from .device import Device


class s3(Device):
    """Controls a Broadlink S3."""

    TYPE = "S3"
    MAX_SUBDEVICES = 8

    def get_subdevices(self) -> list:
        """Return the lit of sub devices."""
        sub_devices = []
        step = 5

        for index in range(0, self.MAX_SUBDEVICES, step):
            state = {"count": step, "index": index}
            packet = self._encode(14, state)
            resp = self.send_packet(0x6A, packet)
            e.check_error(resp[0x22:0x24])
            resp = self._decode(resp)

            sub_devices.extend(resp["list"])
            if len(sub_devices) == resp["total"]:
                break

        return sub_devices

    def get_state(self, did: str = None) -> dict:
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
        did: str = None,
        pwr1: bool = None,
        pwr2: bool = None,
        pwr3: bool = None,
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
        struct.pack_into("<HHHBBI", packet, 0, 0xA5A5, 0x5A5A, 0, flag, 0x0B, len(data))
        packet.extend(data)
        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x04:0x06] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a JSON packet."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        state = json.loads(payload[0x0C : 0x0C + js_len])
        return state
