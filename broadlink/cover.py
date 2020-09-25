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

 class dooya_new(device):
    """Controls a Dooya curtain motor."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "Dooya DT360E(4F6E)"

    def _send(self, magic1: int, magic2: int, magic3:int, magic4:int) -> int:
        """Send a packet to the device."""
        packet = bytearray(32)
        packet[0] = 0x16
        packet[2] = 0xa5
        packet[3] = 0xa5
        packet[4] = 0x5a
        packet[5] = 0x5a
        packet[6] = magic1
        packet[7] = magic2
        packet[8] = 0x02
        packet[9] = 0x0b
        packet[10] = 0x0a
        packet[15] = magic3
        packet[16] = magic4
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[17]

    def open(self) -> int:
        """Open the curtain."""
        return self._send(0xc5, 0xc0, 0x01, 0x00)

    def close(self) -> int:
        """Close the curtain."""
        return self._send(0xc6, 0xc0, 0x02, 0x00)

    def stop(self) -> int:
        """Stop the curtain."""
        return self._send(0xc7, 0xc0, 0x03, 0x00)

    def get_percentage(self) -> int:
        """Return the position of the curtain."""
        return self._send(0xca, 0xc0 ,0x06, 0x5d)

    def set_percentage_and_wait(self, new_percentage) -> int:
        new_percent_hex = struct.pack('<H', 49357+new_percentage)
        magic1 = new_percent_hex[0]
        magic2 = new_percent_hex[1]
        magic3 = 0x09
        magic4 = new_percentage
        return self._send(magic1, magic2, magic3, magic4)
