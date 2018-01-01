from device import device

class dooya(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "Dooya DT360E"

  def _send(self, magic1, magic2):
    packet = bytearray(16)
    packet[0] = 0x09
    packet[2] = 0xbb
    packet[3] = magic1
    packet[4] = magic2
    packet[9] = 0xfa
    packet[10] = 0x44
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      return ord(payload[4])

  def open(self):
    return self._send(0x01, 0x00)

  def close(self):
    return self._send(0x02, 0x00)

  def stop(self):
    return self._send(0x03, 0x00)

  def get_percentage(self):
    return self._send(0x06, 0x5d)

  def set_percentage_and_wait(self, new_percentage):
    current = self.get_percentage()
    if current > new_percentage:
      self.close()
      while current is not None and current > new_percentage:
        time.sleep(0.2)
        current = self.get_percentage()

    elif current < new_percentage:
      self.open()
      while current is not None and current < new_percentage:
        time.sleep(0.2)
        current = self.get_percentage()
    self.stop()
