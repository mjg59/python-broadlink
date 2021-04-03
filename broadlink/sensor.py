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
