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
import codecs

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
  elif devtype == 0x947a or devtype == 0x9479: # SP3S
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
  elif devtype == 0x4EB5 or devtype == 0x4EF7: # MP1: 0x4eb5, honyar oem mp1: 0x4ef7
    return mp1(host=host, mac=mac)
  elif devtype == 0x4EAD: # Hysen controller
    return hysen(host=host, mac=mac)
  elif devtype == 0x2722: # S1 (SmartOne Alarm Kit)
    return S1C(host=host, mac=mac)
  elif devtype == 0x4E4D: # Dooya DT360E (DOOYA_CURTAIN_V2)
    return dooya(host=host, mac=mac)
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
          response = self.cs.recvfrom(2048)
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

  def get_energy(self):
    packet = bytearray([8, 0, 254, 1, 5, 1, 0, 0, 0, 45])
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      payload = self.decrypt(bytes(response[0x38:]))
      energy = int(hex(ord(payload[7]) * 256 + ord(payload[6]))[2:]) + int(hex(ord(payload[5]))[2:])/100.0
      return energy


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


#
# Hysen heating controller
# 
class hysen(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "Hysen heating controller"

  # Send a request
  # input_payload should be a bytearray, usually 6 bytes, e.g. bytearray([0x01,0x06,0x00,0x02,0x10,0x00]) 
  # Returns decrypted payload
  # New behaviour: raises a ValueError if the device response indicates an error
  # Note the function will prepend signature and append CRC
  def send_request(self,input_payload):
    
    from PyCRC.CRC16 import CRC16
    crc = CRC16(modbus_flag=True).calculate(bytes(input_payload))

    # first byte is length, +2 for CRC16
    request_payload = bytearray([len(input_payload) + 2,0x00])
    request_payload.extend(input_payload)
    
    # append CRC
    request_payload.append(crc & 0xFF)
    request_payload.append((crc >> 8) & 0xFF)

    # send to device
    response = self.send_packet(0x6a, request_payload)

    # check for error
    err = response[0x22] | (response[0x23] << 8)
    if err: 
      raise ValueError('broadlink_response_error',err)
    
    response_payload = bytearray(self.decrypt(bytes(response[0x38:])))

    # experimental check on CRC in response (first 2 bytes are len, and trailing bytes are crc)
    response_payload_len = response_payload[0]
    if response_payload_len + 2 > len(response_payload):
      raise ValueError('hysen_response_error','first byte of response is not length')
    crc = CRC16(modbus_flag=True).calculate(bytes(response_payload[2:response_payload_len]))
    if (response_payload[response_payload_len] == crc & 0xFF) and (response_payload[response_payload_len+1] == (crc >> 8) & 0xFF):
      return response_payload[2:response_payload_len]
    else: 
      raise ValueError('hysen_response_error','CRC check on response failed')
      

  # Get current room temperature in degrees celsius (assume can get Fahrenheit with other params)
  def get_temp(self):
    payload = self.send_request(bytearray([0x01,0x03,0x00,0x00,0x00,0x08]))
    return payload[0x05] / 2.0

  # Get current external temperature in degrees celsius
  def get_external_temp(self):
    payload = self.send_request(bytearray([0x01,0x03,0x00,0x00,0x00,0x08]))
    return payload[18] / 2.0

  # Get full status (including timer schedule)
  def get_full_status(self):
    payload = self.send_request(bytearray([0x01,0x03,0x00,0x00,0x00,0x16]))    
    data = {}
    data['remote_lock'] =  payload[3] & 1
    data['power'] =  payload[4] & 1
    data['active'] =  (payload[4] >> 4) & 1
    data['temp_manual'] =  (payload[4] >> 6) & 1
    data['room_temp'] =  (payload[5] & 255)/2.0
    data['thermostat_temp'] =  (payload[6] & 255)/2.0
    data['auto_mode'] =  payload[7] & 15 # same way round as input, duh
    data['loop_mode'] =  (payload[7] >> 4) & 15
    data['sensor'] = payload[8]
    data['osv'] = payload[9]
    data['dif'] = payload[10]
    data['svh'] = payload[11]
    data['svl'] = payload[12]
    data['room_temp_adj'] = ((payload[13] << 8) + payload[14])/2.0
    if data['room_temp_adj'] > 32767:
      data['room_temp_adj'] = 32767 - data['room_temp_adj']
    data['fre'] = payload[15]
    data['poweron'] = payload[16]
    data['unknown'] = payload[17]
    data['external_temp'] = (payload[18] & 255)/2.0
    data['hour'] =  payload[19]
    data['min'] =  payload[20]
    data['sec'] =  payload[21]
    data['dayofweek'] =  payload[22]
    
    weekday = []
    for i in range(0, 6):
      weekday.append({'start_hour':payload[2*i + 23], 'start_minute':payload[2*i + 24],'temp':payload[i + 39]/2.0})
    
    data['weekday'] = weekday
    weekend = []
    for i in range(6, 8):
      weekend.append({'start_hour':payload[2*i + 23], 'start_minute':payload[2*i + 24],'temp':payload[i + 39]/2.0})

    data['weekend'] = weekend
    return data

  # Change controller mode
  # auto_mode = 1 for auto (scheduled/timed) mode, 0 for manual mode.
  # Manual mode will activate last used temperature.  In typical usage call set_temp to activate manual control and set temp.
  # loop_mode refers to index in [ "12345,67", "123456,7", "1234567" ]
  # E.g. loop_mode = 0 ("12345,67") means Saturday and Sunday follow the "weekend" schedule
  # loop_mode = 2 ("1234567") means every day (including Saturday and Sunday) follows the "weekday" schedule
  # The sensor command is currently experimental
  def set_mode(self, auto_mode, loop_mode,sensor=0):
    mode_byte = ( (loop_mode + 1) << 4) + auto_mode
    # print 'Mode byte: 0x'+ format(mode_byte, '02x')
    self.send_request(bytearray([0x01,0x06,0x00,0x02,mode_byte,sensor]))

  def set_advanced(self, loop_mode, sensor, osv, dif, svh, svl, adj, fre, poweron):
    input_payload = bytearray([0x01,0x10,0x00,0x02,0x00,0x05,0x0a, loop_mode, sensor, osv, dif, svh, svl, (int(adj*2)>>8 & 0xff), (int(adj*2) & 0xff), fre, poweron])
    self.send_request(input_payload)

  # For backwards compatibility only
  def switch_to_auto(self):
    self.set_mode(auto_mode=1, loop_mode=0)
  
  def switch_to_manual(self):
    self.set_mode(auto_mode=0, loop_mode=0)

  # Set temperature for manual mode (also activates manual mode if currently in automatic)
  def set_temp(self, temp):
    self.send_request(bytearray([0x01,0x06,0x00,0x01,0x00,int(temp * 2)]) )

  # Set device on(1) or off(0), does not deactivate Wifi connectivity
  def set_power(self, power=1, remote_lock=0):
    self.send_request(bytearray([0x01,0x06,0x00,0x00,remote_lock,power]) )

  # set time on device
  # n.b. day=1 is Monday, ..., day=7 is Sunday
  def set_time(self, hour, minute, second, day):
    self.send_request(bytearray([0x01,0x10,0x00,0x08,0x00,0x02,0x04, hour, minute, second, day ]))

  # Set timer schedule
  # Format is the same as you get from get_full_status.
  # weekday is a list (ordered) of 6 dicts like:
  # {'start_hour':17, 'start_minute':30, 'temp': 22 }
  # Each one specifies the thermostat temp that will become effective at start_hour:start_minute
  # weekend is similar but only has 2 (e.g. switch on in morning and off in afternoon)
  def set_schedule(self,weekday,weekend):
    # Begin with some magic values ...
    input_payload = bytearray([0x01,0x10,0x00,0x0a,0x00,0x0c,0x18])

    # Now simply append times/temps
    # weekday times
    for i in range(0, 6):
      input_payload.append( weekday[i]['start_hour'] )
      input_payload.append( weekday[i]['start_minute'] )

    # weekend times
    for i in range(0, 2):
      input_payload.append( weekend[i]['start_hour'] )
      input_payload.append( weekend[i]['start_minute'] )

    # weekday temperatures
    for i in range(0, 6):
      input_payload.append( int(weekday[i]['temp'] * 2) )

    # weekend temperatures
    for i in range(0, 2):
      input_payload.append( int(weekend[i]['temp'] * 2) )

    self.send_request(input_payload)

############################ End Hysen thermostat device class ############################

S1C_SENSORS_TYPES = {
    0x31: 'Door Sensor',  # 49 as hex
    0x91: 'Key Fob',  # 145 as hex, as serial on fob corpse
    0x21: 'Motion Sensor'  # 33 as hex
}


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
