"""Support for air purifiers."""

import enum

from . import exceptions as e
from .device import Device

@enum.unique
class FanMode(enum.IntEnum):
    """Represents mode of the fan."""

    OFF = 0
    AUTO = 1
    NIGHT = 2
    TURBO = 3
    ANTI_ALLERGY = 4
    MANUAL = 5

    UNKNOWN = -1
    

class lifaair(Device):
    """Controls a broadcom-based LIFAair air purifier."""

    TYPE = "LIFAAIR"

    FAN_STATE_TO_MODE = {
        0x81: FanMode.OFF,
        0xA5: FanMode.AUTO,
        0x95: FanMode.NIGHT,
        0x8D: FanMode.TURBO,
        0x85: FanMode.MANUAL,
        0x01: None, # fan is offline
    }

    @enum.unique
    class _Operation(enum.IntEnum):
        SET_STATE = 1
        GET_STATE = 2

    @enum.unique
    class _Action(enum.IntEnum):
        SET_FAN_SPEED = 1
        SET_FAN_MODE = 2

    FAN_MODE_TO_ACTION_ARG = {
        FanMode.OFF: 1,
        FanMode.AUTO: 2,
        FanMode.NIGHT: 6,
        FanMode.TURBO: 7,
        FanMode.ANTI_ALLERGY: 11,
    }

    def set_fan_mode(self, fan_mode: FanMode) -> dict:
        """Set mode of the fan. Returns updated state."""
        if fan_mode == FanMode.MANUAL:
            return self.set_fan_speed(50)

        action_arg = self.FAN_MODE_TO_ACTION_ARG.get(fan_mode)
        if action_arg is not None:
            data = self._send(
                self._Operation.SET_STATE, self._Action.SET_FAN_MODE, action_arg
            )
            return self._decode_state(data)

        return self.get_state()

    def set_fan_speed(self, fan_speed: int) -> dict:
        """Set fan speed (0-121). Returns updated state. Note that fan mode will be changed to MANUAL by the device."""
        data = self._send(
            self._Operation.SET_STATE, self._Action.SET_FAN_SPEED, fan_speed
        )
        return self._decode_state(data)

    def get_state(self) -> dict:
        """
        Return the current state of the purifier as python dict.
        
        Note that the smart remote we're communicating with contains co2, tvoc and PM2.5 sensors,
        while temperature, humidity and fan-state are fetched remotely from main unit which can be
        offline (unplugged from mains, out of range) in which case those keys will be None.
        
        Format:
        {
            "temperature": 24.5,      # float, deg C, can be None if main-unit offline
            "humidity": 41,           # int, %, can be None if main-unit offline
            "co2": 425                # int, ppm
            "tvoc": 150               # int, ug/m3
            "pm10": 9                 # int, ug/m3 (unsure if this is PM10)
            "pm2_5": 7                # int, ug/m3 (confirmed PM2.5)
            "pm1": 5                  # int, ug/m3 (unsure if this is PM1.0)
            "fan_mode": FanMode.AUTO  # FanMode enum, can be None if main-unit offline
            "fan_speed": 50           # int, 0-121
        }
        """
        data = self._send(self._Operation.GET_STATE)
        return self._decode_state(data)
    
    def _decode_state(self, data: bytes) -> dict:
        raw = self._decode_state_raw(data)
        fan_mode = self._decode_fan_mode(raw["fan_state"], raw["fan_flags"])
        isOffline = fan_mode is None
        return {
            "temperature": None if isOffline else raw["temperature"] / 10.0,
            "humidity": None if isOffline else raw["humidity"],
            "co2": raw["co2"],
            "tvoc": raw["tvoc"] * 10,
            "pm10": raw["pm10"],
            "pm2_5": raw["pm2_5"],
            "pm1": raw["pm1"],
            "fan_mode": fan_mode,
            "fan_speed": raw["fan_speed"],
        }

    def _decode_state_raw(self, data: bytes) -> dict:
        return {
            "temperature": data[27] + 256 * data[28],
            "humidity": data[29],
            "co2": data[31] + 256 * data[32],
            "tvoc": data[35] + 256 * data[36],
            "pm10": data[37] + 256 * data[38],
            "pm2_5": data[39] + 256 * data[40],
            "pm1": data[41] + 256 * data[42],
            "fan_state": data[55],
            "fan_speed": data[56],
            "fan_flags": data[57],
        }

    def _decode_fan_mode(self, fan_state: int, fan_flags: int) -> FanMode:
        if fan_flags & 0x40 == 0:
            return FanMode.ANTI_ALLERGY
        return self.FAN_STATE_TO_MODE.get(fan_state, FanMode.UNKNOWN)
    
    def _send(self, operation: int, action: int = 0, action_arg: int = 0) -> bytes:
        """Send a command to the device."""
        packet = bytearray(26)
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x08] = operation & 0xFF
        packet[0x0A] = 0x0C
        packet[0x0E] = action & 0xFF
        packet[0x0F] = action_arg & 0xFF

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8

        packet_len = len(packet) - 2
        packet[0x00] = packet_len & 0xFF
        packet[0x01] = packet_len >> 8

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        return self.decrypt(resp[0x38:])
