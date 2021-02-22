"""Support for universal remotes."""
import struct

from . import exceptions as e
from .device import device


class rmmini(device):
    """Controls a Broadlink RM mini 3."""

    TYPE = "RMMINI"

    def _send(self, command: int, data: bytes = b'') -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<I", command) + data
        resp, err = self.send_packet(0x6A, packet)
        if err:
            raise e.exception(err)
        return resp[0x4:]

    def send_data(self, data: bytes) -> None:
        """Send a code to the device."""
        self._send(0x2, data)

    def enter_learning(self) -> None:
        """Enter infrared learning mode."""
        self._send(0x3)

    def check_data(self) -> bytes:
        """Return the last captured code."""
        return self._send(0x4)


class rmpro(rmmini):
    """Controls a Broadlink RM pro."""

    TYPE = "RMPRO"

    def sweep_frequency(self) -> None:
        """Sweep frequency."""
        self._send(0x19)

    def check_frequency(self) -> bool:
        """Return True if the frequency was identified successfully."""
        resp = self._send(0x1A)
        return resp[0] == 1

    def find_rf_packet(self) -> None:
        """Enter radiofrequency learning mode."""
        self._send(0x1B)

    def cancel_sweep_frequency(self) -> None:
        """Cancel sweep frequency."""
        self._send(0x1E)

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self._send(0x1)
        temp = struct.unpack("<bb", resp[:0x2])
        return {"temperature": temp[0x0] + temp[0x1] / 10.0}

    def check_temperature(self) -> float:
        """Return the temperature."""
        return self.check_sensors()["temperature"]


class rmminib(rmmini):
    """Controls a Broadlink RM mini 3 (new firmware)."""

    TYPE = "RMMINIB"

    def _send(self, command: int, data: bytes = b'') -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<HI", len(data) + 4, command) + data
        resp, err = self.send_packet(0x6A, packet)
        if err:
            raise e.exception(err)
        p_len = struct.unpack("<H", resp[:0x2])[0]
        return resp[0x6:p_len+2]


class rm4mini(rmminib):
    """Controls a Broadlink RM4 mini."""
    
    TYPE = "RM4MINI"

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self._send(0x24)
        temp = struct.unpack("<bb", resp[:0x2])
        return {
            "temperature": temp[0x0] + temp[0x1] / 100.0,
            "humidity": resp[0x2] + resp[0x3] / 100.0
        }

    def check_temperature(self) -> float:
        """Return the temperature."""
        return self.check_sensors()["temperature"]

    def check_humidity(self) -> float:
        """Return the humidity."""
        return self.check_sensors()["humidity"]


class rm4pro(rm4mini, rmpro):
    """Controls a Broadlink RM4 pro."""

    TYPE = "RM4PRO"


class rm(rmpro):
    """For backwards compatibility."""

    TYPE = "RM2"


class rm4(rm4pro):
    """For backwards compatibility."""

    TYPE = "RM4"
