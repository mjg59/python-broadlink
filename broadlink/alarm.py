"""Support for alarm kits."""
from .device import device
from .exceptions import check_error


class S1C(device):
    """Controls a Broadlink S1C."""

    TYPE = "S1C"

    _SENSORS_TYPES = {
        0x31: "Door Sensor",  # 49 as hex
        0x91: "Key Fob",  # 145 as hex, as serial on fob corpse
        0x21: "Motion Sensor",  # 33 as hex
    }

    def get_sensors_status(self) -> dict:
        """Return the state of the sensors."""
        packet = bytearray(16)
        packet[0] = 0x06  # 0x06 - get sensors info, 0x07 - probably add sensors
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        if not payload:
            return None
        count = payload[0x4]
        sensor_data = payload[0x6:]
        sensors = [
            bytearray(sensor_data[i * 83 : (i + 1) * 83])
            for i in range(len(sensor_data) // 83)
        ]
        return {
            "count": count,
            "sensors": [
                {
                    "status": sensor[0],
                    "name": sensor[4:26].decode().strip("\x00"),
                    "type": self._SENSORS_TYPES.get(sensor[3], "Unknown"),
                    "order": sensor[1],
                    "serial": sensor[26:30].hex(),
                }
                for sensor in sensors
                if any(sensor[26:30])
            ],
        }
