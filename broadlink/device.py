import time
import random
import socket
import sys
import threading
import codecs

from datetime import datetime
try:
    from Crypto.Cipher import AES
except ImportError as e:
    import pyaes


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
    print "Auth"
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

    print "Dump payload not encrypted..."
    print dump_hex_buffer(packet)

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

    print "Dump response..."
    print dump_hex_buffer(response[0])

    return bytearray(response[0])
