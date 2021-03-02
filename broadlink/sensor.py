"""Support for sensors."""
import struct

from .device import device


class a1(device):
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
        resp = self.send_cmd(0x01)
        temp = struct.unpack("<bb", resp[:0x02])

        return {
            "temperature": temp[0x00] + temp[0x01] / 10.0,
            "humidity": resp[0x02] + resp[0x03] / 10.0,
            "light": resp[0x04],
            "air_quality": resp[0x06],
            "noise": resp[0x08],
        }
