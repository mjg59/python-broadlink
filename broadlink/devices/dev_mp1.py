from device import device

class mp1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "MP1"

  def set_power_mask(self, sid_mask, state):
    """Sets the power state of the smart power strip."""

    packet = bytearray(16)
    packet[0x00] = 0x0d
    packet[0x02] = 0xa5
    packet[0x03] = 0xa5
    packet[0x04] = 0x5a
    packet[0x05] = 0x5a
    packet[0x06] = 0xb2 + ((sid_mask<<1) if state else sid_mask)
    packet[0x07] = 0xc0
    packet[0x08] = 0x02
    packet[0x0a] = 0x03
    packet[0x0d] = sid_mask
    packet[0x0e] = sid_mask if state else 0

    response = self.send_packet(0x6a, packet)

    err = response[0x22] | (response[0x23] << 8)

  def set_power(self, sid, state):
    """Sets the power state of the smart power strip."""
    sid_mask = 0x01 << (sid - 1)
    return self.set_power_mask(sid_mask, state)

  def check_power_raw(self):
    """Returns the power state of the smart power strip in raw format."""
    packet = bytearray(16)
    packet[0x00] = 0x0a
    packet[0x02] = 0xa5
    packet[0x03] = 0xa5
    packet[0x04] = 0x5a
    packet[0x05] = 0x5a
    packet[0x06] = 0xae
    packet[0x07] = 0xc0
    packet[0x08] = 0x01

    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        state = payload[0x0e]
      else:
        state = ord(payload[0x0e])
      return state

  def check_power(self):
    """Returns the power state of the smart power strip."""
    state = self.check_power_raw()
    data = {}
    data['s1'] = bool(state & 0x01)
    data['s2'] = bool(state & 0x02)
    data['s3'] = bool(state & 0x04)
    data['s4'] = bool(state & 0x08)
    return data
