"""Support for lights."""
import json
from typing import Union
import struct

from .device import device
from .exceptions import check_error


class lb1(device):
    """Controls a Broadlink LB1."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "SmartBulb"

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{'red': 128, 'blue': 255, 'green': 128, 'pwr': 1, 'brightness': 75, 'colortemp': 2700, 'hue': 240, 'saturation': 50, 'transitionduration': 1500, 'maxworktime': 0, 'bulb_colormode': 1, 'bulb_scenes': '["@01686464,0,0,0", "#ffffff,10,0,#000000,190,0,0", "2700+100,0,0,0", "#ff0000,500,2500,#00FF00,500,2500,#0000FF,500,2500,0", "@01686464,100,2400,@01686401,100,2400,0", "@01686464,100,2400,@01686401,100,2400,@005a6464,100,2400,@005a6401,100,2400,0", "@01686464,10,0,@00000000,190,0,0", "@01686464,200,0,@005a6464,200,0,0"]', 'bulb_scene': '', 'bulb_sceneidx': 255}`
        """
        packet = self._encode(1, b"{}")
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
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
    ) -> dict:
        """Set the power state of the device."""
        data = {}
        if pwr is not None:
            data["pwr"] = int(bool(pwr))
        if red is not None:
            data["red"] = int(red)
        if blue is not None:
            data["blue"] = int(blue)
        if green is not None:
            data["green"] = int(green)
        if brightness is not None:
            data["brightness"] = brightness
        if colortemp is not None:
            data["colortemp"] = colortemp
        if hue is not None:
            data["hue"] = hue
        if saturation is not None:
            data["saturation"] = saturation
        if transitionduration is not None:
            data["transitionduration"] = transitionduration
        if maxworktime is not None:
            data["maxworktime"] = maxworktime
        if bulb_colormode is not None:
            data["bulb_colormode"] = bulb_colormode
        js = json.dumps(data).encode("utf8")
        packet = self._encode(2, js)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        return self._decode(response)

    def _encode(self, flag: int, js: str) -> bytes:
        """Encode a message."""
        #  The packet format is:
        #  0x00-0x01 length
        #  0x02-0x05 header
        #  0x06-0x07 00
        #  0x08 flag (1 for read or 2 write?)
        #  0x09 unknown (0xb)
        #  0x0a-0x0d length of json
        #  0x0e- json data
        packet = bytearray(14)
        length = 4 + 2 + 2 + 4 + len(js)
        struct.pack_into(
            "<HHHHBBI", packet, 0, length, 0xA5A5, 0x5A5A, 0x0000, flag, 0x0B, len(js)
        )
        for i in range(len(js)):
            packet.append(js[i])

        checksum = sum(packet[0x08:], 0xC0AD) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x0A)[0]
        state = json.loads(payload[0x0E : 0x0E + js_len])
        return state