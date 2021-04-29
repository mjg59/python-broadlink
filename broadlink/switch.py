"""Support for switches."""
import json
import struct

from . import exceptions as e
from .device import Device


class sp1(Device):
    """Controls a Broadlink SP1."""

    TYPE = "SP1"

    def set_power(self, pwr: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(4)
        packet[0] = bool(pwr)
        response = self.send_packet(0x66, packet)
        e.check_error(response[0x22:0x24])


class sp2(Device):
    """Controls a Broadlink SP2."""

    TYPE = "SP2"

    def set_power(self, pwr: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        packet[4] = bool(pwr)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4])


class sp2s(sp2):
    """Controls a Broadlink SP2S."""

    TYPE = "SP2S"

    def get_energy(self) -> float:
        """Return the power consumption in W."""
        packet = bytearray(16)
        packet[0] = 4
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return int.from_bytes(payload[0x4:0x7], "little") / 1000


class sp3(Device):
    """Controls a Broadlink SP3."""

    TYPE = "SP3"

    def set_power(self, pwr: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        packet[4] = self.check_nightlight() << 1 | bool(pwr)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])

    def set_nightlight(self, ntlight: bool) -> None:
        """Set the night light state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        packet[4] = bool(ntlight) << 1 | self.check_power()
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] & 1)

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] & 2)


class sp3s(sp2):
    """Controls a Broadlink SP3S."""

    TYPE = "SP3S"

    def get_energy(self) -> float:
        """Return the power consumption in W."""
        packet = bytearray([8, 0, 254, 1, 5, 1, 0, 0, 0, 45])
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        energy = payload[0x7:0x4:-1].hex()
        return int(energy) / 100


class sp4(Device):
    """Controls a Broadlink SP4."""

    TYPE = "SP4"

    def set_power(self, pwr: bool) -> None:
        """Set the power state of the device."""
        self.set_state(pwr=pwr)

    def set_nightlight(self, ntlight: bool) -> None:
        """Set the night light state of the device."""
        self.set_state(ntlight=ntlight)

    def set_state(
        self,
        pwr: bool = None,
        ntlight: bool = None,
        indicator: bool = None,
        ntlbrightness: int = None,
        maxworktime: int = None,
        childlock: bool = None,
    ) -> dict:
        """Set state of device."""
        state = {}
        if pwr is not None:
            state["pwr"] = int(bool(pwr))
        if ntlight is not None:
            state["ntlight"] = int(bool(ntlight))
        if indicator is not None:
            state["indicator"] = int(bool(indicator))
        if ntlbrightness is not None:
            state["ntlbrightness"] = ntlbrightness
        if maxworktime is not None:
            state["maxworktime"] = maxworktime
        if childlock is not None:
            state["childlock"] = int(bool(childlock))

        packet = self._encode(2, state)
        response = self.send_packet(0x6A, packet)
        return self._decode(response)

    def check_power(self) -> bool:
        """Return the power state of the device."""
        state = self.get_state()
        return bool(state["pwr"])

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        state = self.get_state()
        return bool(state["ntlight"])

    def get_state(self) -> dict:
        """Get full state of device."""
        packet = self._encode(1, {})
        response = self.send_packet(0x6A, packet)
        return self._decode(response)

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a message."""
        packet = bytearray(12)
        data = json.dumps(state, separators=(",", ":")).encode()
        struct.pack_into(
            "<HHHBBI", packet, 0, 0xA5A5, 0x5A5A, 0x0000, flag, 0x0B, len(data)
        )
        packet.extend(data)
        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x04:0x06] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x08)[0]
        state = json.loads(payload[0x0C : 0x0C + js_len])
        return state


class sp4b(sp4):
    """Controls a Broadlink SP4 (type B)."""

    TYPE = "SP4B"

    def get_state(self) -> dict:
        """Get full state of device."""
        state = super().get_state()

        # Convert sensor data to float. Remove keys if sensors are not supported.
        sensor_attrs = ["current", "volt", "power", "totalconsum", "overload"]
        for attr in sensor_attrs:
            value = state.pop(attr, -1)
            if value != -1:
                state[attr] = value / 1000
        return state

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a message."""
        packet = bytearray(14)
        data = json.dumps(state, separators=(",", ":")).encode()
        length = 12 + len(data)
        struct.pack_into(
            "<HHHHBBI",
            packet,
            0,
            length,
            0xA5A5,
            0x5A5A,
            0x0000,
            flag,
            0x0B,
            len(data),
        )
        packet.extend(data)
        checksum = sum(packet[0x02:], 0xBEAF) & 0xFFFF
        packet[0x06:0x08] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0xA)[0]
        state = json.loads(payload[0x0E : 0x0E + js_len])
        return state


class bg1(Device):
    """Controls a BG Electrical smart outlet."""

    TYPE = "BG1"

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{"pwr":1,"pwr1":1,"pwr2":0,"maxworktime":60,"maxworktime1":60,"maxworktime2":0,"idcbrightness":50}`
        """
        packet = self._encode(1, {})
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def set_state(
        self,
        pwr: bool = None,
        pwr1: bool = None,
        pwr2: bool = None,
        maxworktime: int = None,
        maxworktime1: int = None,
        maxworktime2: int = None,
        idcbrightness: int = None,
    ) -> dict:
        """Set the power state of the device."""
        state = {}
        if pwr is not None:
            state["pwr"] = int(bool(pwr))
        if pwr1 is not None:
            state["pwr1"] = int(bool(pwr1))
        if pwr2 is not None:
            state["pwr2"] = int(bool(pwr2))
        if maxworktime is not None:
            state["maxworktime"] = maxworktime
        if maxworktime1 is not None:
            state["maxworktime1"] = maxworktime1
        if maxworktime2 is not None:
            state["maxworktime2"] = maxworktime2
        if idcbrightness is not None:
            state["idcbrightness"] = idcbrightness

        packet = self._encode(2, state)
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a message."""
        packet = bytearray(14)
        data = json.dumps(state).encode()
        length = 12 + len(data)
        struct.pack_into(
            "<HHHHBBI", packet, 0, length, 0xA5A5, 0x5A5A, 0x0000, flag, 0x0B, len(data)
        )
        packet.extend(data)
        checksum = sum(packet[0x2:], 0xBEAF) & 0xFFFF
        packet[0x06:0x08] = checksum.to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x0A)[0]
        state = json.loads(payload[0x0E : 0x0E + js_len])
        return state


class mp1(Device):
    """Controls a Broadlink MP1."""

    TYPE = "MP1"

    def set_power_mask(self, sid_mask: int, pwr: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0x00] = 0x0D
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x06] = 0xB2 + ((sid_mask << 1) if pwr else sid_mask)
        packet[0x07] = 0xC0
        packet[0x08] = 0x02
        packet[0x0A] = 0x03
        packet[0x0D] = sid_mask
        packet[0x0E] = sid_mask if pwr else 0

        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])

    def set_power(self, sid: int, pwr: bool) -> None:
        """Set the power state of the device."""
        sid_mask = 0x01 << (sid - 1)
        self.set_power_mask(sid_mask, pwr)

    def check_power_raw(self) -> int:
        """Return the power state of the device in raw format."""
        packet = bytearray(16)
        packet[0x00] = 0x0A
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x06] = 0xAE
        packet[0x07] = 0xC0
        packet[0x08] = 0x01

        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x0E]

    def check_power(self) -> dict:
        """Return the power state of the device."""
        data = self.check_power_raw()
        return {
            "s1": bool(data & 1),
            "s2": bool(data & 2),
            "s3": bool(data & 4),
            "s4": bool(data & 8),
        }
