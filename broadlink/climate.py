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

class tornado(device):
    """Controls Tornado TOP SQ X series air conditioners."""
    def __init__(self, *args, **kwargs):
        device.__init__(self, *args, **kwargs)
        self.type = "Tornado air conditioner"
    
    def _decode(self, response) -> bytes:
        payload = self.decrypt(bytes(response[0x38:]))
        return payload
    
    def _calculate_checksum(self, packet:bytes, target:int=0x20017) -> tuple:
        """Calculate checksum of given array,
        by adding little endian words and subtracting from target.
        
        Args:
            packet (list/bytearray/bytes): 
        """
        result = target - (sum([v if i % 2 == 0 else v << 8 for i, v in enumerate(packet)]) & 0xffff)
        return (result & 0xff, (result >> 8) & 0xff)

    def _send_short_payload(self, payload:int) -> bytes:
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
            raise ValueError('unrecognized payload type: {}'.format(payload))

        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        return (self._decode(response))

    def get_state(self, payload_debug: bool = None) -> dict:
        """Returns a dictionary with the unit's parameters.
        
        Args:
            payload_debug (Optional[bool]): add the received payload for debugging
        
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
                cmnd_0d_rmask (int): unknown
                cmnd_0e_rmask (int): unknown
                cmnd_18 (int): unknown
        """
        payload = self._send_short_payload(1)
        if (len(payload) != 32):
            raise ValueError('unexpected payload size: {}'.format(len(payload)))
        
        data = {}
        data['state'] = payload[0x14] & 0x20 == 0x20
        data['target_temp'] = (payload[0x0c] >> 3) + 8 + (0.0 if ((payload[0xe] & 0b10000000) == 0) else 0.5)

        swing_v = payload[0x0c] & 0b111
        swing_h = (payload[0x0d] & 0b11100000) >> 5
        if (swing_h == 0b111):
            data['swing_h'] = 'OFF'
        elif (swing_h == 0b000):
            data['swing_h'] = 'ON'
        else:
            data['swing_h'] = 'unrecognized value'
        
        if (swing_v == 0b111):
            data['swing_v'] = 'OFF'
        elif (swing_v == 0b000):
            data['swing_v'] = 'ON'
        elif (swing_v >= 0 and swing_v <=5):
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
        data['display'] = (payload[0x16] & 0x10 == 0x10)
        data['health'] = (payload[0x14] & 0b11 == 0b11)
        data['cmnd_0d_rmask'] = payload[0x0d] & 0xf
        data['cmnd_0e_rmask'] = payload[0x0e] & 0xf
        data['cmnd_18'] = payload[0x18]

        checksum = self._calculate_checksum(payload[:0x19]) # checksum=(payload[0x1a] << 8) + payload[0x19]

        if (payload[0x19] == checksum[0] and payload[0x1a] == checksum[1]):
            pass # success
        else:
            print('checksum fail', ['{:02x}'.format(x) for x in checksum])

        if (payload_debug):
            data['received_payload'] = payload

        return data

    def get_ac_info(self, payload_debug: bool = None) -> dict:
        """Returns dictionary with A/C info...
        Not implemented yet, except power state.

        Args:
            payload_debug (Optional[bool]): add the received payload for debugging
        """
        payload = self._send_short_payload(0)

        # first 13 bytes are the same: 22 00 bb 00 07 00 00 00 18 00 01 21 c0
        data = {}
        data['state'] = True if (payload[0x0d] & 0b1 == 0b1) else False

        if (payload_debug):
            data['received_payload'] = payload

        return data

    def set_advanced(self,
        state: bool,
        mode: str,
        target_temp: float,
        speed: str,
        swing_v: str,
        swing_h: str,
        sleep: bool,
        display: bool,
        health: bool,
        cmnd_0d_rmask: int,
        cmnd_0e_rmask: int,
        cmnd_18: int,
        checksum_lbit: int
    ) -> bytes:
        """Set paramaters of unit and return response. All parameters need to be specified.
        
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
            cmnd_0d_rmask (int): unknown
            cmnd_0e_rmask (int): unknown
            cmnd_18 (int): unknown
            checksum_lbit (int): subtracted from the left byte of the checksum
        """
        
        PREFIX = [0x19, 0x00, 0xbb, 0x00, 0x06, 0x80, 0x00, 0x00, 0x0f, 0x00, 0x01, 0x01] # 12B
        MIDDLE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 13B + 2B checksum
        SUFFIX = [0, 0, 0, 0, 0] # 5B
        payload = PREFIX + MIDDLE + SUFFIX

        assert ((target_temp >= 16) and (target_temp <= 32) and ((target_temp * 2) % 1 == 0))

        if (swing_v == 'OFF'):
            swing_L = 0b111
        elif (swing_v == 'ON'):
            swing_L = 0b000
        else:
            raise ValueError('unrecognized swing vertical value {}'.format(swing_v))

        if (swing_h == 'OFF'):
            swing_R = 0b111
        elif (swing_h == 'ON'):
            swing_R = 0b000
        elif (swing_h >= 0 and swing_v <= 5):
            swing_R = str(swing_v)
        else:
            raise ValueError('unrecognized swing horizontal value {}'.format(swing_h))

        if (speed == 'low'):
            speed_L, speed_R = 0x60, 0x00
        elif (speed == 'mid'):
            speed_L, speed_R = 0x40, 0x00
        elif (speed  == 'high'):
            speed_L, speed_R = 0x20, 0x00
        elif (speed == 'mute'):
            speed_L, speed_R = 0x40, 0x80
            assert (mode == 'F')
        elif (speed == 'turbo'):
            speed_R = 0x40
            speed_L = 0x20 # doesn't matter
        elif (speed == 'auto'):
            speed_L, speed_R = 0xa0, 0x00
        else:
            raise ValueError('unrecognized speed value: {}'.format(speed))

        if (mode == 'auto'):
            mode_1 = 0x00
        elif (mode == 'cooling'):
            mode_1 = 0x20
        elif (mode == 'drying'):
            mode_1 = 0x40
            cmnd_0e_rmask = 0x16
        elif (mode == 'heating'):
            mode_1 = 0x80
        elif (mode == 'fan'):
            mode_1 = 0xc0
            target_temp = 24.0
            if speed == 'turbo':
                raise ValueError('speed cannot be {} in fan mode'.format(speed))
        else:
            raise ValueError('unrecognized mode value: {}'.format(mode))

        payload[0x0c] = ((int(target_temp) - 8 << 3) | swing_L)
        payload[0x0d] = (int(swing_R) << 5) | cmnd_0d_rmask
        payload[0x0e] = (0b10000000 if (target_temp % 1 == 0.5) else 0b0) | cmnd_0e_rmask
        payload[0x0f] = speed_L
        payload[0x10] = speed_R
        payload[0x11] = mode_1 | (0b100 if sleep else 0b000)
        # payload[0x12] = always 0x00
        # payload[0x13] = always 0x00
        payload[0x14] = (0b11 if health else 0b00) | (0b100000 if state else 0b000000)
        # payload[0x15] = always 0x00
        payload[0x16] = 0b10000 if display else 0b00000 # 0b_00 also changes
        # payload[0x17] = always 0x00
        payload[0x18] = cmnd_18
        
        # 0x19-0x1a - checksum
        checksum = self._calculate_checksum(payload[:0x19]) # checksum=(payload[0x1a] << 8) + payload[0x19]
        payload[0x19] = checksum[0] - checksum_lbit
        payload[0x1a] = checksum[1]

        response = self.send_packet(0x6a, bytearray(payload))
        check_error(response[0x22:0x24])
        response_payload = self._decode(response)
        return response_payload

    def set_partial(self,
        state: bool = None,
        mode: str = None,
        target_temp: float = None,
        speed: str = None,
        swing_v: str = None,
        swing_h: str = None,
        sleep: bool = None,
        display: bool = None,
        health: bool = None,
        cmnd_0d_rmask: int = 0b100,
        cmnd_0e_rmask: int = 0b1101,
        cmnd_18: int = 0b101,
    ) -> bytes:
        """Retrieves the current state and changes only the specified parameters.
        
        Uses `get_state` and `set_advanced` internally."""

        try:
            received_state = self.get_state()
        except ValueError as e:
            if str(e) == "unexpected payload size: 48":
                # Occasionally you will get 48 byte payloads. Reading these isn't implemented yet but a retry should suffice.
                received_state = self.get_state()
            else:
                raise

        args = {
            'state': state if state != None else received_state['state'],
            'mode': mode if mode != None else received_state['mode'],
            'target_temp': target_temp if target_temp != None else received_state['target_temp'],
            'speed': speed if speed != None else received_state['speed'],
            'swing_v': swing_v if swing_v != None else received_state['swing_v'],
            'swing_h': swing_h if swing_h != None else received_state['swing_h'],
            'sleep': sleep if sleep != None else received_state['sleep'],
            'display': display if display != None else received_state['display'],
            'health': health if health != None else received_state['health'],
            'cmnd_0d_rmask': cmnd_0d_rmask,
            'cmnd_0e_rmask': cmnd_0e_rmask,
            'cmnd_18': cmnd_18,
            'checksum_lbit': 0
        }

        if (args['mode'] == 'heating' or args['mode'] == 'fan' or args['mode'] == 'drying'):
            args['checksum_lbit'] = 1
            if (args['swing_h'] == 'ON'):
                args['checksum_lbit'] = 0
        
        return self.set_advanced(**args)
