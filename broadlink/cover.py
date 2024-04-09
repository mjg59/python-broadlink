"""Support for covers."""
import time

from . import exceptions as e
from .device import Device


class dooya(Device):
    """Controls a Dooya curtain motor."""

    TYPE = "DT360E"

    def _send(self, command: int, attribute: int = 0) -> int:
        """Send a packet to the device."""
        packet = bytearray(16)
        packet[0] = 0x09
        packet[2] = 0xBB
        packet[3] = command
        packet[4] = attribute
        packet[9] = 0xFA
        packet[10] = 0x44
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[4]

    def open(self) -> int:
        """Open the curtain."""
        return self._send(0x01)

    def close(self) -> int:
        """Close the curtain."""
        return self._send(0x02)

    def stop(self) -> int:
        """Stop the curtain."""
        return self._send(0x03)

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


class dooya2(Device):
    """Controls a Dooya curtain motor (version 2)."""

    TYPE = "DT360E-2"

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
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x11]

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

    def set_percentage(self, new_percentage: int) -> None:
        """Set the position of the curtain."""
        self._send(0x09, new_percentage)
