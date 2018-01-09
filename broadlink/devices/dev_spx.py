from device import device

class sp1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "SP1"

  def set_power(self, state):
    packet = bytearray(4)
    packet[0] = state
    self.send_packet(0x66, packet)


class sp2(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "SP2"

  def set_power(self, state):
    """Sets the power state of the smart plug."""
    packet = bytearray(16)
    packet[0] = 2
    packet[4] = 1 if state else 0
    self.send_packet(0x6a, packet)

  def check_power(self):
    """Returns the power state of the smart plug."""
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        state = bool(payload[0x4])
      else:
        state = bool(ord(payload[0x4]))
      return state

  def get_energy(self):
    packet = bytearray([8, 0, 254, 1, 5, 1, 0, 0, 0, 45])
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      energy = int(hex(ord(payload[7]) * 256 + ord(payload[6]))[2:]) + int(hex(ord(payload[5]))[2:])/100.0
      return energy
