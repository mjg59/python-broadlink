"""Support for climate control."""
from typing import List
import logging

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

    def _encode(self, payload: bytes) -> bytes:
        """Encode payload i.e. add length to beginning, checksum after payload,
        and pad size.
        """
        import struct
        length = 2 + len(payload)  # length prefix
        packet_length = ((length - 1) // 16 + 1) * 16
        packet = bytearray(2)
        struct.pack_into("<H", packet, 0, length)
        packet.extend(payload)
        packet.extend(self._calculate_checksum(packet[2:], 'little'))
        packet.extend([0] * (packet_length - len(packet)))  # round size to 16

        return packet

    def _send_short_payload(self, payload: int) -> bytes:
        """Send a request for info from AC unit and returns the response.
        0 = GET_AC_INFO, 1 = GET_STATES, 2 = GET_SLEEP_INFO
        """
        packet = bytearray([0xbb, 0x00, 0x06, 0x80, 0x00, 0x00, 0x02, 0x00])
        if (payload == 0):
            packet.extend([0x21, 0x01])
        elif (payload == 1):
            packet.extend([0x11, 0x01])
        elif (payload == 2):
            packet.extend([0x41, 0x01])
        # elif (payload == 3):
        #     packet = bytearray(16)
        #     packet[0x00] = 0xd0
        #     packet[0x01] = 0x07
        else:
            raise ValueError(f"unrecognized payload type: {payload}")

        response = self.send_packet(0x6a, self._encode(packet))
        check_error(response[0x22:0x24])
        return (self._decode(response))

    def get_state(self) -> dict:
        """Returns a dictionary with the unit's parameters.

        Returns:
            dict:
                state (bool): power
                target_temp (float): temperature set point 16<n<32
                mode (str): cooling, heating, fan, dry, auto
                speed (str): low, mid, high, auto
                mute (bool):
                turbo (bool):
                swing_h (str): ON, OFF
                swing_v (str): ON, OFF, 1, 2, 3, 4, 5 (fixed positions)
                sleep (bool):
                display (bool):
                health (bool):
                clean (bool):
                mildew (bool):
        """
        payload = self._send_short_payload(1)
        if (len(payload) != 32):
            raise RuntimeError(f"unexpected payload size: {len(payload)}")

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

        mode = payload[0x11] &~ 0b111  # noqa E225
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

        if payload[0x0f] == 0x60:
            data['speed'] = 'low'
        elif payload[0x0f] == 0x40:
            data['speed'] = 'mid'
        elif payload[0x0f] == 0x20:
            data['speed'] = 'high'
        elif payload[0x0f] == 0xa0:
            data['speed'] = 'auto'
        else:
            data['speed'] = 'unrecognized value'

        data['mute'] = bool(payload[0x10] == 0x80)
        data['turbo'] = bool(payload[0x10] == 0x40)

        data['sleep'] = bool(payload[0x11] & 0b100)

        data['health'] = bool(payload[0x14] & 0b10)
        data['clean'] = bool(payload[0x14] & 0b100)

        data['display'] = bool(payload[0x16] & 0b10000)
        data['mildew'] = bool(payload[0x16] & 0b1000)

        checksum = self._calculate_checksum(payload[2:0x19], 'little')
        if payload[0x19:0x1b] != checksum:
            logging.warning("checksum fail: calculated %s actual %s",
                            checksum.hex(), payload[0x19:0x1b].hex())

        logging.debug("Received payload:\n%s", payload.hex(' '))
        logging.debug("0b[R] mask: %x, 0c[R] mask: %x, cmnd_16: %x",
                      payload[0x0d] & 0xf, payload[0x0e] & 0xf, payload[0x18])
        logging.debug("Data: %s", data)

        return data

    def get_ac_info(self) -> dict:
        """Returns dictionary with A/C info.

        Returns:
            dict:
                state (bool): power
                ambient_temp (float): ambient temperature
        """
        payload = self._send_short_payload(0)
        if (len(payload) != 48):
            raise ValueError(f"get_ac_info, unexpected payload size: {len(payload)}")

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
            logging.warning("checksum fail: calculated %s actual %s",
                            checksum.hex(), payload[0x23:0x25].hex())

        logging.debug("Received payload:\n%s", payload.hex(' '))

        return data

    def set_state(self, args: dict) -> bytes:
        """Set parameters of unit.

        Args:
            args: if any are missing the current state will be retrived with `get_state`
                state (bool): power
                target_temp (float): temperature set point 16<n<32
                mode (str): cooling, heating, fan, dry, auto
                speed (str): low, mid, high, auto
                mute (bool):
                turbo (bool):
                swing_h (str): ON, OFF
                swing_v (str): ON, OFF, 1, 2, 3, 4, 5 (fixed positions)
                sleep (bool)
                display (bool)
                health (bool)
                clean (bool)
                mildew (bool)

        Returns:
            True for success, verified by the unit's response.
        """
        cmnd_0b_rmask = 0b100
        cmnd_0c_rmask = 0b1101
        cmnd_16 = 0b101

        keys = ['state', 'mode', 'target_temp', 'speed', 'mute', 'turbo',
                'swing_v', 'swing_h', 'sleep', 'display', 'health', 'clean',
                'mildew']
        unknown_keys = [key for key in args.keys() if key not in keys]
        if len(unknown_keys) > 0:
            raise ValueError(f"unknown argument(s) {unknown_keys}")

        missing_keys = [key for key in keys if key not in args]
        if len(missing_keys) > 0:
            try:
                received_state = self.get_state()
            except RuntimeError as e:
                if "unexpected payload size: 48" in str(e):
                    # Occasionally a 48 byte payload gets mixed in,
                    # a retry should suffice.
                    received_state = self.get_state()
                else:
                    raise(e)
            logging.debug("raw args %s", args)
            received_state.update(args)
            args = received_state
            logging.debug("filled args %s", args)

        PREFIX = [0xbb, 0x00, 0x06, 0x80, 0x00, 0x00, 0x0f, 0x00,
                  0x01, 0x01]  # 10B
        MIDDLE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0]  # 13B
        payload = bytearray(PREFIX + MIDDLE)

        args['target_temp'] = round(args['target_temp'] * 2) / 2
        if not (args['target_temp'] >= 16 and args['target_temp'] <= 32):
            raise ValueError(f"target_temp out of range, value: {args['target_temp']}")

        if args['swing_v'] == 'OFF':
            swing_L = 0b111
        elif args['swing_v'] == 'ON':
            swing_L = 0b000
        elif (int(args['swing_v']) >= 0 and int(args['swing_v']) <= 5):
            swing_L = int(args['swing_v'])
        else:
            raise ValueError(f"unrecognized swing vertical value {args['swing_v']}")

        if args['swing_h'] == 'OFF':
            swing_R = 0b111
        elif args['swing_h'] == 'ON':
            swing_R = 0b000
        else:
            raise ValueError(f"unrecognized swing horizontal value {args['swing_h']}")

        if (args['mode'] == 'auto'):
            mode_1 = 0x00
        elif (args['mode'] == 'cooling'):
            mode_1 = 0x20
        elif (args['mode'] == 'drying'):
            mode_1 = 0x40
        elif (args['mode'] == 'heating'):
            mode_1 = 0x80
        elif (args['mode'] == 'fan'):
            mode_1 = 0xc0
            # target_temp is irrelevant in this case
        else:
            raise ValueError(f"unrecognized mode value {args['mode']}")

        if args['mute'] and args['turbo']:
            raise ValueError("mute and turbo can't be on at once")
        elif args['mute']:
            speed_R = 0x80
            if args['mode'] != 'fan':
                raise ValueError("mute is only available in fan mode")
            args['speed'] = 'low'
        elif args['turbo']:
            speed_R = 0x40
            if args['mode'] not in ('cooling', 'heating'):
                raise ValueError("turbo is only available in cooling/heating")
            args['speed'] = 'high'
        else:
            speed_R = 0x00

        if args['speed'] == 'low':
            speed_L = 0x60
        elif args['speed'] == 'mid':
            speed_L = 0x40
        elif args['speed'] == 'high':
            speed_L = 0x20
        elif args['speed'] == 'auto':
            speed_L = 0xa0
        else:
            raise ValueError(f"unrecognized speed value: {args['speed']}")

        payload[0x0a] = (int(args['target_temp']) - 8 << 3) | swing_L
        payload[0x0b] = (swing_R << 5) | cmnd_0b_rmask
        payload[0x0c] = (0b10000000 if (args['target_temp'] % 1 == 0.5) else 0
                         | cmnd_0c_rmask)
        payload[0x0d] = speed_L
        payload[0x0e] = speed_R
        payload[0x0f] = mode_1 | (0b100 if args['sleep'] else 0b000)
        # payload[0x10] = always 0x00
        # payload[0x11] = always 0x00
        payload[0x12] = (0b100000 if args['state'] else 0b000000
                         | 0b100 if args['clean'] else 0b000
                         | 0b11 if args['health'] else 0b00)
        # payload[0x13] = always 0x00
        payload[0x14] = (0b10000 if args['display'] else 0b00000
                         | 0b1000 if args['mildew'] else 0b0000)
        # payload[0x15] = always 0x00
        payload[0x16] = cmnd_16

        checksum = self._calculate_checksum(payload, 'little')
        payload = self._encode(payload)

        logging.debug("Constructed payload:\n%s", payload.hex(' '))

        response = self.send_packet(0x6a, payload)
        check_error(response[0x22:0x24])
        response_payload = self._decode(response)
        logging.debug("Response payload:\n%s", response_payload.hex(' '))
        # Response payloads are 16 bytes long.
        # The first 12 bytes are always 0e 00 bb 00 07 00 00 00 04 00 01 01,
        # the next two should be the checksum of the sent command
        # and the last two are the checksum of the response.
        if (response_payload[0xe:0x10]
                == self._calculate_checksum(response_payload[2:0xe], 'little')):
            if response_payload[0xc:0xe] == checksum:
                return True
            else:
                logging.warning("Checksum in response %s different from sent payload %s",
                                response_payload[0xc:0xe].hex(), checksum.hex())

        return False
