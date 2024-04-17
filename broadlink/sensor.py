"""Support for sensors."""
from typing import Sequence

from . import exceptions as e
from .device import Device


class a1(Device):
    """Controls a Broadlink A1."""

    TYPE = "A1"

    _SENSORS_AND_LEVELS = (
        ("light", ("dark", "dim", "normal", "bright")),
        ("air_quality", ("excellent", "good", "normal", "bad")),
        ("noise", ("quiet", "normal", "noisy")),
    )

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        data = self.check_sensors_raw()
        for sensor, levels in self._SENSORS_AND_LEVELS:
            try:
                data[sensor] = levels[data[sensor]]
            except IndexError:
                data[sensor] = "unknown"
        return data

    def check_sensors_raw(self) -> dict:
        """Return the state of the sensors in raw format."""
        packet = bytearray([0x1])
        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        data = self.decrypt(resp[0x38:])

        return {
            "temperature": data[0x04] + data[0x05] / 10.0,
            "humidity": data[0x06] + data[0x07] / 10.0,
            "light": data[0x08],
            "air_quality": data[0x0A],
            "noise": data[0x0C],
        }


class a2(Device):
    """Controls a Broadlink A2."""

    TYPE = "A2"

    def _send(self, operation: int, data: Sequence = b""):
        """Send a command to the device."""
        packet = bytearray(12)
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x08] = operation
        packet[0x09] = 0x0B

        if data:
            data_len = len(data)
            packet[0x0A] = data_len & 0xFF
            packet[0x0B] = data_len >> 8
            packet += bytes(2)
            packet.extend(data)

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8

        packet_len = len(packet) - 2
        packet[0x00] = packet_len & 0xFF
        packet[0x01] = packet_len >> 8

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        return payload

    def check_sensors_raw(self) -> dict:
        """Return the state of the sensors in raw format."""
        data = self._send(1)

        return {
            "temperature": data[0x13] * 256 + data[0x14],
            "humidity": data[0x15] * 256 + data[0x16],
            "pm10": data[0x0D] * 256 + data[0x0E],
            "pm2_5": data[0x0F] * 256 + data[0x10],
            "pm1": data[0x11] * 256 + data[0x12],
        }
