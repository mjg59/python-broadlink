"""Support for hubs."""
import struct
import json

from . import exceptions as e
from .device import Device

class s3(Device):
    """Controls a Broadlink S3."""

    TYPE = "S3"
    
    def print_payload(self) -> None:
        hex_string = "d27fdf0201008c01ffca000080d0650dda21b4ce49960000feca00027c107bbfffe9545b1c7f5b640b563ea929a1d0e43bd21112206a1224760eb43dd1f2812086bc6431a7c82995df238e4240142cf4208f866a2d48f8d231f75578a75e54aa74573533c858840fa5165bb9f14533bfbf7a651409788953da8b081287fd0f2e88d0be2b7c75d7aa118f2457f8fe5b5e87448ee8d738fa3df7d8d36e3d4b2385b873554aa3f0e4f111e9106355b1225c3cc9ab1fcd0e83684d2873ec13a03301d371f501557a6606a960293a6a682e3c602d2a9cc81139568964c2c6c219196d4992cd33533cf3d4dd88fc923f5bdba5131eae06d2dba20b07067b28f939300a78e908ffa8f76a2ad7ffdd8905f9030117846e394dd2e7c0ee2aaf178cb128109e5ea67c2e8c1c9c5fb8113dd73e6c98ca48edb6bc5c10b303ba11bfa94f9f19a7844cffda903b7f099bb5b5deeab6364c0c1b0ce772b0f9ee579049eeb1c0769dc601ab16dfff06d56ecfb2e64b8f8568233bdf8907d2b378d4b54a25e90ba3d787c4ae39c1850850cd4d4f"  
        payload = self.decrypt(bytearray.fromhex(hex_string))
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        print(payload)
        print(json.loads(payload[0x0C : 0x0C + js_len]))
        
            
    def get_subdevices(self) -> dict:
        """Return the lit of sub devices."""
        sub_devices = []
        get_subdevices = True
        total = 0
        state = {"count":5,"index":0}
        
        while(get_subdevices):
            packet = self._encode(14, state)
            resp = self.send_packet(0x6a, packet)
            e.check_error(resp[0x22:0x24])
            resp = self._decode(resp)
            
            sub_devices.extend(resp["list"])
            total = resp["total"]
            
            if len(sub_devices) >= total:
                get_subdevices = False
            else:
                state["index"] += 5
            
        return(sub_devices)

    def get_state(self,did: str = None) -> dict:
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