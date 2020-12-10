"""Support for climate control."""
from typing import List
import logging
from enum import IntEnum, unique

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

    REQUEST_PREFIX = bytes([0xbb, 0x00, 0x06, 0x80])
    RESPONSE_PREFIX = bytes([0xbb, 0x00, 0x07, 0x00])

    @unique
    class Mode(IntEnum):
        AUTO = 0
        COOLING = 0x20
        DRYING = 0x40
        HEATING = 0x80
        FAN = 0xc0

    @unique
    class Speed(IntEnum):
        HIGH = 0x20
        MID = 0x40
        LOW = 0x60
        AUTO = 0xa0

    @unique
    class Swing_H(IntEnum):
        ON = 0b000,
        OFF = 0b111

    @unique
    class Swing_V(IntEnum):
        ON = 0b000,
        POS_1 = 1
        POS_2 = 2
        POS_3 = 3
        POS_4 = 4
        POS_5 = 5
        OFF = 0b111

    def __init__(self, *args, **kwargs):
        device.__init__(self, *args, **kwargs)
        self.type = "Tornado SQ air conditioner"

    def _decode(self, response) -> bytes:
        payload = self.decrypt(bytes(response[0x38:]))
        return payload

    def _calculate_checksum(self, payload: bytes) -> int:
        """Calculate checksum of given array,
        by adding little endian words and subtracting from 0xffff.

        The first two bytes of most packets in the class are the length of the
        payload and should be cropped out when using this function.

        Args:
            payload (bytes): the payload
        """
        s = sum([v if i % 2 == 0 else v << 8 for i, v in enumerate(payload)])
        # trim the overflow and add it to smallest bit
        s = (s & 0xffff) + (s >> 16)
        return (0xffff - s)

    def _encode(self, payload: bytes) -> bytes:
        """Encode payload (add length to beginning, checksum after payload)."""
        payload = self.REQUEST_PREFIX + payload
        checksum = self._calculate_checksum(payload).to_bytes(2, 'little')
        return (len(payload) + 2).to_bytes(2, 'little') + payload + checksum

    def _send_short_payload(self, payload: int) -> bytes:
        """Send a request for info from AC unit and returns the response.
        0 = GET_AC_INFO, 1 = GET_STATES, 2 = GET_SLEEP_INFO
        """
        packet = bytes(
            [0x00, 0x00, 0x02, 0x00]
            + {
                0: [0x21, 0x01],
                1: [0x11, 0x01],
                2: [0x41, 0x01]
            }[payload]
        )

        response = self.send_packet(0x6a, self._encode(packet))
        check_error(response[0x22:0x24])
        return (self._decode(response))

    def get_state(self) -> dict:
        """Returns a dictionary with the unit's parameters.

        Returns:
            dict:
                state (bool): power
                target_temp (float): temperature set point 16<n<32
                mode (sq1.Mode): COOLING, HEATING, FAN, DRY, AUTO
                speed (sq1.Speed): LOW, MID, HIGH, AUTO
                mute (bool):
                turbo (bool):
                swing_h (sq1.Swing_H): ON, OFF
                swing_v (sq1.Swing_V): ON, OFF, POS_1, POS_2, POS_3, POS_4, POS_5
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
                               + (0.0 if (payload[0xe] & 0b10000000) == 0 else 0.5))  # noqa E501

        data['swing_h'] = self.Swing_H((payload[0x0d] & 0b11100000) >> 5)
        data['swing_v'] = self.Swing_V(payload[0x0c] & 0b111)

        data['mode'] = self.Mode(payload[0x11] & ~ 0b111)

        data['speed'] = self.Speed(payload[0x0f])

        data['mute'] = bool(payload[0x10] == 0x80)
        data['turbo'] = bool(payload[0x10] == 0x40)

        data['sleep'] = bool(payload[0x11] & 0b100)

        data['health'] = bool(payload[0x14] & 0b10)
        data['clean'] = bool(payload[0x14] & 0b100)

        data['display'] = bool(payload[0x16] & 0b10000)
        data['mildew'] = bool(payload[0x16] & 0b1000)

        checksum = self._calculate_checksum(payload[2:0x19]
                                            ).to_bytes(2, 'little')
        if payload[0x19:0x1b] != checksum:
            logging.warning("checksum fail: calculated %s actual %s",
                            checksum.hex(), payload[0x19:0x1b].hex())

        logging.debug("Received payload:\n%s", payload.hex(' '))
        logging.debug("0b[R] mask: %x, 0c[R] mask: %x, cmnd_16: %x",
                      payload[0x0d] & 0xf, payload[0x0e] & 0xf, payload[0x18])
        logging.debug("Data: %s", data)

        return data

    def get_ac_info(self) -> dict:
        """Returns dictionary with AC info.

        Returns:
            dict:
                state (bool): power
                ambient_temp (float): ambient temperature
        """
        payload = self._send_short_payload(0)
        if (len(payload) != 48):
            raise ValueError(f"unexpected payload size: {len(payload)}")

        # Length is 34 (0x22), the next 11 bytes are
        # the same: bb 00 07 00 00 00 18 00 01 21 c0,
        # bytes 0x23,0x24 are the checksum.
        data = {}
        data['state'] = payload[0x0d] & 0b1 == 0b1

        ambient_temp = payload[0x11] & 0b00011111
        if ambient_temp:
            data['ambient_temp'] = (ambient_temp
                                    + float(payload[0x21] & 0b00011111) / 10.0)

        checksum = self._calculate_checksum(payload[2:0x23]).to_bytes(2, 'big')
        if (payload[0x23:0x25] != checksum):
            logging.warning("checksum fail: calculated %s actual %s",
                            checksum.hex(), payload[0x23:0x25].hex())

        logging.debug("Received payload:\n%s", payload.hex(' '))

        return data

    def set_state(self, args: dict) -> bool:
        """Set parameters of unit.

        Args:
            args (dict): if any are missing the current value will be retrived
                state (bool): power
                target_temp (float): temperature set point 16<n<32
                mode (sq1.Mode): COOLING, HEATING, FAN, DRY, AUTO
                speed (sq1.Speed): LOW, MID, HIGH, AUTO
                mute (bool):
                turbo (bool):
                swing_h (sq1.Swing_H): ON, OFF
                swing_v (sq1.Swing_V): ON, OFF, POS_1, POS_2, POS_3, POS_4, POS_5
                sleep (bool)
                display (bool)
                health (bool)
                clean (bool)
                mildew (bool)

        Returns:
            True for success, verified by the unit's response.
        """
        CMND_0B_RMASK = 0b100
        CMND_0C_RMASK = 0b1101
        CMND_16 = 0b101

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
                    raise e
            logging.debug("Raw args %s", args)
            received_state.update(args)
            args = received_state
            logging.debug("Filled args %s", args)

        args['target_temp'] = round(args['target_temp'] * 2) / 2
        if not (args['target_temp'] >= 16 and args['target_temp'] <= 32):
            raise ValueError(f"target_temp out of range, value: {args['target_temp']}")  # noqa E501

        if not isinstance(args['swing_h'], self.Swing_H):
            raise ValueError("{} isn't a {} object".format(
                args['swing_h'], self.Swing_H.__qualname__))
        swing_R = args['swing_h'].value
        if not isinstance(args['swing_v'], self.Swing_V):
            raise ValueError("{} isn't a {} object".format(
                args['swing_v'], self.Swing_V.__qualname__))
        swing_L = args['swing_v'].value

        if not isinstance(args['mode'], self.Mode):
            raise ValueError("{} isn't a {} object".format(
                args['mode'], self.Mode.__qualname__))
        mode = args['mode'].value

        if args['mute'] and args['turbo']:
            raise ValueError("mute and turbo can't be on at once")
        elif args['mute']:
            speed_R = 0x80
            if args['mode'] != 'fan':
                raise ValueError("mute is only available in fan mode")
            args['speed'] = self.Speed.LOW
        elif args['turbo']:
            speed_R = 0x40
            if args['mode'] not in ('cooling', 'heating'):
                raise ValueError("turbo is only available in cooling/heating")
            args['speed'] = self.Speed.HIGH
        else:
            speed_R = 0x00

        if not isinstance(args['speed'], self.Speed):
            raise ValueError("{} isn't a {} object".format(
                args['speed'], self.Speed.__qualname__))
        speed_L = args['speed'].value

        payload = self._encode(bytes(
            [
                0x00,
                0x00,
                0x0f,
                0x00,
                0x01,
                0x01,
                (int(args['target_temp']) - 8 << 3) | swing_L,
                (swing_R << 5) | CMND_0B_RMASK,
                (0b10000000 if (args['target_temp'] % 1 == 0.5) else 0
                 | CMND_0C_RMASK),
                speed_L,
                speed_R,
                mode | (0b100 if args['sleep'] else 0b000),
                0x00,
                0x00,
                (0b100000 if args['state'] else 0b000000
                 | 0b100 if args['clean'] else 0b000
                 | 0b11 if args['health'] else 0b00),
                0x00,
                (0b10000 if args['display'] else 0b00000
                 | 0b1000 if args['mildew'] else 0b0000),
                0x00,
                CMND_16
            ]
        ))
        logging.debug("Constructed payload:\n%s", payload.hex(' '))

        response = self.send_packet(0x6a, payload)
        check_error(response[0x22:0x24])
        response_payload = self._decode(response)
        logging.debug("Response payload:\n%s", response_payload.hex(' '))
        # Response payloads are 16 bytes long.
        # The first 12 bytes are always 0e 00 bb 00 07 00 00 00 04 00 01 01,
        # the next two should be the checksum of the sent command
        # and the last two are the checksum of the response.

        if (response_payload[0xe:0x10] == self._calculate_checksum(
                response_payload[2:0xe]).to_bytes(2, 'little')):
            if response_payload[0xc:0xe] == payload[0x19:0x1b]:
                return True
            else:
                logging.warning(
                    "Checksum in response %s different from sent payload %s",
                    response_payload[0xc:0xe].hex(), payload[0x19:0x1b].hex()
                )

        return False
