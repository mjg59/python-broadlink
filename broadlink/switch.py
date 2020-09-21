import json
import struct

from .device import device
from .exceptions import check_error


class mp1(device):
    """Controls a Broadlink MP1."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "MP1"

    def set_power_mask(self, sid_mask: int, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0x00] = 0x0d
        packet[0x02] = 0xa5
        packet[0x03] = 0xa5
        packet[0x04] = 0x5a
        packet[0x05] = 0x5a
        packet[0x06] = 0xb2 + ((sid_mask << 1) if state else sid_mask)
        packet[0x07] = 0xc0
        packet[0x08] = 0x02
        packet[0x0a] = 0x03
        packet[0x0d] = sid_mask
        packet[0x0e] = sid_mask if state else 0

        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])

    def set_power(self, sid: int, state: bool) -> None:
        """Set the power state of the device."""
        sid_mask = 0x01 << (sid - 1)
        self.set_power_mask(sid_mask, state)

    def check_power_raw(self) -> bool:
        """Return the power state of the device in raw format."""
        packet = bytearray(16)
        packet[0x00] = 0x0a
        packet[0x02] = 0xa5
        packet[0x03] = 0xa5
        packet[0x04] = 0x5a
        packet[0x05] = 0x5a
        packet[0x06] = 0xae
        packet[0x07] = 0xc0
        packet[0x08] = 0x01

        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x0e]

    def check_power(self) -> dict:
        """Return the power state of the device."""
        state = self.check_power_raw()
        if state is None:
            return {'s1': None, 's2': None, 's3': None, 's4': None}
        data = {}
        data['s1'] = bool(state & 0x01)
        data['s2'] = bool(state & 0x02)
        data['s3'] = bool(state & 0x04)
        data['s4'] = bool(state & 0x08)
        return data


class bg1(device):
    """Controls a BG Electrical smart outlet."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "BG1"

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{"pwr":1,"pwr1":1,"pwr2":0,"maxworktime":60,"maxworktime1":60,"maxworktime2":0,"idcbrightness":50}`
        """
        packet = self._encode(1, b'{}')
        response = self.send_packet(0x6a, packet)
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
            data['pwr'] = int(bool(pwr))
        if pwr1 is not None:
            data['pwr1'] = int(bool(pwr1))
        if pwr2 is not None:
            data['pwr2'] = int(bool(pwr2))
        if maxworktime is not None:
            data['maxworktime'] = maxworktime
        if maxworktime1 is not None:
            data['maxworktime1'] = maxworktime1
        if maxworktime2 is not None:
            data['maxworktime2'] = maxworktime2
        if idcbrightness is not None:
            data['idcbrightness'] = idcbrightness
        js = json.dumps(data).encode('utf8')
        packet = self._encode(2, js)
        response = self.send_packet(0x6a, packet)
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
        struct.pack_into('<HHHHBBI', packet, 0, length, 0xa5a5, 0x5a5a, 0x0000, flag, 0x0b, len(js))
        for i in range(len(js)):
            packet.append(js[i])

        checksum = sum(packet[0x08:], 0xc0ad) & 0xffff
        packet[0x06] = checksum & 0xff
        packet[0x07] = checksum >> 8
        return packet

    def _decode(self, response: bytes) -> dict:
        """Decode a message."""
        payload = self.decrypt(response[0x38:])
        js_len = struct.unpack_from('<I', payload, 0x0a)[0]
        state = json.loads(payload[0x0e:0x0e+js_len])
        return state


class sp1(device):
    """Controls a Broadlink SP1."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the device."""
        device.__init__(self, *args, **kwargs)
        self.type = "SP1"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(4)
        packet[0] = state
        response = self.send_packet(0x66, packet)
        check_error(response[0x22:0x24])


class sp2(device):
    """Controls a Broadlink SP2."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "SP2"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        if self.check_nightlight():
            packet[4] = 3 if state else 2
        else:
            packet[4] = 1 if state else 0
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])

    def set_nightlight(self, state: bool) -> None:
        """Set the night light state of the device."""
        packet = bytearray(16)
        packet[0] = 2
        if self.check_power():
            packet[4] = 3 if state else 1
        else:
            packet[4] = 2 if state else 0
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] == 1 or payload[0x4] == 3 or payload[0x4] == 0xFD)

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        packet = bytearray(16)
        packet[0] = 1
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return bool(payload[0x4] == 2 or payload[0x4] == 3 or payload[0x4] == 0xFF)

    def get_energy(self) -> int:
        """Return the energy state of the device."""
        packet = bytearray([8, 0, 254, 1, 5, 1, 0, 0, 0, 45])
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return int(hex(payload[0x07] * 256 + payload[0x06])[2:]) + int(hex(payload[0x05])[2:]) / 100.0
