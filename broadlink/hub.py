"""Support for hubs."""
import struct
import enum
import json

from . import exceptions as e
from .device import Device


class s3(Device):
    """Controls a Broadlink S3."""

    TYPE = "S3"
    
    def print_payload(self) -> None:
        hex_string = "80958b19c3cdbbf4e44a07285a1f64a860dda677568d5369134ebef0345244d55dd827fdf7227d6424c73159bc311d0a336eec48a57830d4ccec3ebd06c176a8"  
        payload = self.decrypt(bytearray.fromhex(hex_string))
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        print(json.loads(payload[0x0C : 0x0C + js_len]))
        
        hex_string = "1dd713e6bf12fee9a7e98a29148b1f4ba569e3106ead7fb38214fa66584a3c4e98669e027ba94df43b8015719ee1b0feb8d83f7d14b28170357094e283024bc68eddfceca43e6376e5ad3a713ad04714"
        payload = self.decrypt(bytearray.fromhex(hex_string))
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        print(json.loads(payload[0x0C : 0x0C + js_len]))
    
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
            state["pwr1"] = int(bool(pwr3))

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