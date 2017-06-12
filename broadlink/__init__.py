#!/usr/bin/python

from datetime import datetime
try:
    from Crypto.Cipher import AES
except ImportError as e:
    import pyaes

import time
import random
import socket
import sys
import threading

def gendevice(devtype, host, mac):
  if devtype == 0: # SP1
    return sp1(host=host, mac=mac)
  if devtype == 0x2711: # SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2719 or devtype == 0x7919 or devtype == 0x271a or devtype == 0x791a: # Honeywell SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2720: # SPMini
    return sp2(host=host, mac=mac)
  elif devtype == 0x753e: # SP3
    return sp2(host=host, mac=mac)
  elif devtype == 0x2728: # SPMini2
    return sp2(host=host, mac=mac)
  elif devtype == 0x2733 or devtype == 0x273e: # OEM branded SPMini
    return sp2(host=host, mac=mac)
  elif devtype >= 0x7530 and devtype <= 0x7918: # OEM branded SPMini2
    return sp2(host=host, mac=mac)
  elif devtype == 0x2736: # SPMiniPlus
    return sp2(host=host, mac=mac)
  elif devtype == 0x2712: # RM2
    return rm(host=host, mac=mac)
  elif devtype == 0x2737: # RM Mini
    return rm(host=host, mac=mac)
  elif devtype == 0x273d: # RM Pro Phicomm
    return rm(host=host, mac=mac)
  elif devtype == 0x2783: # RM2 Home Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x277c: # RM2 Home Plus GDT
    return rm(host=host, mac=mac)
  elif devtype == 0x272a: # RM2 Pro Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x2787: # RM2 Pro Plus2
    return rm(host=host, mac=mac)
  elif devtype == 0x278b: # RM2 Pro Plus BL
    return rm(host=host, mac=mac)
  elif devtype == 0x278f: # RM Mini Shate
    return rm(host=host, mac=mac)
  elif devtype == 0x2714: # A1
    return a1(host=host, mac=mac)
  elif devtype == 0x4EB5: # MP1
    return mp1(host=host, mac=mac)
  else:
    return device(host=host, mac=mac)

def discover(timeout=None, local_ip_address=None):
  if local_ip_address is None:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(('8.8.8.8', 53))  # connecting to a UDP address doesn't send packets
      local_ip_address = s.getsockname()[0]
  address = local_ip_address.split('.')
  cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  cs.bind((local_ip_address,0))
  port = cs.getsockname()[1]
  starttime = time.time()

  devices = []

  timezone = int(time.timezone/-3600)
  packet = bytearray(0x30)

  year = datetime.now().year

  if timezone < 0:
    packet[0x08] = 0xff + timezone - 1
    packet[0x09] = 0xff
    packet[0x0a] = 0xff
    packet[0x0b] = 0xff
  else:
    packet[0x08] = timezone
    packet[0x09] = 0
    packet[0x0a] = 0
    packet[0x0b] = 0
  packet[0x0c] = year & 0xff
  packet[0x0d] = year >> 8
  packet[0x0e] = datetime.now().minute
  packet[0x0f] = datetime.now().hour
  subyear = str(year)[2:]
  packet[0x10] = int(subyear)
  packet[0x11] = datetime.now().isoweekday()
  packet[0x12] = datetime.now().day
  packet[0x13] = datetime.now().month
  packet[0x18] = int(address[0])
  packet[0x19] = int(address[1])
  packet[0x1a] = int(address[2])
  packet[0x1b] = int(address[3])
  packet[0x1c] = port & 0xff
  packet[0x1d] = port >> 8
  packet[0x26] = 6
  checksum = 0xbeaf

  for i in range(len(packet)):
      checksum += packet[i]
  checksum = checksum & 0xffff
  packet[0x20] = checksum & 0xff
  packet[0x21] = checksum >> 8

  cs.sendto(packet, ('255.255.255.255', 80))
  if timeout is None:
    response = cs.recvfrom(1024)
    responsepacket = bytearray(response[0])
    host = response[1]
    mac = responsepacket[0x3a:0x40]
    devtype = responsepacket[0x34] | responsepacket[0x35] << 8
    return gendevice(devtype, host, mac)
  else:
    while (time.time() - starttime) < timeout:
      cs.settimeout(timeout - (time.time() - starttime))
      try:
        response = cs.recvfrom(1024)
      except socket.timeout:
        return devices
      responsepacket = bytearray(response[0])
      host = response[1]
      devtype = responsepacket[0x34] | responsepacket[0x35] << 8
      mac = responsepacket[0x3a:0x40]
      dev = gendevice(devtype, host, mac)
      devices.append(dev)
    return devices


class device:
  def __init__(self, host, mac, timeout=10):
    self.host = host
    self.mac = mac
    self.timeout = timeout
    self.count = random.randrange(0xffff)
    self.key = bytearray([0x09, 0x76, 0x28, 0x34, 0x3f, 0xe9, 0x9e, 0x23, 0x76, 0x5c, 0x15, 0x13, 0xac, 0xcf, 0x8b, 0x02])
    self.iv = bytearray([0x56, 0x2e, 0x17, 0x99, 0x6d, 0x09, 0x3d, 0x28, 0xdd, 0xb3, 0xba, 0x69, 0x5a, 0x2e, 0x6f, 0x58])
    self.id = bytearray([0, 0, 0, 0])
    self.cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    self.cs.bind(('',0))
    self.type = "Unknown"
    self.lock = threading.Lock()

    if 'pyaes' in sys.modules:
        self.encrypt = self.encrypt_pyaes
        self.decrypt = self.decrypt_pyaes
    else:
        self.encrypt = self.encrypt_pycrypto
        self.decrypt = self.decrypt_pycrypto

  def encrypt_pyaes(self, payload):
    aes = pyaes.AESModeOfOperationCBC(self.key, iv = bytes(self.iv))
    return "".join([aes.encrypt(bytes(payload[i:i+16])) for i in range(0, len(payload), 16)])

  def decrypt_pyaes(self, payload):
    aes = pyaes.AESModeOfOperationCBC(self.key, iv = bytes(self.iv))
    return "".join([aes.decrypt(bytes(payload[i:i+16])) for i in range(0, len(payload), 16)])

  def encrypt_pycrypto(self, payload):
    aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
    return aes.encrypt(bytes(payload))

  def decrypt_pycrypto(self, payload):
    aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
    return aes.decrypt(bytes(payload))

  def auth(self):
    payload = bytearray(0x50)
    payload[0x04] = 0x31
    payload[0x05] = 0x31
    payload[0x06] = 0x31
    payload[0x07] = 0x31
    payload[0x08] = 0x31
    payload[0x09] = 0x31
    payload[0x0a] = 0x31
    payload[0x0b] = 0x31
    payload[0x0c] = 0x31
    payload[0x0d] = 0x31
    payload[0x0e] = 0x31
    payload[0x0f] = 0x31
    payload[0x10] = 0x31
    payload[0x11] = 0x31
    payload[0x12] = 0x31
    payload[0x1e] = 0x01
    payload[0x2d] = 0x01
    payload[0x30] = ord('T')
    payload[0x31] = ord('e')
    payload[0x32] = ord('s')
    payload[0x33] = ord('t')
    payload[0x34] = ord(' ')
    payload[0x35] = ord(' ')
    payload[0x36] = ord('1')

    response = self.send_packet(0x65, payload)

    payload = self.decrypt(response[0x38:])

    if not payload:
     return False

    key = payload[0x04:0x14]
    if len(key) % 16 != 0:
     return False

    self.id = payload[0x00:0x04]
    self.key = key
    return True

  def get_type(self):
    return self.type

  def send_packet(self, command, payload):
    self.count = (self.count + 1) & 0xffff
    packet = bytearray(0x38)
    packet[0x00] = 0x5a
    packet[0x01] = 0xa5
    packet[0x02] = 0xaa
    packet[0x03] = 0x55
    packet[0x04] = 0x5a
    packet[0x05] = 0xa5
    packet[0x06] = 0xaa
    packet[0x07] = 0x55
    packet[0x24] = 0x2a
    packet[0x25] = 0x27
    packet[0x26] = command
    packet[0x28] = self.count & 0xff
    packet[0x29] = self.count >> 8
    packet[0x2a] = self.mac[0]
    packet[0x2b] = self.mac[1]
    packet[0x2c] = self.mac[2]
    packet[0x2d] = self.mac[3]
    packet[0x2e] = self.mac[4]
    packet[0x2f] = self.mac[5]
    packet[0x30] = self.id[0]
    packet[0x31] = self.id[1]
    packet[0x32] = self.id[2]
    packet[0x33] = self.id[3]

    # pad the payload for AES encryption
    if len(payload)>0:
      numpad=(len(payload)//16+1)*16
      payload=payload.ljust(numpad,b"\x00")

    checksum = 0xbeaf
    for i in range(len(payload)):
      checksum += payload[i]
      checksum = checksum & 0xffff

    payload = self.encrypt(payload)

    packet[0x34] = checksum & 0xff
    packet[0x35] = checksum >> 8

    for i in range(len(payload)):
      packet.append(payload[i])

    checksum = 0xbeaf
    for i in range(len(packet)):
      checksum += packet[i]
      checksum = checksum & 0xffff
    packet[0x20] = checksum & 0xff
    packet[0x21] = checksum >> 8

    starttime = time.time()
    with self.lock:
      while True:
        try:
          self.cs.sendto(packet, self.host)
          self.cs.settimeout(1)
          response = self.cs.recvfrom(1024)
          break
        except socket.timeout:
          if (time.time() - starttime) > self.timeout:
            raise
    return bytearray(response[0])


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
    packet = bytearray(16)
    packet[0] = 3
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

# Setup a new Broadlink device via AP Mode. Review the README to see how to enter AP Mode.
# Only tested with Broadlink RM3 Mini (Blackbean)
def setup(ssid, password, security_mode):
  # Security mode options are (0 - none, 1 = WEP, 2 = WPA1, 3 = WPA2, 4 = WPA1/2)
  payload = bytearray(0x88)
  payload[0x26] = 0x14  # This seems to always be set to 14
  # Add the SSID to the payload
  ssid_start = 68
  ssid_length = 0
  for letter in ssid:
    payload[(ssid_start + ssid_length)] = ord(letter)
    ssid_length += 1
  # Add the WiFi password to the payload
  pass_start = 100
  pass_length = 0
  for letter in password:
    payload[(pass_start + pass_length)] = ord(letter)
    pass_length += 1

  payload[0x84] = ssid_length  # Character length of SSID
  payload[0x85] = pass_length  # Character length of password
  payload[0x86] = security_mode  # Type of encryption (00 - none, 01 = WEP, 02 = WPA1, 03 = WPA2, 04 = WPA1/2)

  checksum = 0xbeaf
  for i in range(len(payload)):
    checksum += payload[i]
    checksum = checksum & 0xffff

  payload[0x20] = checksum & 0xff  # Checksum 1 position
  payload[0x21] = checksum >> 8  # Checksum 2 position

  sock = socket.socket(socket.AF_INET,  # Internet
                       socket.SOCK_DGRAM)  # UDP
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(payload, ('255.255.255.255', 80))
