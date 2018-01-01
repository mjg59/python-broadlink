from device import device

class S1C(device):
  """
  Its VERY VERY VERY DIRTY IMPLEMENTATION of S1C
  """
  def __init__(self, *a, **kw):
    device.__init__(self, *a, **kw)
    self.type = 'S1C'

  def get_sensors_status(self):
    packet = bytearray(16)
    packet[0] = 0x06  # 0x06 - get sensors info, 0x07 - probably add sensors
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))

      payload = aes.decrypt(bytes(response[0x38:]))
      if payload:
        head = payload[:4]
        count = payload[0x4] #need to fix for python 2.x
        sensors = payload[0x6:]
        sensors_a = [bytearray(sensors[i * 83:(i + 1) * 83]) for i in range(len(sensors) // 83)]

        sens_res = []
        for sens in sensors_a:
          status = ord(chr(sens[0]))
          _name = str(bytes(sens[4:26]).decode())
          _order = ord(chr(sens[1]))
          _type = ord(chr(sens[3]))
          _serial = bytes(codecs.encode(sens[26:30],"hex")).decode()

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

