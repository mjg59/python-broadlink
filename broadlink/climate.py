"""Support for climate control."""
from typing import List

from .device import device
from .exceptions import check_error
from .helpers import calculate_crc16


class hysen(device):
    """Controls a Hysen HVAC."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = "Hysen heating controller"

    # Send a request
    # input_payload should be a bytearray, usually 6 bytes, e.g. bytearray([0x01,0x06,0x00,0x02,0x10,0x00])
    # Returns decrypted payload
    # New behaviour: raises a ValueError if the device response indicates an error or CRC check fails
    # The function prepends length (2 bytes) and appends CRC

    def send_request(self, input_payload: bytes) -> bytes:
        """Send a request to the device."""
        crc = calculate_crc16(input_payload)

        # first byte is length, +2 for CRC16
        request_payload = bytearray([len(input_payload) + 2, 0x00])
        request_payload.extend(input_payload)

        # append CRC
        request_payload.append(crc & 0xFF)
        request_payload.append((crc >> 8) & 0xFF)

        # send to device
        response = self.send_packet(0x6A, request_payload)
        check_error(response[0x22:0x24])
        response_payload = self.decrypt(response[0x38:])

        # experimental check on CRC in response (first 2 bytes are len, and trailing bytes are crc)
        response_payload_len = response_payload[0]
        if response_payload_len + 2 > len(response_payload):
            raise ValueError(
                "hysen_response_error", "first byte of response is not length"
            )
        crc = calculate_crc16(response_payload[2:response_payload_len])
        if (response_payload[response_payload_len] == crc & 0xFF) and (
            response_payload[response_payload_len + 1] == (crc >> 8) & 0xFF
        ):
            return response_payload[2:response_payload_len]
        raise ValueError("hysen_response_error", "CRC check on response failed")

    def get_temp(self) -> int:
        """Return the room temperature in degrees celsius."""
        payload = self.send_request(bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x08]))
        return payload[0x05] / 2.0

    def get_external_temp(self) -> int:
        """Return the external temperature in degrees celsius."""
        payload = self.send_request(bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x08]))
        return payload[18] / 2.0

    def get_full_status(self) -> dict:
        """Return the state of the device.

        Timer schedule included.
        """
        payload = self.send_request(bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x16]))
        data = {}
        data["remote_lock"] = payload[3] & 1
        data["power"] = payload[4] & 1
        data["active"] = (payload[4] >> 4) & 1
        data["temp_manual"] = (payload[4] >> 6) & 1
        data["room_temp"] = (payload[5] & 255) / 2.0
        data["thermostat_temp"] = (payload[6] & 255) / 2.0
        data["auto_mode"] = payload[7] & 15
        data["loop_mode"] = (payload[7] >> 4) & 15
        data["sensor"] = payload[8]
        data["osv"] = payload[9]
        data["dif"] = payload[10]
        data["svh"] = payload[11]
        data["svl"] = payload[12]
        data["room_temp_adj"] = ((payload[13] << 8) + payload[14]) / 2.0
        if data["room_temp_adj"] > 32767:
            data["room_temp_adj"] = 32767 - data["room_temp_adj"]
        data["fre"] = payload[15]
        data["poweron"] = payload[16]
        data["unknown"] = payload[17]
        data["external_temp"] = (payload[18] & 255) / 2.0
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
    # E.g. loop_mode = 0 ("12345,67") means Saturday and Sunday follow the "weekend" schedule
    # loop_mode = 2 ("1234567") means every day (including Saturday and Sunday) follows the "weekday" schedule
    # The sensor command is currently experimental
    def set_mode(self, auto_mode: int, loop_mode: int, sensor: int = 0) -> None:
        """Set the mode of the device."""
        mode_byte = ((loop_mode + 1) << 4) + auto_mode
        self.send_request(bytearray([0x01, 0x06, 0x00, 0x02, mode_byte, sensor]))

    # Advanced settings
    # Sensor mode (SEN) sensor = 0 for internal sensor, 1 for external sensor,
    # 2 for internal control temperature, external limit temperature. Factory default: 0.
    # Set temperature range for external sensor (OSV) osv = 5..99. Factory default: 42C
    # Deadzone for floor temprature (dIF) dif = 1..9. Factory default: 2C
    # Upper temperature limit for internal sensor (SVH) svh = 5..99. Factory default: 35C
    # Lower temperature limit for internal sensor (SVL) svl = 5..99. Factory default: 5C
    # Actual temperature calibration (AdJ) adj = -0.5. Prescision 0.1C
    # Anti-freezing function (FrE) fre = 0 for anti-freezing function shut down,
    #  1 for anti-freezing function open. Factory default: 0
    # Power on memory (POn) poweron = 0 for power on memory off, 1 for power on memory on. Factory default: 0
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
        input_payload = bytearray(
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
                (int(adj * 2) >> 8 & 0xFF),
                (int(adj * 2) & 0xFF),
                fre,
                poweron,
            ]
        )
        self.send_request(input_payload)

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
        self.send_request(bytearray([0x01, 0x06, 0x00, 0x01, 0x00, int(temp * 2)]))

    # Set device on(1) or off(0), does not deactivate Wifi connectivity.
    # Remote lock disables control by buttons on thermostat.
    def set_power(self, power: int = 1, remote_lock: int = 0) -> None:
        """Set the power state of the device."""
        self.send_request(bytearray([0x01, 0x06, 0x00, 0x00, remote_lock, power]))

    # set time on device
    # n.b. day=1 is Monday, ..., day=7 is Sunday
    def set_time(self, hour: int, minute: int, second: int, day: int) -> None:
        """Set the time."""
        self.send_request(
            bytearray(
                [0x01, 0x10, 0x00, 0x08, 0x00, 0x02, 0x04, hour, minute, second, day]
            )
        )

    # Set timer schedule
    # Format is the same as you get from get_full_status.
    # weekday is a list (ordered) of 6 dicts like:
    # {'start_hour':17, 'start_minute':30, 'temp': 22 }
    # Each one specifies the thermostat temp that will become effective at start_hour:start_minute
    # weekend is similar but only has 2 (e.g. switch on in morning and off in afternoon)
    def set_schedule(self, weekday: List[dict], weekend: List[dict]) -> None:
        """Set timer schedule."""
        # Begin with some magic values ...
        input_payload = bytearray([0x01, 0x10, 0x00, 0x0A, 0x00, 0x0C, 0x18])

        # Now simply append times/temps
        # weekday times
        for i in range(0, 6):
            input_payload.append(weekday[i]["start_hour"])
            input_payload.append(weekday[i]["start_minute"])

        # weekend times
        for i in range(0, 2):
            input_payload.append(weekend[i]["start_hour"])
            input_payload.append(weekend[i]["start_minute"])

        # weekday temperatures
        for i in range(0, 6):
            input_payload.append(int(weekday[i]["temp"] * 2))

        # weekend temperatures
        for i in range(0, 2):
            input_payload.append(int(weekend[i]["temp"] * 2))

        self.send_request(input_payload)


class sq1(device):
    """Controls Tornado SMART X SQ series air conditioners."""
    def __init__(self, *args, **kwargs):
        device.__init__(self, *args, **kwargs)
        self.type = "Tornado SQ air conditioner"

    def _decode(self, response) -> bytes:
        payload = self.decrypt(bytes(response[0x38:]))
        return payload

    def _calculate_checksum(self, payload: bytes, byteorder: str) -> bytes:
        """Calculate checksum of given array,
        by adding little endian words and subtracting from 0xffff.

        The first two bytes of most packets in the class are the length of the
        payload and should be cropped out when using this function.

        Args:
            payload (bytes): the payload
            byteorder (str): byte order to return the results in
        """
        s = sum([v if i % 2 == 0 else v << 8 for i, v in enumerate(payload)])
        # trim the overflow and add it smallest bit
        s = (s & 0xffff) + (s >> 16)
        result = (0xffff - s)
        return result.to_bytes(2, byteorder)

    def _send_short_payload(self, payload: int) -> bytes:
        """Send a request for info from A/C unit and returns the response.
        0 = GET_AC_INFO, 1 = GET_STATES, 2 = GET_SLEEP_INFO, 3 = unknown function
        """
        header = bytearray([0x0c, 0x00, 0xbb, 0x00, 0x06, 0x80, 0x00, 0x00, 0x02, 0x00])
        if (payload == 0):
            packet = header + bytes([0x21, 0x01, 0x1b, 0x7e])
        elif (payload == 1):
            packet = header + bytes([0x11, 0x01, 0x2b, 0x7e])
        elif (payload == 2):
            packet = header + bytes([0x41, 0x01, 0xfb, 0x7d])
        elif (payload == 3):
            packet = bytearray(16)
            packet[0x00] = 0xd0
            packet[0x01] = 0x07
        else:
            raise ValueError(f'unrecognized payload type: {payload}')

        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        return (self._decode(response))

    def get_state(
        self,
        payload_debug: bool = False,
        unidentified_commands_debug: bool = False
    ) -> dict:
        """Returns a dictionary with the unit's parameters.

        Args:
            payload_debug (Optional[bool]): prints the received payload
            unidentified_commands_debug (Optional[bool]): add cmnd_0d_rmask, cmnd_0e_rmask and cmnd_18 for debugging

        Returns:
            dict:
                state (bool): power
                target_temp (float): temperature set point 16<n<32
                mode (str): cooling, heating, fan, dry, auto
                speed (str): mute, low, mid, high, turbo (available only in cooling)
                swing_h (str): ON, OFF
                swing_v (str): ON, OFF, 1, 2, 3, 4, 5 (fixed positions)
                sleep (bool):
                display (bool):
                health (bool):
                clean (bool):
                mildew (bool)
        """
        payload = self._send_short_payload(1)
        if (len(payload) != 32):
            raise ValueError(f'unexpected payload size: {len(payload)}')

        data = {}
        data['state'] = payload[0x14] & 0x20 == 0x20
        data['target_temp'] = (8 + (payload[0x0c] >> 3)
                               + (0.0 if (payload[0xe] & 0b10000000) == 0 else 0.5))

        swing_v = payload[0x0c] & 0b111
        swing_h = (payload[0x0d] & 0b11100000) >> 5
        if swing_h == 0b111:
            data['swing_h'] = 'OFF'
        elif swing_h == 0b000:
            data['swing_h'] = 'ON'
        else:
            data['swing_h'] = 'unrecognized value'

        if swing_v == 0b111:
            data['swing_v'] = 'OFF'
        elif swing_v == 0b000:
            data['swing_v'] = 'ON'
        elif (swing_v >= 0 and swing_v <= 5):
            data['swing_v'] = str(swing_v)
        else:
            data['swing_v'] = 'unrecognized value'

        mode = payload[0x11] >> 3 << 3
        if mode == 0x00:
            data['mode'] = 'auto'
        elif mode == 0x20:
            data['mode'] = 'cooling'
        elif mode == 0x40:
            data['mode'] = 'drying'
        elif mode == 0x80:
            data['mode'] = 'heating'
        elif mode == 0xc0:
            data['mode'] = 'fan'
        else:
            data['mode'] = 'unrecognized value'

        speed_L = payload[0x0f]
        speed_R = payload[0x10]
        if speed_L == 0x60 and speed_R == 0x00:
            data['speed'] = 'low'
        elif speed_L == 0x40 and speed_R == 0x00:
            data['speed'] = 'mid'
        elif speed_L == 0x20 and speed_R == 0x00:
            data['speed'] = 'high'
        elif speed_L == 0x40 and speed_R == 0x80:
            data['speed'] = 'mute'
        elif speed_R == 0x40:
            data['speed'] = 'turbo'
        elif speed_L == 0xa0 and speed_R == 0x00:
            data['speed'] = 'auto'
        else:
            data['speed'] = 'unrecognized value'

        data['sleep'] = bool(payload[0x11] & 0b100)

        data['health'] = bool(payload[0x14] & 0b10)
        data['clean'] = bool(payload[0x14] & 0b100)

        data['display'] = bool(payload[0x16] & 0b10000)
        data['mildew'] = bool(payload[0x16] & 0b1000)

        if (unidentified_commands_debug):
            data['cmnd_0d_rmask'] = payload[0x0d] & 0xf
            data['cmnd_0e_rmask'] = payload[0x0e] & 0xf
            data['cmnd_18'] = payload[0x18]

        checksum = self._calculate_checksum(payload[2:0x19], 'little')
        if payload[0x19:0x1b] != checksum:
            print(f'get_state, checksum fail: calculated '
                  f'{checksum.hex()} actual {payload[0x19:0x1b].hex()}')

        if (payload_debug):
            print(payload.hex(' '))

        return data

    def get_ac_info(self, payload_debug: bool = False) -> dict:
        """Returns dictionary with A/C info.

        Args:
            payload_debug (Optional[bool]): print the received payload

        Returns:
            dict:
                state (bool): power
                ambient_temp (float): ambient temperature
        """
        payload = self._send_short_payload(0)
        if (len(payload) != 48):
            raise ValueError(f'get_ac_info, unexpected payload size: {len(payload)}')

        # The first 13 bytes are the same: 22 00 bb 00 07 00 00 00 18 00 01 21 c0,
        # bytes 0x23,0x24 are the checksum
        # bytes 0x25 forward are always empty
        data = {}
        data['state'] = payload[0x0d] & 0b1 == 0b1

        ambient_temp = payload[0x11] & 0b00011111
        if ambient_temp:
            data['ambient_temp'] = ambient_temp + float(payload[0x21] & 0b00011111) / 10.0

        checksum = self._calculate_checksum(payload[2:0x23], 'big')
        if (payload[0x23:0x25] != checksum):
            print(f'in get_ac_state, checksum fail: calculated '
                  f'{checksum.hex()} actual {payload[0x23:0x25].hex()}')

        if (payload_debug):
            print(payload.hex(' '))

        return data

    def set_advanced(
        self,
        state: bool,
        mode: str,
        target_temp: float,
        speed: str,
        swing_v: str,
        swing_h: str,
        sleep: bool,
        display: bool,
        health: bool,
        clean: bool,
        mildew: bool,
        cmnd_0d_rmask: int = 0b100,
        cmnd_0e_rmask: int = 0b1101,
        cmnd_18: int = 0b101,
        payload_debug: bool = False
    ) -> bytes:
        """Set parameters of unit.

        Use `set_partial` to modify only some parameters.

        Args:
            state (bool): power
            target_temp (float): temperature set point 16<n<32
            mode (str): cooling, heating, fan, dry, auto
            speed (str): mute, low, mid, high, turbo (available only for cooling)
            swing_h (str): ON, OFF
            swing_v (str): ON, OFF, 1, 2, 3, 4, 5 (fixed positions)
            sleep (bool)
            display (bool)
            health (bool)
            clean (bool)
            mildew (bool)
            cmnd_0d_rmask (Optional[int]): override an unidentified option
            cmnd_0e_rmask (Optional[int]): override an unidentified option
            cmnd_18 (Optional[int]): override an unidentified option
            payload_debug (Optional[bool]): print the constructed payload

        Returns:
            True for verified success.
        """

        PREFIX = [0x19, 0x00, 0xbb, 0x00, 0x06, 0x80, 0x00, 0x00, 0x0f, 0x00,
                  0x01, 0x01]  # 12B
        MIDDLE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]  # 13B + 2B checksum
        SUFFIX = [0, 0, 0, 0, 0]  # 5B
        payload = PREFIX + MIDDLE + SUFFIX

        target_temp = round(target_temp * 2) / 2
        if not (target_temp >= 16 and target_temp <= 32):
            raise ValueError(f'target_temp out of range, value: {target_temp}')

        if swing_v == 'OFF':
            swing_L = 0b111
        elif swing_v == 'ON':
            swing_L = 0b000
        elif (int(swing_v) >= 0 and int(swing_v) <= 5):
            swing_L = int(swing_v)
        else:
            raise ValueError(f'unrecognized swing vertical value {swing_v}')

        if swing_h == 'OFF':
            swing_R = 0b111
        elif swing_h == 'ON':
            swing_R = 0b000
        else:
            raise ValueError(f'unrecognized swing horizontal value {swing_h}')

        if (mode == 'auto'):
            mode_1 = 0x00
        elif (mode == 'cooling'):
            mode_1 = 0x20
        elif (mode == 'drying'):
            mode_1 = 0x40
        elif (mode == 'heating'):
            mode_1 = 0x80
        elif (mode == 'fan'):
            mode_1 = 0xc0
            # target_temp is irrelevant in this case
        else:
            raise ValueError(f'unrecognized mode value {mode}')

        if speed == 'low':
            speed_L, speed_R = 0x60, 0x00
        elif speed == 'mid':
            speed_L, speed_R = 0x40, 0x00
        elif speed == 'high':
            speed_L, speed_R = 0x20, 0x00
        elif speed == 'mute':
            speed_L, speed_R = 0x40, 0x80
            if mode != 'fan':
                raise ValueError('mute speed is only available in fan mode')
        elif speed == 'turbo':
            speed_L = 0x20  # doesn't matter
            speed_R = 0x40
            if mode not in ('cooling', 'heating'):
                raise ValueError('turbo speed is only available in cooling and heating modes')
        elif speed == 'auto':
            speed_L, speed_R = 0xa0, 0x00
        else:
            raise ValueError(f'unrecognized speed value: {speed}')

        payload[0x0c] = (int(target_temp) - 8 << 3) | swing_L
        payload[0x0d] = (swing_R << 5) | cmnd_0d_rmask
        payload[0x0e] = (0b10000000 if (target_temp % 1 == 0.5) else 0b0
                         | cmnd_0e_rmask)
        payload[0x0f] = speed_L
        payload[0x10] = speed_R
        payload[0x11] = mode_1 | (0b100 if sleep else 0b000)
        # payload[0x12] = always 0x00
        # payload[0x13] = always 0x00
        payload[0x14] = (0b100000 if state else 0b000000
                         | 0b100 if clean else 0b000
                         | 0b11 if health else 0b00)
        # payload[0x15] = always 0x00
        payload[0x16] = (0b10000 if display else 0b00000
                         | 0b1000 if mildew else 0b0000)
        # payload[0x17] = always 0x00
        payload[0x18] = cmnd_18

        checksum = self._calculate_checksum(payload[2:0x19], 'little')
        payload[0x19:0x1b] = checksum

        if (payload_debug):
            print(payload.hex(' '))

        response = self.send_packet(0x6a, bytearray(payload))
        check_error(response[0x22:0x24])
        response_payload = self._decode(response)
        # Response payloads are 16 bytes long.
        # The first 12 bytes are always 0e 00 bb 00 07 00 00 00 04 00 01 01,
        # the next two should be the checksum of the sent command
        # and the last two are the checksum of the response.
        if (response_payload[0xe:0x10]
                == self._calculate_checksum(response_payload[2:0xe], 'little')):
            if response_payload[0xc:0xe] == checksum:
                return True

        return False

    def set_partial(
        self,
        state: bool = None,
        mode: str = None,
        target_temp: float = None,
        speed: str = None,
        swing_v: str = None,
        swing_h: str = None,
        sleep: bool = None,
        display: bool = None,
        health: bool = None,
        clean: bool = None,
        mildew: bool = None,
        cmnd_0d_rmask: int = None,
        cmnd_0e_rmask: int = None,
        cmnd_18: int = None,
        payload_debug: bool = False
    ) -> bool:
        """Retrieves the current state and changes only the specified parameters.

        Uses `get_state` and `set_advanced` internally (see usage there)."""

        try:
            received_state = self.get_state()
        except ValueError as e:
            if str(e) == "unexpected payload size: 48":
                # Occasionally a 48 byte payload gets mixed in,
                # a retry should suffice.
                received_state = self.get_state()
            else:
                raise

        args = {
            'state': state if state is not None else received_state['state'],
            'mode': mode if mode is not None else received_state['mode'],
            'target_temp': target_temp if target_temp is not None else received_state['target_temp'],
            'speed': speed if speed is not None else received_state['speed'],
            'swing_v': swing_v if swing_v is not None else received_state['swing_v'],
            'swing_h': swing_h if swing_h is not None else received_state['swing_h'],
            'sleep': sleep if sleep is not None else received_state['sleep'],
            'display': display if display is not None else received_state['display'],
            'health': health if health is not None else received_state['health'],
            'clean': clean if clean is not None else received_state['clean'],
            'mildew': mildew if mildew is not None else received_state['mildew'],
            'payload_debug': payload_debug
        }

        # Allow overriding of optional parameters
        if cmnd_0d_rmask is not None:
            args['cmnd_0d_rmask'] = cmnd_0d_rmask
        if cmnd_0e_rmask is not None:
            args['cmnd_0e_rmask'] = cmnd_0e_rmask
        if cmnd_18 is not None:
            args['cmnd_18'] = cmnd_18

        return self.set_advanced(**args)
