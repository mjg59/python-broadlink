"""Support for covers."""
import time

from . import device
from . import exceptions as e


class dooya(device.device):
    """Controls a Dooya curtain motor."""

    _TYPE = "Dooya DT360E"

    def _send(self, magic1: int, magic2: int) -> int:
        """Send a packet to the device."""
        packet = bytearray(16)
        packet[0] = 0x09
        packet[2] = 0xBB
        packet[3] = magic1
        packet[4] = magic2
        packet[9] = 0xFA
        packet[10] = 0x44
        resp, err = self.send_packet(0x6A, packet)
        e.check_error(err)
        return resp[4]

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
