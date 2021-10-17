"""Support for HVAC units."""
import typing as t

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

    def send_request(self, request: t.Sequence[int]) -> bytes:
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

    def get_temp(self) -> float:
        """Return the room temperature in degrees celsius."""
        payload = self.send_request([0x01, 0x03, 0x00, 0x00, 0x00, 0x08])
        return payload[0x05] / 2.0

    def get_external_temp(self) -> float:
        """Return the external temperature in degrees celsius."""
        payload = self.send_request([0x01, 0x03, 0x00, 0x00, 0x00, 0x08])
        return payload[18] / 2.0

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
        data["room_temp"] = payload[5] / 2.0
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
        data["external_temp"] = payload[18] / 2.0
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
    def set_power(self, power: int = 1, remote_lock: int = 0) -> None:
        """Set the power state of the device."""
        self.send_request([0x01, 0x06, 0x00, 0x00, remote_lock, power])

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
    def set_schedule(self, weekday: t.List[dict], weekend: t.List[dict]) -> None:
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
