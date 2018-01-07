from device import device

class rm(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "RM2"

  def check_data(self):
    packet = bytearray(16)
    packet[0] = 4
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      return payload[0x04:]

  def send_data(self, data):
    packet = bytearray([0x02, 0x00, 0x00, 0x00])
    packet += data
    self.send_packet(0x6a, packet)

  def enter_learning(self):
    print "creating buffer"
    packet = bytearray(16)
    packet[0] = 3
    print "Dump learning packet to send..."
    print dump_hex_buffer(packet)
    self.send_packet(0x6a, packet)

  def check_temperature(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        temp = (payload[0x4] * 10 + payload[0x5]) / 10.0
      else:
        temp = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
      return temp

# For legay compatibility - don't use this
class rm2(rm):
  def __init__ (self):
    device.__init__(self, None, None)

  def discover(self):
    dev = discover()
    self.host = dev.host
    self.mac = dev.mac


S1C_SENSORS_TYPES = {
    0x31: 'Door Sensor',  # 49 as hex
    0x91: 'Key Fob',  # 145 as hex, as serial on fob corpse
    0x21: 'Motion Sensor'  # 33 as hex
}