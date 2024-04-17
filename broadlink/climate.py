"""Support for climate control."""
import enum
import logging
import struct
from typing import List, Sequence

from . import exceptions as e
from .device import Device
from .helpers import CRC16


class hysen(Device):
    """Controls a Hysen heating thermostat.

    This device is manufactured by Hysen and sold under different
    brands, including Floureon, Beca Energy, Beok and Decdeal.

    Supported models:
    - HY02B05H
    - HY03WE
    """

    TYPE = "HYS"

    def send_request(self, request: Sequence[int]) -> bytes:
        """Send a request to the device."""
        packet = bytearray()
        packet.extend((len(request) + 2).to_bytes(2, "little"))
        packet.extend(request)
        packet.extend(CRC16.calculate(request).to_bytes(2, "little"))

        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])

        p_len = int.from_bytes(payload[:0x02], "little")
        if p_len + 2 > len(payload):
            raise ValueError(
                "hysen_response_error", "first byte of response is not length"
            )

        nom_crc = int.from_bytes(payload[p_len : p_len + 2], "little")
        real_crc = CRC16.calculate(payload[0x02:p_len])
        if nom_crc != real_crc:
            raise ValueError("hysen_response_error", "CRC check on response failed")

        return payload[0x02:p_len]

    def _decode_temp(self, payload, base_index):
        base_temp = payload[base_index] / 2.0
        add_offset = (payload[4] >> 3) & 1  # should offset be added?
        offset_raw_value = (payload[17] >> 4) & 3  # offset value
        offset = (offset_raw_value + 1) / 10 if add_offset else 0.0
        return base_temp + offset

    def get_temp(self) -> float:
        """Return the room temperature in degrees celsius."""
        payload = self.send_request([0x01, 0x03, 0x00, 0x00, 0x00, 0x08])
        return self._decode_temp(payload, 5)

    def get_external_temp(self) -> float:
        """Return the external temperature in degrees celsius."""
        payload = self.send_request([0x01, 0x03, 0x00, 0x00, 0x00, 0x08])
        return self._decode_temp(payload, 18)

    def get_full_status(self) -> dict:
        """Return the state of the device.

        Timer schedule included.
        """
        payload = self.send_request([0x01, 0x03, 0x00, 0x00, 0x00, 0x16])
        data = {}
        data["remote_lock"] = payload[3] & 1
        data["power"] = payload[4] & 1
        data["active"] = (payload[4] >> 4) & 1
        data["temp_manual"] = (payload[4] >> 6) & 1
        data["heating_cooling"] = (payload[4] >> 7) & 1
        data["room_temp"] = self._decode_temp(payload, 5)
        data["thermostat_temp"] = payload[6] / 2.0
        data["auto_mode"] = payload[7] & 0xF
        data["loop_mode"] = payload[7] >> 4
        data["sensor"] = payload[8]
        data["osv"] = payload[9]
        data["dif"] = payload[10]
        data["svh"] = payload[11]
        data["svl"] = payload[12]
        data["room_temp_adj"] = (
            int.from_bytes(payload[13:15], "big", signed=True) / 10.0
        )
        data["fre"] = payload[15]
        data["poweron"] = payload[16]
        data["unknown"] = payload[17]
        data["external_temp"] = self._decode_temp(payload, 18)
        data["hour"] = payload[19]
        data["min"] = payload[20]
        data["sec"] = payload[21]
        data["dayofweek"] = payload[22]

        weekday = []
        for i in range(0, 6):
            weekday.append(
                {
                    "start_hour": payload[2 * i + 23],
                    "start_minute": payload[2 * i + 24],
                    "temp": payload[i + 39] / 2.0,
                }
            )

        data["weekday"] = weekday
        weekend = []
        for i in range(6, 8):
            weekend.append(
                {
                    "start_hour": payload[2 * i + 23],
                    "start_minute": payload[2 * i + 24],
                    "temp": payload[i + 39] / 2.0,
                }
            )

        data["weekend"] = weekend
        return data

    # Change controller mode
    # auto_mode = 1 for auto (scheduled/timed) mode, 0 for manual mode.
    # Manual mode will activate last used temperature.
    # In typical usage call set_temp to activate manual control and set temp.
    # loop_mode refers to index in [ "12345,67", "123456,7", "1234567" ]
    # E.g. loop_mode = 0 ("12345,67") means Saturday and Sunday (weekend schedule)
    # loop_mode = 2 ("1234567") means every day, including Saturday and Sunday (weekday schedule)
    # The sensor command is currently experimental
    def set_mode(self, auto_mode: int, loop_mode: int, sensor: int = 0) -> None:
        """Set the mode of the device."""
        mode_byte = ((loop_mode + 1) << 4) + auto_mode
        self.send_request([0x01, 0x06, 0x00, 0x02, mode_byte, sensor])

    # Advanced settings
    # Sensor mode (SEN) sensor = 0 for internal sensor, 1 for external sensor,
    # 2 for internal control temperature, external limit temperature. Factory default: 0.
    # Set temperature range for external sensor (OSV) osv = 5..99. Factory default: 42C
    # Deadzone for floor temprature (dIF) dif = 1..9. Factory default: 2C
    # Upper temperature limit for internal sensor (SVH) svh = 5..99. Factory default: 35C
    # Lower temperature limit for internal sensor (SVL) svl = 5..99. Factory default: 5C
    # Actual temperature calibration (AdJ) adj = -0.5. Precision 0.1C
    # Anti-freezing function (FrE) fre = 0 for anti-freezing function shut down,
    #  1 for anti-freezing function open. Factory default: 0
    # Power on memory (POn) poweron = 0 for off, 1 for on. Default: 0
    def set_advanced(
        self,
        loop_mode: int,
        sensor: int,
        osv: int,
        dif: int,
        svh: int,
        svl: int,
        adj: float,
        fre: int,
        poweron: int,
    ) -> None:
        """Set advanced options."""
        self.send_request(
            [
                0x01,
                0x10,
                0x00,
                0x02,
                0x00,
                0x05,
                0x0A,
                loop_mode,
                sensor,
                osv,
                dif,
                svh,
                svl,
                int(adj * 10) >> 8 & 0xFF,
                int(adj * 10) & 0xFF,
                fre,
                poweron,
            ]
        )

    # For backwards compatibility only.  Prefer calling set_mode directly.
    # Note this function invokes loop_mode=0 and sensor=0.
    def switch_to_auto(self) -> None:
        """Switch mode to auto."""
        self.set_mode(auto_mode=1, loop_mode=0)

    def switch_to_manual(self) -> None:
        """Switch mode to manual."""
        self.set_mode(auto_mode=0, loop_mode=0)

    # Set temperature for manual mode (also activates manual mode if currently in automatic)
    def set_temp(self, temp: float) -> None:
        """Set the target temperature."""
        self.send_request([0x01, 0x06, 0x00, 0x01, 0x00, int(temp * 2)])

    # Set device on(1) or off(0), does not deactivate Wifi connectivity.
    # Remote lock disables control by buttons on thermostat.
    # heating_cooling: heating(0) cooling(1)
    def set_power(
        self, power: int = 1, remote_lock: int = 0, heating_cooling: int = 0
    ) -> None:
        """Set the power state of the device."""
        state = (heating_cooling << 7) + power
        self.send_request([0x01, 0x06, 0x00, 0x00, remote_lock, state])

    # set time on device
    # n.b. day=1 is Monday, ..., day=7 is Sunday
    def set_time(self, hour: int, minute: int, second: int, day: int) -> None:
        """Set the time."""
        self.send_request(
            [0x01, 0x10, 0x00, 0x08, 0x00, 0x02, 0x04, hour, minute, second, day]
        )

    # Set timer schedule
    # Format is the same as you get from get_full_status.
    # weekday is a list (ordered) of 6 dicts like:
    # {'start_hour':17, 'start_minute':30, 'temp': 22 }
    # Each one specifies the thermostat temp that will become effective at start_hour:start_minute
    # weekend is similar but only has 2 (e.g. switch on in morning and off in afternoon)
    def set_schedule(self, weekday: List[dict], weekend: List[dict]) -> None:
        """Set timer schedule."""
        request = [0x01, 0x10, 0x00, 0x0A, 0x00, 0x0C, 0x18]

        # weekday times
        for i in range(0, 6):
            request.append(weekday[i]["start_hour"])
            request.append(weekday[i]["start_minute"])

        # weekend times
        for i in range(0, 2):
            request.append(weekend[i]["start_hour"])
            request.append(weekend[i]["start_minute"])

        # weekday temperatures
        for i in range(0, 6):
            request.append(int(weekday[i]["temp"] * 2))

        # weekend temperatures
        for i in range(0, 2):
            request.append(int(weekend[i]["temp"] * 2))

        self.send_request(request)


class hvac(Device):
    """Controls a HVAC.

    Supported models:
    - Tornado SMART X SQ series.
    """

    TYPE = "HVAC"

    @enum.unique
    class Mode(enum.IntEnum):
        """Enumerates modes."""
        AUTO = 0
        COOL = 1
        DRY = 2
        HEAT = 3
        FAN = 4

    @enum.unique
    class Speed(enum.IntEnum):
        """Enumerates fan speed."""
        HIGH = 1
        MID = 2
        LOW = 3
        AUTO = 5

    @enum.unique
    class Preset(enum.IntEnum):
        """Enumerates presets."""
        NORMAL = 0
        TURBO = 1
        MUTE = 2

    @enum.unique
    class SwHoriz(enum.IntEnum):
        """Enumerates horizontal swing."""
        ON = 0
        OFF = 7

    @enum.unique
    class SwVert(enum.IntEnum):
        """Enumerates vertical swing."""
        ON = 0
        POS1 = 1
        POS2 = 2
        POS3 = 3
        POS4 = 4
        POS5 = 5
        OFF = 7

    def _crc(self, data: bytes) -> int:
        """Calculate CRC of a byte object."""
        s = sum([v if i % 2 == 0 else v << 8 for i, v in enumerate(data)])
        # trim the overflow and add it to smallest bit
        s = (s & 0xFFFF) + (s >> 16)
        return (0xFFFF - s) & 0xFFFF

    def _encode(self, data: bytes) -> bytes:
        """Encode data for transport."""
        packet = bytearray(10)
        p_len = 8 + len(data)
        struct.pack_into(
            "<HHHHH", packet, 0, p_len, 0x00BB, 0x8006, 0, len(data)
        )
        packet += data
        packet += self._crc(packet[2:]).to_bytes(2, "little")
        return packet

    def _decode(self, response: bytes) -> bytes:
        """Decode data from transport."""
        # payload[0x2:0x8] == bytes([0xbb, 0x00, 0x07, 0x00, 0x00, 0x00])
        payload = self.decrypt(response[0x38:])
        p_len = int.from_bytes(payload[:0x2], "little")
        checksum = int.from_bytes(payload[p_len:p_len+2], "little")

        if checksum != self._crc(payload[0x2:p_len]):
            logging.debug(
                "Checksum incorrect (calculated %s actual %s).",
                checksum.hex(), payload[p_len:p_len+2].hex()
            )

        d_len = int.from_bytes(payload[0x8:0xA], "little")
        return payload[0xA:0xA+d_len]

    def _send(self, command: int, data: bytes = b'') -> bytes:
        """Send a command to the unit."""
        command = bytes([((command << 4) | 1), 1])
        packet = self._encode(command + data)
        logging.debug("Payload:\n%s", packet.hex(' '))
        response = self.send_packet(0x6a, packet)
        e.check_error(response[0x22:0x24])
        return self._decode(response)[0x2:]

    def get_state(self) -> dict:
        """Returns a dictionary with the unit's parameters.

        Returns:
            dict:
                power (bool):
                target_temp (float): temperature set point 16<n<32
                mode (hvac.Mode):
                speed (hvac.Speed):
                preset (hvac.Preset):
                swing_h (hvac.SwHoriz):
                swing_v (hvac.SwVert):
                sleep (bool):
                display (bool):
                health (bool):
                clean (bool):
                mildew (bool):
        """
        resp = self._send(0x1)

        if (len(resp) != 0xF):
            raise ValueError(f"unexpected resp size: {len(resp)}")

        logging.debug("Received resp:\n%s", resp.hex(' '))
        logging.debug("0b[R] mask: %x, 0c[R] mask: %x, cmnd_16: %x",
                      resp[0x3] & 0xF, resp[0x4] & 0xF, resp[0x4])

        state = {}
        state['power'] = resp[0x8] & 1 << 5
        state['target_temp'] = 8 + (resp[0x0] >> 3) + (resp[0x4] >> 7) * 0.5
        state['swing_v'] = self.SwVert(resp[0x0] & 0b111)
        state['swing_h'] = self.SwHoriz(resp[0x1] >> 5)
        state['mode'] = self.Mode(resp[0x5] >> 5)
        state['speed'] = self.Speed(resp[0x3] >> 5)
        state['preset'] = self.Preset(resp[0x4] >> 6)
        state['sleep'] = bool(resp[0x5] & 1 << 2)
        state['health'] = bool(resp[0x8] & 1 << 1)
        state['clean'] = bool(resp[0x8] & 1 << 2)
        state['display'] = bool(resp[0xA] & 1 << 4)
        state['mildew'] = bool(resp[0xA] & 1 << 3)

        logging.debug("State: %s", state)

        return state

    def get_ac_info(self) -> dict:
        """Returns dictionary with AC info.

        Returns:
            dict:
                power (bool): power
                ambient_temp (float): ambient temperature
        """
        resp = self._send(2)
        if (len(resp) != 0x18):
            raise ValueError(f"unexpected resp size: {len(resp)}")

        logging.debug("Received resp:\n%s", resp.hex(' '))

        ac_info = {}
        ac_info["power"] = resp[0x1] & 1

        ambient_temp = resp[0x5] & 0b11111, resp[0x15] & 0b11111
        if any(ambient_temp):
            ac_info["ambient_temp"] = ambient_temp[0] + ambient_temp[1] / 10.0

        logging.debug("AC info: %s", ac_info)
        return ac_info

    def set_state(
        self,
        power: bool,
        target_temp: float,  # 16<=target_temp<=32
        mode: int,  # hvac.Mode
        speed: int,  # hvac.Speed
        preset: int,  # hvac.Preset
        swing_h: int,  # hvac.SwHoriz
        swing_v: int,  # hvac.SwVert
        sleep: bool,
        display: bool,
        health: bool,
        clean: bool,
        mildew: bool,
    ) -> None:
        """Set the state of the device."""
        # TODO: What does these values represent?
        UNK0 = 0b100
        UNK1 = 0b1101
        UNK2 = 0b101

        target_temp = round(target_temp * 2) / 2
        if not (16 <= target_temp <= 32):
            raise ValueError(f"target_temp out of range: {target_temp}")

        if preset == self.Preset.MUTE:
            if mode != self.Mode.FAN:
                raise ValueError("mute is only available in fan mode")
            speed = self.Speed.LOW

        elif preset == self.Preset.TURBO:
            if mode not in {self.Mode.COOL, self.Mode.HEAT}:
                raise ValueError("turbo is only available in cooling/heating")
            speed = self.Speed.HIGH

        data = bytearray(0xD)
        data[0x0] = (int(target_temp) - 8 << 3) | swing_v
        data[0x1] = (swing_h << 5) | UNK0
        data[0x2] = ((target_temp % 1 == 0.5) << 7) | UNK1
        data[0x3] = speed << 5
        data[0x4] = preset << 6
        data[0x5] = mode << 5 | (sleep << 2)
        data[0x8] = (power << 5 | clean << 2 | health * 0b11)
        data[0xA] = display << 4 | mildew << 3
        data[0xC] = UNK2

        logging.debug("Constructed payload data:\n%s", data.hex(' '))

        response_payload = self._send(0, data)
        logging.debug("Response payload:\n%s", response_payload.hex(' '))
