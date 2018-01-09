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

from device_types import gendevice

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
  packet[0x26] = 6  # Hello command
  
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
