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
        packet[2] = 0xbb
        packet[3] = magic1
        packet[4] = magic2
        packet[9] = 0xfa
        packet[10] = 0x44
        response = self.send_packet(0x6a, packet)
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
        return self._send(0x06, 0x5d)

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
