from .device import device
from .exceptions import check_error


S1C_SENSORS_TYPES = {
    0x31: 'Door Sensor',  # 49 as hex
    0x91: 'Key Fob',  # 145 as hex, as serial on fob corpse
    0x21: 'Motion Sensor'  # 33 as hex
}


class S1C(device):
    """Controls a Broadlink S1C."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the controller."""
        device.__init__(self, *args, **kwargs)
        self.type = 'S1C'

    def get_sensors_status(self) -> dict:
        """Return the state of the sensors."""
        packet = bytearray(16)
        packet[0] = 0x06  # 0x06 - get sensors info, 0x07 - probably add sensors
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        if not payload:
            return None
        count = payload[0x4]
        sensors = payload[0x6:]
        sensors_a = [bytearray(sensors[i * 83:(i + 1) * 83]) for i in range(len(sensors) // 83)]

        sens_res = []
        for sens in sensors_a:
            status = sens[0]
            _name = sens[4:26].decode()
            _order = sens[1]
            _type = sens[3]
            _serial = sens[26:30].hex()

            type_str = S1C_SENSORS_TYPES.get(_type, 'Unknown')

            r = {
                'status': status,
                'name': _name.strip('\x00'),
                'type': type_str,
                'order': _order,
                'serial': _serial,
            }
            if r['serial'] != '00000000':
                sens_res.append(r)
        result = {
            'count': count,
            'sensors': sens_res
        }
        return result
