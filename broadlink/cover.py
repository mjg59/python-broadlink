"""Support for covers."""
import time

from .device import device
from .exceptions import check_error


class dooya(device):
    """Controls a Dooya curtain motor."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "Dooya DT360E"

    def _send(self, magic1: int, magic2: int) -> int:
        """Send a packet to the device."""
        packet = bytearray(16)
        packet[0] = 0x09
        packet[2] = 0xBB
        packet[3] = magic1
        packet[4] = magic2
        packet[9] = 0xFA
        packet[10] = 0x44
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[4]

    def open(self) -> int:
        """Open the curtain."""
        return self._send(0x01, 0x00)

    def close(self) -> int:
        """Close the curtain."""
        return self._send(0x02, 0x00)

    def stop(self) -> int:
        """Stop the curtain."""
        return self._send(0x03, 0x00)

    def get_percentage(self) -> int:
        """Return the position of the curtain."""
        return self._send(0x06, 0x5D)

    def set_percentage_and_wait(self, new_percentage: int) -> None:
        """Set the position of the curtain."""
        current = self.get_percentage()
        if current > new_percentage:
            self.close()
            while current is not None and current > new_percentage:
                time.sleep(0.2)
                current = self.get_percentage()

        elif current < new_percentage:
            self.open()
            while current is not None and current < new_percentage:
                time.sleep(0.2)
                current = self.get_percentage()
        self.stop()

class dooya_new(device):
    """Controls a Dooya curtain motor."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "Dooya DT360E(4F6E)"

    def _send(self, command: int, attribute: int = 0) -> int:
        """Send a packet to the device."""
        checksum = 0xC0C4 + command + attribute & 0xFFFF
        packet = bytearray(32)
        packet[0] = 0x16
        packet[2] = 0xA5
        packet[3] = 0xA5
        packet[4] = 0x5A
        packet[5] = 0x5A
        packet[6] = checksum & 0xFF
        packet[7] = checksum >> 8
        packet[8] = 0x02
        packet[9] = 0x0B
        packet[10] = 0x0A
        packet[15] = command
        packet[16] = attribute
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[17]

    def open(self) -> None:
        """Open the curtain."""
        self._send(0x01)

    def close(self) -> None:
        """Close the curtain."""
        self._send(0x02)

    def stop(self) -> None:
        """Stop the curtain."""
        self._send(0x03)

    def get_percentage(self) -> int:
        """Return the position of the curtain."""
        return self._send(0x06)

    def set_percentage(self, new_percentage) -> None:
        """Set the position of the curtain."""
        self._send(0x09, new_percentage)
