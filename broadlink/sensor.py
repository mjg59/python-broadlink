"""Support for sensors."""
import struct

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
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        data = payload[0x4:]

        temperature = struct.unpack("<bb", data[:0x2])
        temperature = temperature[0x0] + temperature[0x1] / 10.0
        humidity = data[0x2] + data[0x3] / 10.0

        return {
            "temperature": temperature,
            "humidity": humidity,
            "light": data[0x4],
            "air_quality": data[0x6],
            "noise": data[0x8],
        }


class a2(Device):
    """Controls a Broadlink A2."""

    TYPE = "A2"

    def _send(self, operation: int, data: bytes = b""):
        """Send a command to the device."""
        packet = bytearray(14)
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
            packet += bytes(data)

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
        resp = self._send(1)
        data = resp[0x6:]
        return {
            "temperature": data[0x0D] * 255 + data[0x0E],
            "humidity": data[0x0F] * 255 + data[0x10],
            "pm100": data[0x07] * 255 + data[0x08],
            "pm25": data[0x09] * 255 + data[0x0A],
            "pm10": data[0x0B] * 255 + data[0x0C],
        }
