"""Support for universal remotes."""
import struct

from . import exceptions as e
from .device import Device

TICK = 32.84
IR_TOKEN = 0x26


def durations_to_ir_data(durations) -> None:
    result = bytearray()
    result.append(IR_TOKEN)
    result.append(0)
    result.append(len(durations) % 256)
    result.append(len(durations) / 256)
    for dur in durations:
        num = int(round(dur / TICK))
        if num > 255:
            result.append(0)
            result.append(num / 256)
        result.append(num % 256)
    return result


def data_to_durations(bytes):
    result = []
    # XXX: Should check IR/RF token, repeat and length bytes.
    index = 4
    while index < len(bytes):
        chunk = bytes[index]
        index += 1
        if chunk == 0:
            chunk = bytes[index]
            chunk = 256 * chunk + bytes[index + 1]
            index += 2
        result.append(int(round(chunk * TICK)))
        if chunk == 0x0D05:
            break
    return result


class rmmini(Device):
    """Controls a Broadlink RM mini 3."""

    TYPE = "RMMINI"

    def _send(self, command: int, data: bytes = b"") -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<I", command) + data
        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        return payload[0x4:]

    def update(self) -> None:
        """Update device name and lock status."""
        resp = self._send(0x1)
        self.name = resp[0x48:].split(b"\x00")[0].decode()
        self.is_locked = bool(resp[0x87])

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

    def _send(self, command: int, data: bytes = b"") -> bytes:
        """Send a packet to the device."""
        packet = struct.pack("<HI", len(data) + 4, command) + data
        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        payload = self.decrypt(resp[0x38:])
        p_len = struct.unpack("<H", payload[:0x2])[0]
        return payload[0x6 : p_len + 2]


class rm4mini(rmminib):
    """Controls a Broadlink RM4 mini."""

    TYPE = "RM4MINI"

    def check_sensors(self) -> dict:
        """Return the state of the sensors."""
        resp = self._send(0x24)
        temp = struct.unpack("<bb", resp[:0x2])
        return {
            "temperature": temp[0x0] + temp[0x1] / 100.0,
            "humidity": resp[0x2] + resp[0x3] / 100.0,
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
