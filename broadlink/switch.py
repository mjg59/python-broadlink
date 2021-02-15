"""Support for switches."""
import json
import struct

from .device import device
from .exceptions import check_error


class mp1(device):
    """Controls a Broadlink MP1."""

    TYPE = "MP1"

    def set_power_mask(self, sid_mask: int, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0x00] = 0x0D
        packet[0x02] = 0xA5
        packet[0x03] = 0xA5
        packet[0x04] = 0x5A
        packet[0x05] = 0x5A
        packet[0x06] = 0xB2 + ((sid_mask << 1) if state else sid_mask)
        packet[0x07] = 0xC0
        packet[0x08] = 0x02
        packet[0x0A] = 0x03
        packet[0x0D] = sid_mask
        packet[0x0E] = sid_mask if state else 0

        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def set_power(self, sid: int, state: bool) -> None:
        """Set the power state of the device."""
        sid_mask = 0x01 << (sid - 1)
        self.set_power_mask(sid_mask, state)

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
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x0E]

    def check_power(self) -> dict:
        """Return the power state of the device."""
        state = self.check_power_raw()
        if state is None:
            return {"s1": None, "s2": None, "s3": None, "s4": None}
        data = {}
        data["s1"] = bool(state & 0x01)
        data["s2"] = bool(state & 0x02)
        data["s3"] = bool(state & 0x04)
        data["s4"] = bool(state & 0x08)
        return data


class bg1(device):
    """Controls a BG Electrical smart outlet."""

    TYPE = "BG1"

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{"pwr":1,"pwr1":1,"pwr2":0,"maxworktime":60,"maxworktime1":60,"maxworktime2":0,"idcbrightness":50}`
        """
        packet = self._encode(1, b"{}")
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
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
        data = {}
        if pwr is not None:
            data["pwr"] = int(bool(pwr))
        if pwr1 is not None:
            data["pwr1"] = int(bool(pwr1))
        if pwr2 is not None:
            data["pwr2"] = int(bool(pwr2))
        if maxworktime is not None:
            data["maxworktime"] = maxworktime
        if maxworktime1 is not None:
            data["maxworktime1"] = maxworktime1
        if maxworktime2 is not None:
            data["maxworktime2"] = maxworktime2
        if idcbrightness is not None:
            data["idcbrightness"] = idcbrightness
        js = json.dumps(data).encode("utf8")
        packet = self._encode(2, js)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        return self._decode(response)

    def _encode(self, flag: int, js: str) -> bytes:
        """Encode a message."""
        #  The packet format is:
        #  0x00-0x01 length
        #  0x02-0x05 header
        #  0x06-0x07 00
        #  0x08 flag (1 for read or 2 write?)
        #  0x09 unknown (0xb)
        #  0x0a-0x0d length of json
        #  0x0e- json data
        packet = bytearray(14)
        length = 4 + 2 + 2 + 4 + len(js)
        struct.pack_into(
            "<HHHHBBI", packet, 0, length, 0xA5A5, 0x5A5A, 0x0000, flag, 0x0B, len(js)
        )
        for i in range(len(js)):
            packet.append(js[i])

        checksum = sum(packet[0x08:], 0xC0AD) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0x0A)[0]
        state = json.loads(payload[0x0E : 0x0E + js_len])
        return state


class sp1(device):
    """Controls a Broadlink SP1."""

    TYPE = "SP1"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(4)
        packet[0] = state
        response = self.send_packet(0x66, packet)
        check_error(response[0x22:0x24])


class sp2(device):
    """Controls a Broadlink SP2."""

    TYPE = "SP2"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        packet[4] = int(bool(state))
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
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
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return int.from_bytes(payload[0x4:0x7], "little") / 1000


class sp3(device):
    """Controls a Broadlink SP3."""

    TYPE = "SP3"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        if self.check_nightlight():
            packet[4] = 3 if state else 2
        else:
            packet[4] = 1 if state else 0
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def set_nightlight(self, state: bool) -> None:
        """Set the night light state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        if self.check_power():
            packet[4] = 3 if state else 1
        else:
            packet[4] = 2 if state else 0
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] == 1 or payload[0x4] == 3 or payload[0x4] == 0xFD)

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] == 2 or payload[0x4] == 3 or payload[0x4] == 0xFF)


class sp3s(sp2):
    """Controls a Broadlink SP3S."""

    TYPE = "SP3S"

    def get_energy(self) -> float:
        """Return the power consumption in W."""
        packet = bytearray([8, 0, 254, 1, 5, 1, 0, 0, 0, 45])
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        energy = payload[0x7:0x4:-1].hex()
        return int(energy) / 100


class sp4(device):
    """Controls a Broadlink SP4."""

    TYPE = "SP4"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        self.set_state(pwr=state)

    def set_nightlight(self, state: bool) -> None:
        """Set the night light state of the device."""
        self.set_state(ntlight=state)

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
        data = {}
        if pwr is not None:
            data["pwr"] = int(bool(pwr))
        if ntlight is not None:
            data["ntlight"] = int(bool(ntlight))
        if indicator is not None:
            data["indicator"] = int(bool(indicator))
        if ntlbrightness is not None:
            data["ntlbrightness"] = ntlbrightness
        if maxworktime is not None:
            data["maxworktime"] = maxworktime
        if childlock is not None:
            data["childlock"] = int(bool(childlock))

        packet = self._encode(2, data)
        response = self.send_packet(0x6A, packet)
        return self._decode(response)

    def check_power(self) -> bool:
        """Return the power state of the device."""
        state = self.get_state()
        return state["pwr"]

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        state = self.get_state()
        return state["ntlight"]

    def get_state(self) -> dict:
        """Get full state of device."""
        packet = self._encode(1, {})
        response = self.send_packet(0x6A, packet)
        return self._decode(response)

    def _encode(self, flag: int, state: dict) -> bytes:
        """Encode a message."""
        payload = json.dumps(state, separators=(",", ":")).encode()
        packet = bytearray(12)
        struct.pack_into(
            "<HHHBBI", packet, 0, 0xA5A5, 0x5A5A, 0x0000, flag, 0x0B, len(payload)
        )
        packet.extend(payload)
        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x04] = checksum & 0xFF
        packet[0x05] = checksum >> 8
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        check_error(response[0x22:0x24])
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
        payload = json.dumps(state, separators=(",", ":")).encode()
        packet = bytearray(14)
        length = 4 + 2 + 2 + 4 + len(payload)
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
            len(payload),
        )
        packet.extend(payload)
        checksum = sum(packet[0x8:], 0xC0AD) & 0xFFFF
        packet[0x06] = checksum & 0xFF
        packet[0x07] = checksum >> 8
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from("<I", payload, 0xA)[0]
        state = json.loads(payload[0x0E : 0x0E + js_len])
        return state
