"""Support for lights."""
import json
from typing import Union

from .device import device
from .exceptions import check_error


class lb1(device):
    """Controls a Broadlink LB1."""

    state_dict = []
    effect_map_dict = {
        "lovely color": 0,
        "flashlight": 1,
        "lightning": 2,
        "color fading": 3,
        "color breathing": 4,
        "multicolor breathing": 5,
        "color jumping": 6,
        "multicolor jumping": 7,
    }

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "SmartBulb"

    def send_command(self, command: str, type: str = "set") -> None:
        """Send a command to the device."""
        packet = bytearray(16 + (int(len(command) / 16) + 1) * 16)
        packet[0x00] = 0x0C + len(command) & 0xFF
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x08] = 0x02 if type == "set" else 0x01  # 0x01 => query, # 0x02 => set
        packet[0x09] = 0x0B
        packet[0x0A] = len(command)
        packet[0x0E:] = map(ord, command)

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x06] = checksum & 0xFF  # Checksum 1 position
        packet[0x07] = checksum >> 8  # Checksum 2 position

        response = self.send_packet(0x6A, packet)
        check_error(response[0x36:0x38])
        payload = self.decrypt(response[0x38:])

        responseLength = int(payload[0x0A]) | (int(payload[0x0B]) << 8)
        if responseLength > 0:
            self.state_dict = json.loads(payload[0x0E : 0x0E + responseLength])

    def set_json(self, jsonstr: str) -> str:
        """Send a command to the device and return state."""
        reconvert = json.loads(jsonstr)
        if "bulb_sceneidx" in reconvert.keys():
            reconvert["bulb_sceneidx"] = self.effect_map_dict.get(
                reconvert["bulb_sceneidx"], 255
            )

        self.send_command(json.dumps(reconvert))
        return json.dumps(self.state_dict)

    def set_state(self, state: Union[str, int]) -> None:
        """Set the state of the device."""
        cmd = '{"pwr":%d}' % (1 if state == "ON" or state == 1 else 0)
        self.send_command(cmd)

    def get_state(self) -> dict:
        """Return the state of the device."""
        cmd = "{}"
        self.send_command(cmd)
        return self.state_dict
