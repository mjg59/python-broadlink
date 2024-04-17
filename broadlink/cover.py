"""Support for covers."""
import time
from typing import Sequence

from . import exceptions as e
from .device import Device


class dooya(Device):
    """Controls a Dooya curtain motor."""

    TYPE = "DT360E"

    def _send(self, command: int, attribute: int = 0) -> int:
        """Send a packet to the device."""
        packet = bytearray(16)
        packet[0x00] = 0x09
        packet[0x02] = 0xBB
        packet[0x03] = command
        packet[0x04] = attribute
        packet[0x09] = 0xFA
        packet[0x0A] = 0x44

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
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

    def _send(self, operation: int, data: Sequence = b""):
        """Send a command to the device."""
        packet = bytearray(12)
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x08] = operation
        packet[0x09] = 0x0B

        if data:
            data_len = len(data)
            packet[0x0A] = data_len & 0xFF
            packet[0x0B] = data_len >> 8
            packet += bytes(2)
            packet.extend(data)

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8

        packet_len = len(packet) - 2
        packet[0x00] = packet_len & 0xFF
        packet[0x01] = packet_len >> 8

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        return payload

    def open(self) -> None:
        """Open the curtain."""
        self._send(2, [0x00, 0x01, 0x00])

    def close(self) -> None:
        """Close the curtain."""
        self._send(2, [0x00, 0x02, 0x00])

    def stop(self) -> None:
        """Stop the curtain."""
        self._send(2, [0x00, 0x03, 0x00])

    def get_percentage(self) -> int:
        """Return the position of the curtain."""
        resp = self._send(1, [0x00, 0x06, 0x00])
        return resp[0x11]

    def set_percentage(self, new_percentage: int) -> None:
        """Set the position of the curtain."""
        self._send(2, [0x00, 0x09, new_percentage])


class wser(Device):
    """Controls a Wistar curtain motor"""

    TYPE = "WSER"

    def _send(self, operation: int, data: Sequence = b""):
        """Send a command to the device."""
        packet = bytearray(12)
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x08] = operation
        packet[0x09] = 0x0B

        if data:
            data_len = len(data)
            packet[0x0A] = data_len & 0xFF
            packet[0x0B] = data_len >> 8
            packet += bytes(2)
            packet.extend(data)

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8

        packet_len = len(packet) - 2
        packet[0x00] = packet_len & 0xFF
        packet[0x01] = packet_len >> 8

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        return payload

    def get_position(self) -> int:
        """Return the position of the curtain."""
        resp = self._send(1, [])
        position = resp[0x0E]
        return position

    def open(self) -> int:
        """Open the curtain."""
        resp = self._send(2, [0x4A, 0x31, 0xA0])
        position = resp[0x0E]
        return position

    def close(self) -> int:
        """Close the curtain."""
        resp = self._send(2, [0x61, 0x32, 0xA0])
        position = resp[0x0E]
        return position

    def stop(self) -> int:
        """Stop the curtain."""
        resp = self._send(2, [0x4C, 0x73, 0xA0])
        position = resp[0x0E]
        return position

    def set_position(self, position: int) -> int:
        """Set the position of the curtain."""
        resp = self._send(2, [position, 0x70, 0xA0])
        position = resp[0x0E]
        return position
