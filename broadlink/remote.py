"""Support for universal remotes."""
import struct

from . import exceptions as e
from .device import device, v4


class rmmini(device):
    """Controls a Broadlink RM mini 3."""

    TYPE = "RMMINI"

    def send_data(self, data: bytes) -> None:
        """Send a code to the device."""
        self.send_cmd(0x02, data, retry_intvl=5.0)

    def enter_learning(self) -> None:
        """Enter infrared learning mode."""
        self.send_cmd(0x03)

    def check_data(self) -> bytes:
        """Return the last captured code."""
        return self.send_cmd(0x04)


class rmpro(rmmini):
    """Controls a Broadlink RM pro."""

    TYPE = "RMPRO"

    def sweep_frequency(self) -> None:
        """Sweep frequency."""
        self.send_cmd(0x19)

    def check_frequency(self) -> bool:
        """Return True if the frequency was identified successfully."""
        resp = self.send_cmd(0x1A)
        return resp[0] == 1

    def find_rf_packet(self) -> None:
        """Enter radiofrequency learning mode."""
        self.send_cmd(0x1B)

    def cancel_sweep_frequency(self) -> None:
        """Cancel sweep frequency."""
        self.send_cmd(0x1E)

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self.send_cmd(0x01)
        temp = struct.unpack("<bb", resp[:0x02])
        return {"temperature": temp[0x00] + temp[0x01] / 10.0}

    def check_temperature(self) -> float:
        """Return the temperature."""
        return self.check_sensors()["temperature"]


class rmminib(rmmini, metaclass=v4):
    """Controls a Broadlink RM mini 3 (new firmware)."""

    TYPE = "RMMINIB"


class rm4mini(rmminib):
    """Controls a Broadlink RM4 mini."""
    
    TYPE = "RM4MINI"

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self.send_cmd(0x24)
        temp = struct.unpack("<bb", resp[:0x02])
        return {
            "temperature": temp[0x00] + temp[0x01] / 100.0,
            "humidity": resp[0x02] + resp[0x03] / 100.0
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
