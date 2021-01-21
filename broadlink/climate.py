"""Support for climate control."""
from typing import List
import logging
from enum import IntEnum, unique
import struct

from .device import device
from .exceptions import check_error
from .helpers import calculate_crc16


class hysen(device):
    """Controls a Hysen HVAC."""

    TYPE = "Hysen heating controller"

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


class hvac(device):
    """Controls a HVAC.

    Supported models:
    - Tornado SMART X SQ series.
    """

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
    class SwingH(IntEnum):
        ON = 0b000,
        OFF = 0b111

    @unique
    class SwingV(IntEnum):
        ON = 0b000,
        POS1 = 1
        POS2 = 2
        POS3 = 3
        POS4 = 4
        POS5 = 5
        OFF = 0b111

    def __init__(self, *args, **kwargs):
        device.__init__(self, *args, **kwargs)
        self.type = "HVAC"

    def _decode(self, response) -> bytes:
        # RESPONSE_PREFIX = bytes([0xbb, 0x00, 0x07, 0x00, 0x00, 0x00])
        payload = self.decrypt(bytes(response[0x38:]))

        length = int.from_bytes(payload[:2], 'little')
        checksum = self._calculate_checksum(
            payload[2:length]).to_bytes(2, 'little')
        if checksum == payload[length:length+2]:
            logging.debug("Checksum incorrect (calculated %s actual %s).",
                          checksum.hex(), payload[length:length+2].hex())

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

    def _encode(self, data: bytes) -> bytes:
        """Encode data for transport."""
        payload = struct.pack("HHHH", 0x00BB, 0x8006, 0x0000, len(data)) + data
        logging.debug("Payload:\n%s", payload.hex(' '))
        checksum = self._calculate_checksum(payload).to_bytes(2, 'little')
        return (len(payload) + 2).to_bytes(2, 'little') + payload + checksum

    def _send_command(self, command: int, data: bytes = b'') -> bytes:
        """Send a command to the unit.

        Known commands:
        - Get AC info: 0x0121
        - Get states: 0x0111
        - Get sleep info: 0x0141
        """
        packet = self._encode(command.to_bytes(2, "little") + data)
        logging.debug("Payload:\n%s", packet.hex(' '))
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        return self._decode(response)

    def get_state(self) -> dict:
        """Returns a dictionary with the unit's parameters.

        Returns:
            dict:
                power (bool):
                target_temp (float): temperature set point 16<n<32
                mode (hvac.Mode)
                speed (hvac.Speed)
                mute (bool):
                turbo (bool):
                swing_h (hvac.SwHoriz)
                swing_v (hvac.SwVert)
                sleep (bool):
                display (bool):
                health (bool):
                clean (bool):
                mildew (bool):
        """
        payload = self._send_command(0x111)
        if (len(payload) != 32):
            raise RuntimeError(f"unexpected payload size: {len(payload)}")

        logging.debug("Received payload:\n%s", payload.hex(' '))
        logging.debug("0b[R] mask: %x, 0c[R] mask: %x, cmnd_16: %x",
                      payload[0x0d] & 0xf, payload[0x0e] & 0xf, payload[0x18])

        data = {}
        data['power'] = payload[0x14] & 0x20 == 0x20
        data['target_temp'] = (8 + (payload[0x0c] >> 3)
                               + (0.0 if (payload[0xe] & 0b10000000) == 0 else 0.5))  # noqa E501

        data['swing_h'] = self.SwingH((payload[0x0d] & 0b11100000) >> 5)
        data['swing_v'] = self.SwingV(payload[0x0c] & 0b111)

        data['mode'] = self.Mode(payload[0x11] & ~ 0b111)

        data['speed'] = self.Speed(payload[0x0f])

        data['mute'] = bool(payload[0x10] == 0x80)
        data['turbo'] = bool(payload[0x10] == 0x40)

        data['sleep'] = bool(payload[0x11] & 0b100)

        data['health'] = bool(payload[0x14] & 0b10)
        data['clean'] = bool(payload[0x14] & 0b100)

        data['display'] = bool(payload[0x16] & 0b10000)
        data['mildew'] = bool(payload[0x16] & 0b1000)

        logging.debug("Data: %s", data)

        return data

    def get_ac_info(self) -> dict:
        """Returns dictionary with AC info.

        Returns:
            dict:
                state (bool): power
                ambient_temp (float): ambient temperature
        """
        payload = self._send_command(0x121)
        if (len(payload) != 48):
            raise ValueError(f"unexpected payload size: {len(payload)}")

        logging.debug("Received payload:\n%s", payload.hex(' '))

        # Length is 34 (0x22), the next 11 bytes are
        # the same: bb 00 07 00 00 00 18 00 01 21 c0,
        # bytes 0x23,0x24 are the checksum.
        data = {}
        data['state'] = payload[0x0d] & 0b1 == 0b1

        ambient_temp = payload[0x11] & 0b00011111
        if ambient_temp:
            data['ambient_temp'] = (ambient_temp
                                    + float(payload[0x21] & 0b00011111) / 10.0)

        logging.debug("Data: %s", data)
        return data

    def set_state(self, state: dict) -> bool:
        """Set parameters of unit.

        Args:
            state (dict): if any are missing the current value will be retrived
                power (bool):
                target_temp (float): temperature set point 16<n<32
                mode (hvac.Mode)
                speed (hvac.Speed)
                mute (bool):
                turbo (bool):
                swing_h (hvac.SwHoriz)
                swing_v (hvac.SwVert)
                sleep (bool):
                display (bool):
                health (bool):
                clean (bool):
                mildew (bool):

        Returns:
            True for success, verified by the unit's response.
        """
        CMND_0B_RMASK = 0b100
        CMND_0C_RMASK = 0b1101
        CMND_16 = 0b101

        keys = ['power', 'mode', 'target_temp', 'speed', 'mute', 'turbo',
                'swing_v', 'swing_h', 'sleep', 'display', 'health', 'clean',
                'mildew']
        unknown_keys = [key for key in state.keys() if key not in keys]
        if len(unknown_keys) > 0:
            raise ValueError(f"unknown argument(s) {unknown_keys}")

        missing_keys = [key for key in keys if key not in state]
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
            logging.debug("Raw state %s", state)
            received_state.update(state)
            state = received_state
            logging.debug("Filled state %s", state)

        state['target_temp'] = round(state['target_temp'] * 2) / 2
        if not (16 <= state['target_temp'] <= 32):
            raise ValueError(f"target_temp out of range: {state['target_temp']}")  # noqa E501

        # Creating a new instance verifies the type
        swing_R = self.SwingH(state['swing_h'])
        swing_L = self.SwingV(state['swing_v'])

        mode = self.Mode(state['mode'])

        if state['mute'] and state['turbo']:
            raise ValueError("mute and turbo can't be on at once")
        elif state['mute']:
            speed_R = 0x80
            if state['mode'] != 'fan':
                raise ValueError("mute is only available in fan mode")
            state['speed'] = self.Speed.LOW
        elif state['turbo']:
            speed_R = 0x40
            if state['mode'] not in ('cooling', 'heating'):
                raise ValueError("turbo is only available in cooling/heating")
            state['speed'] = self.Speed.HIGH
        else:
            speed_R = 0x00

        speed_L = self.Speed(state['speed'])

        data = bytes(
            [
                (int(state['target_temp']) - 8 << 3) | swing_L,
                (swing_R << 5) | CMND_0B_RMASK,
                ((state['target_temp'] % 1 == 0.5) << 7) | CMND_0C_RMASK,
                speed_L,
                speed_R,
                mode | (state['sleep'] << 2),
                0x00,
                0x00,
                (state['power'] << 5 | state['clean'] << 2 | 0b11 if state['health'] else 0b00),
                0x00,
                state['display'] << 4 | state['mildew'] << 3,
                0x00,
                CMND_16
            ]
        )
        logging.debug("Constructed payload data:\n%s", data.hex(' '))

        response_payload = self._send_command(0x0101, data)
        logging.debug("Response payload:\n%s", response_payload.hex(' '))
        # Response payloads are 16 bytes long,
        # Bytes 0d-0e are the checksum of the sent command.
