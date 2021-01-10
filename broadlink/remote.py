"""Support for universal remotes."""
import struct

from .device import device
from .exceptions import check_error


class rm(device):
    """Controls a Broadlink RM."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "RM2"

    def _send(self, command: int, data: bytes = b'') -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<I", command) + data
        resp = self.send_packet(0x6A, packet)
        check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        return payload[0x4:]

    def check_data(self) -> bytes:
        """Return the last captured code."""
        return self._send(0x4)

    def send_data(self, data: bytes) -> None:
        """Send a code to the device."""
        self._send(0x2, data)

    def enter_learning(self) -> None:
        """Enter infrared learning mode."""
        self._send(0x3)

    def sweep_frequency(self) -> None:
        """Sweep frequency."""
        self._send(0x19)

    def cancel_sweep_frequency(self) -> None:
        """Cancel sweep frequency."""
        self._send(0x1E)

    def check_frequency(self) -> bool:
        """Return True if the frequency was identified successfully."""
        resp = self._send(0x1A)
        return resp[0] == 1

    def find_rf_packet(self) -> bool:
        """Enter radiofrequency learning mode."""
        resp = self._send(0x1B)
        return resp[0] == 1

    def check_temperature(self) -> float:
        """Return the temperature."""
        return self.check_sensors()["temperature"]

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self._send(0x1)
        temperature = struct.unpack("<bb", resp[:0x2])
        temperature = temperature[0x0] + temperature[0x1] / 10.0
        return {"temperature": temperature}


class rm4(rm):
    """Controls a Broadlink RM4."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "RM4"

    def _send(self, command: int, data: bytes = b'') -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<HI", len(data) + 4, command) + data
        resp = self.send_packet(0x6A, packet)
        check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        p_len = struct.unpack("<H", payload[:0x2])[0]
        return payload[0x6:p_len+2]

    def find_rf_packet(self) -> bool:
        """Enter radiofrequency learning mode."""
        self._send(0x1B)
        return True

    def check_humidity(self) -> float:
        """Return the humidity."""
        return self.check_sensors()["humidity"]

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self._send(0x24)
        temperature = struct.unpack("<bb", resp[:0x2])
        temperature = temperature[0x0] + temperature[0x1] / 100.0
        humidity = resp[0x2] + resp[0x3] / 100.0
        return {"temperature": temperature, "humidity": humidity}
