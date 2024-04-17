"""Support for lights."""
import enum
import json
import struct

from . import exceptions as e
from .device import Device


class lb1(Device):
    """Controls a Broadlink LB1."""

    TYPE = "LB1"

    @enum.unique
    class ColorMode(enum.IntEnum):
        """Enumerates color modes."""

        RGB = 0
        WHITE = 1
        SCENE = 2

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{'red': 128, 'blue': 255, 'green': 128, 'pwr': 1, 'brightness': 75, 'colortemp': 2700, 'hue': 240, 'saturation': 50, 'transitionduration': 1500, 'maxworktime': 0, 'bulb_colormode': 1, 'bulb_scenes': '["@01686464,0,0,0", "#ffffff,10,0,#000000,190,0,0", "2700+100,0,0,0", "#ff0000,500,2500,#00FF00,500,2500,#0000FF,500,2500,0", "@01686464,100,2400,@01686401,100,2400,0", "@01686464,100,2400,@01686401,100,2400,@005a6464,100,2400,@005a6401,100,2400,0", "@01686464,10,0,@00000000,190,0,0", "@01686464,200,0,@005a6464,200,0,0"]', 'bulb_scene': '', 'bulb_sceneidx': 255}`
        """
        packet = self._encode(1, {})
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def set_state(
        self,
        pwr: bool = None,
        red: int = None,
        blue: int = None,
        green: int = None,
        brightness: int = None,
        colortemp: int = None,
        hue: int = None,
        saturation: int = None,
        transitionduration: int = None,
        maxworktime: int = None,
        bulb_colormode: int = None,
        bulb_scenes: str = None,
        bulb_scene: str = None,
        bulb_sceneidx: int = None,
    ) -> dict:
        """Set the power state of the device."""
        state = {}
        if pwr is not None:
            state["pwr"] = int(bool(pwr))
        if red is not None:
            state["red"] = int(red)
        if blue is not None:
            state["blue"] = int(blue)
        if green is not None:
            state["green"] = int(green)
        if brightness is not None:
            state["brightness"] = int(brightness)
        if colortemp is not None:
            state["colortemp"] = int(colortemp)
        if hue is not None:
            state["hue"] = int(hue)
        if saturation is not None:
            state["saturation"] = int(saturation)
        if transitionduration is not None:
            state["transitionduration"] = int(transitionduration)
        if maxworktime is not None:
            state["maxworktime"] = int(maxworktime)
        if bulb_colormode is not None:
            state["bulb_colormode"] = int(bulb_colormode)
        if bulb_scenes is not None:
            state["bulb_scenes"] = str(bulb_scenes)
        if bulb_scene is not None:
            state["bulb_scene"] = str(bulb_scene)
        if bulb_sceneidx is not None:
            state["bulb_sceneidx"] = int(bulb_sceneidx)

        packet = self._encode(2, state)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a JSON packet."""
        # flag: 1 for reading, 2 for writing.
        packet = bytearray(14)
        data = json.dumps(state, separators=(",", ":")).encode()
        p_len = 12 + len(data)
        struct.pack_into(
            "<HHHHBBI", packet, 0, p_len, 0xA5A5, 0x5A5A, 0, flag, 0x0B, len(data)
        )
        packet.extend(data)
        checksum = sum(packet[0x02:], 0xBEAF) & 0xFFFF
        packet[0x06:0x08] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a JSON packet."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0xA)[0]
        state = json.loads(payload[0xE : 0xE + js_len])
        return state


class lb2(Device):
    """Controls a Broadlink LB26/LB27."""

    TYPE = "LB2"

    @enum.unique
    class ColorMode(enum.IntEnum):
        """Enumerates color modes."""

        RGB = 0
        WHITE = 1
        SCENE = 2

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{'red': 128, 'blue': 255, 'green': 128, 'pwr': 1, 'brightness': 75, 'colortemp': 2700, 'hue': 240, 'saturation': 50, 'transitionduration': 1500, 'maxworktime': 0, 'bulb_colormode': 1, 'bulb_scenes': '["@01686464,0,0,0", "#ffffff,10,0,#000000,190,0,0", "2700+100,0,0,0", "#ff0000,500,2500,#00FF00,500,2500,#0000FF,500,2500,0", "@01686464,100,2400,@01686401,100,2400,0", "@01686464,100,2400,@01686401,100,2400,@005a6464,100,2400,@005a6401,100,2400,0", "@01686464,10,0,@00000000,190,0,0", "@01686464,200,0,@005a6464,200,0,0"]', 'bulb_scene': ''}`
        """
        packet = self._encode(1, {})
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def set_state(
        self,
        pwr: bool = None,
        red: int = None,
        blue: int = None,
        green: int = None,
        brightness: int = None,
        colortemp: int = None,
        hue: int = None,
        saturation: int = None,
        transitionduration: int = None,
        maxworktime: int = None,
        bulb_colormode: int = None,
        bulb_scenes: str = None,
        bulb_scene: str = None,
    ) -> dict:
        """Set the power state of the device."""
        state = {}
        if pwr is not None:
            state["pwr"] = int(bool(pwr))
        if red is not None:
            state["red"] = int(red)
        if blue is not None:
            state["blue"] = int(blue)
        if green is not None:
            state["green"] = int(green)
        if brightness is not None:
            state["brightness"] = int(brightness)
        if colortemp is not None:
            state["colortemp"] = int(colortemp)
        if hue is not None:
            state["hue"] = int(hue)
        if saturation is not None:
            state["saturation"] = int(saturation)
        if transitionduration is not None:
            state["transitionduration"] = int(transitionduration)
        if maxworktime is not None:
            state["maxworktime"] = int(maxworktime)
        if bulb_colormode is not None:
            state["bulb_colormode"] = int(bulb_colormode)
        if bulb_scenes is not None:
            state["bulb_scenes"] = str(bulb_scenes)
        if bulb_scene is not None:
            state["bulb_scene"] = str(bulb_scene)

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
