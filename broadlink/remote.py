"""Support for universal remotes."""
from .device import device
from .exceptions import check_error


class rm(device):
    """Controls a Broadlink RM."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "RM2"
        self._request_header = bytes()
        self._code_sending_header = bytes()

    def check_data(self) -> bytes:
        """Return the last captured code."""
        packet = bytearray(self._request_header)
        packet.append(0x04)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[len(self._request_header) + 4 :]

    def send_data(self, data: bytes) -> None:
        """Send a code to the device."""
        packet = bytearray(self._code_sending_header)
        packet += bytearray([0x02, 0x00, 0x00, 0x00])
        packet += data
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def enter_learning(self) -> None:
        """Enter infrared learning mode."""
        packet = bytearray(self._request_header)
        packet.append(0x03)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def sweep_frequency(self) -> None:
        """Sweep frequency."""
        packet = bytearray(self._request_header)
        packet.append(0x19)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def cancel_sweep_frequency(self) -> None:
        """Cancel sweep frequency."""
        packet = bytearray(self._request_header)
        packet.append(0x1E)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def check_frequency(self) -> bool:
        """Return True if the frequency was identified successfully."""
        packet = bytearray(self._request_header)
        packet.append(0x1A)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        if payload[len(self._request_header) + 4] == 1:
            return True
        return False

    def find_rf_packet(self) -> bool:
        """Enter radiofrequency learning mode."""
        packet = bytearray(self._request_header)
        packet.append(0x1B)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        if payload[len(self._request_header) + 4] == 1:
            return True
        return False

    def _check_sensors(self, command: int) -> bytes:
        """Return the state of the sensors in raw format."""
        packet = bytearray(self._request_header)
        packet.append(command)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bytearray(payload[len(self._request_header) + 4 :])

    def check_temperature(self) -> int:
        """Return the temperature."""
        data = self._check_sensors(0x1)
        return data[0x0] + data[0x1] / 10.0

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        data = self._check_sensors(0x1)
        return {"temperature": data[0x0] + data[0x1] / 10.0}


class rm4(rm):
    """Controls a Broadlink RM4."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "RM4"
        self._request_header = b"\x04\x00"
        self._code_sending_header = b"\xda\x00"

    def check_temperature(self) -> int:
        """Return the temperature."""
        data = self._check_sensors(0x24)
        return data[0x0] + data[0x1] / 100.0

    def check_humidity(self) -> int:
        """Return the humidity."""
        data = self._check_sensors(0x24)
        return data[0x2] + data[0x3] / 100.0

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        data = self._check_sensors(0x24)
        return {
            "temperature": data[0x0] + data[0x1] / 100.0,
            "humidity": data[0x2] + data[0x3] / 100.0,
        }
