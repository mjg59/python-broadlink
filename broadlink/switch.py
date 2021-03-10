"""Support for switches."""
from .device import BroadlinkDevice, v1_core, v2_core, v3_core, v4_core, v5_core


@v4_core
class mp1(BroadlinkDevice):
    """Controls a Broadlink MP1."""

    _TYPE = "MP1"

    def set_power_mask(self, sid_mask: int, state: bool) -> None:
        """Set the power state of the device."""
        state = bytes([sid_mask, sid_mask if state else 0])
        self.send_json_cmd(0x02, state, eoh=0)

    def set_power(self, sid: int, state: bool) -> None:
        """Set the power state of the device."""
        sid_mask = 1 << (sid - 1)
        self.set_power_mask(sid_mask, state)

    def check_power_raw(self) -> int:
        """Return the power state of the device in raw format."""
        return self.send_json_cmd(0x01, b"", eoh=0)

    def check_power(self) -> dict:
        """Return the power state of the device."""
        resp = self.check_power_raw()
        return {
            "s1": bool(resp & 1),
            "s2": bool(resp & 2),
            "s3": bool(resp & 4),
            "s4": bool(resp & 8),
        }


@v4_core
class bg1(BroadlinkDevice):
    """Controls a BG Electrical smart outlet."""

    _TYPE = "BG1"

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{"pwr":1,"pwr1":1,"pwr2":0,"maxworktime":60,"maxworktime1":60,"maxworktime2":0,"idcbrightness":50}`
        """
        return self.send_json_cmd(0x01, {})

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

        return self.send_json_cmd(0x02, state)


@v1_core
class sp1(BroadlinkDevice):
    """Controls a Broadlink SP1."""

    _TYPE = "SP1"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        data = int(bool(state)).to_bytes(4, "little")
        self.send_packet(0x66, data)


@v2_core
class sp2(BroadlinkDevice):
    """Controls a Broadlink SP2."""

    _TYPE = "SP2"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        state = int(bool(state))
        self.send_cmd(0x02, [state])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        resp = self.send_cmd(0x01)
        return bool(resp[0] & 1)


class sp2s(sp2):
    """Controls a Broadlink SP2S."""

    _TYPE = "SP2S"

    def get_energy(self) -> float:
        """Return the power consumption in W."""
        resp = self.send_cmd(0x04)
        return int.from_bytes(resp[:0x03], "little") / 1000


@v3_core
class sp3(sp2):
    """Controls a Broadlink SP3."""

    _TYPE = "SP3"

    def set_power(self, state: bool) -> None:
        """Set the power state of the device."""
        state = self.check_nightlight() << 1 | bool(state)
        self.send_cmd(0x02, [state])

    def set_nightlight(self, state: bool) -> None:
        """Set the night light state of the device."""
        state = bool(state) << 1 | self.check_power()
        self.send_cmd(0x02, [state])

    def check_power(self) -> bool:
        """Return the power state of the device."""
        resp = self.send_cmd(0x01)
        return bool(resp[0] & 1)

    def check_nightlight(self) -> bool:
        """Return the state of the night light."""
        resp = self.send_cmd(0x01)
        return bool(resp[0] & 2)


@v3_core
class sp3s(sp2):
    """Controls a Broadlink SP3S."""

    _TYPE = "SP3S"

    def get_energy(self) -> float:
        """Return the power consumption in W."""
        resp = self.send_cmd(0x01FE0008, [5, 1, 0, 0, 0, 45])
        energy = resp[0x3:0x0:-1].hex()
        return int(energy) / 100


@v5_core
class sp4(BroadlinkDevice):
    """Controls a Broadlink SP4."""

    _TYPE = "SP4"

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

        return self.send_json_cmd(0x02, state)

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
        return self.send_json_cmd(0x01, {})


@v4_core
class sp4b(sp4):
    """Controls a Broadlink SP4 (type B)."""

    _TYPE = "SP4B"

    def get_state(self) -> dict:
        """Get full state of device."""
        state = super().get_state()

        # Convert sensor data to float. Remove keys if sensors are not supported.
        sensors = ["current", "volt", "power", "totalconsum", "overload"]
        for sensor in sensors:
            value = state.pop(sensor, -1)
            if value != -1:
                state[sensor] = value / 1000
        return state
