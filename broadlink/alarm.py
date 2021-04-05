"""Support for alarm kits."""
from . import exceptions as e
from .device import Device


class S1C(Device):
    """Controls a Broadlink S1C."""

    TYPE = "S1C"

    _SENSORS_TYPES = {
        0x31: "Door Sensor",
        0x91: "Key Fob",
        0x21: "Motion Sensor",
    }

    def get_sensors_status(self) -> dict:
        """Return the state of the sensors."""
        packet = bytearray(16)
        packet[0] = 0x06
        response = self.send_packet(0x6A, packet)
        e.check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
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
