"""Support for sensors."""
import enum
import struct

from .device import device
from .exceptions import check_error, exception


class a1(device):
    """Controls a Broadlink A1."""

    @enum.unique
    class Light(enum.IntEnum):
        """Enumerates light levels."""
        DARK = 0
        DIM = 1
        NORMAL = 2
        BRIGHT = 3

    @enum.unique
    class AirQuality(enum.IntEnum):
        """Enumerates air quality levels."""
        EXCELLENT = 0
        GOOD = 1
        NORMAL = 2
        BAD = 3

    @enum.unique
    class Noise(enum.IntEnum):
        """Enumerates noise levels."""
        QUIET = 0
        NORMAL = 1
        NOISY = 2

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "A1"

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        data = self._check_sensors()
        for sensor in {"light", "air_quality", "noise"}:
            data[sensor] = data[sensor].name.lower()
        return data

    def check_sensors_raw(self) -> dict:
        """Return the state of the sensors in raw format."""
        data = self._check_sensors()
        for sensor in {"light", "air_quality", "noise"}:
            data[sensor] = data[sensor].value
        return data

    def _check_sensors(self) -> dict:
        """Return the state of the sensors."""
        packet = bytearray([0x1])
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        data = payload[0x4:]

        temperature = struct.unpack("<bb", data[:0x2])
        temperature = temperature[0x0] + temperature[0x1] / 10.0
        humidity = data[0x2] + data[0x3] / 10.0

        try:
            if not -5 <= temperature <= 85:
                raise ValueError("Temperature out of range: %s" % temperature)

            if humidity > 100:
                raise ValueError("Humidity out of range: %s" % humidity)

            return {
                "temperature": temperature,
                "humidity": humidity,
                "light": self.Light(data[0x4]),
                "air_quality": self.AirQuality(data[0x6]),
                "noise": self.Noise(data[0x8]),
            }

        except ValueError as err:
            raise exception(-4026, "The device returned malformed data", data) from err
