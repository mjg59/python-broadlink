from device import device

class a1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "A1"

  def check_sensors(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      data = {}
      payload = self.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        data['temperature'] = (payload[0x4] * 10 + payload[0x5]) / 10.0
        data['humidity'] = (payload[0x6] * 10 + payload[0x7]) / 10.0
        light = payload[0x8]
        air_quality = payload[0x0a]
        noise = payload[0xc]
      else:
        data['temperature'] = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
        data['humidity'] = (ord(payload[0x6]) * 10 + ord(payload[0x7])) / 10.0
        light = ord(payload[0x8])
        air_quality = ord(payload[0x0a])
        noise = ord(payload[0xc])
      if light == 0:
        data['light'] = 'dark'
      elif light == 1:
        data['light'] = 'dim'
      elif light == 2:
        data['light'] = 'normal'
      elif light == 3:
        data['light'] = 'bright'
      else:
        data['light'] = 'unknown'
      if air_quality == 0:
        data['air_quality'] = 'excellent'
      elif air_quality == 1:
        data['air_quality'] = 'good'
      elif air_quality == 2:
        data['air_quality'] = 'normal'
      elif air_quality == 3:
        data['air_quality'] = 'bad'
      else:
        data['air_quality'] = 'unknown'
      if noise == 0:
        data['noise'] = 'quiet'
      elif noise == 1:
        data['noise'] = 'normal'
      elif noise == 2:
        data['noise'] = 'noisy'
      else:
        data['noise'] = 'unknown'
      return data

  def check_sensors_raw(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      data = {}
      payload = self.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        data['temperature'] = (payload[0x4] * 10 + payload[0x5]) / 10.0
        data['humidity'] = (payload[0x6] * 10 + payload[0x7]) / 10.0
        data['light'] = payload[0x8]
        data['air_quality'] = payload[0x0a]
        data['noise'] = payload[0xc]
      else:
        data['temperature'] = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
        data['humidity'] = (ord(payload[0x6]) * 10 + ord(payload[0x7])) / 10.0
        data['light'] = ord(payload[0x8])
        data['air_quality'] = ord(payload[0x0a])
        data['noise'] = ord(payload[0xc])
      return data
