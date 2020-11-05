"""Support for sensors."""
from .device import device
from .exceptions import check_error


class a1(device):
    """Controls a Broadlink A1."""

    _SENSORS_AND_LEVELS = (
        ("light", ("dark", "dim", "normal", "bright")),
        ("air_quality", ("excellent", "good", "normal", "bad")),
        ("noise", ("quiet", "normal", "noisy")),
    )

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "A1"

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
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        data = bytearray(payload[0x4:])
        return {
            "temperature": data[0x0] + data[0x1] / 10.0,
            "humidity": data[0x2] + data[0x3] / 10.0,
            "light": data[0x4],
            "air_quality": data[0x6],
            "noise": data[0x8],
        }
