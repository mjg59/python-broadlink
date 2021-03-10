"""Support for alarm kits."""
from .device import BroadlinkDevice, v2_core


@v2_core
class S1C(BroadlinkDevice):
    """Controls a Broadlink S1C."""

    _TYPE = "S1C"

    _SENSORS_TYPES = {
        0x31: "Door Sensor",
        0x91: "Key Fob",
        0x21: "Motion Sensor",
    }

    def get_sensors_status(self) -> dict:
        """Return the state of the sensors."""
        resp = self.send_cmd(0x06)
        count = resp[0x00]
        sensor_data = resp[0x02:]
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
