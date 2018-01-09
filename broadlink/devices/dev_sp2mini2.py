import time
import random
import socket

try:
    from Crypto.Cipher import AES
except ImportError as e:
    import pyaes

from datetime   import datetime
from device     import device
from dbg_utils  import dump_hex_buffer

# This in an implementation for eControl with devices of the type 'SPMini2' ID code 0x2728

PACKAGE_SIZE = 45

# indices for filling in the message buffer
IDX_TIMEZONE = 0x06
IDX_YEAR     = 0x0A
IDX_TIME_SEC = 0x0C
IDX_TIME_MIN = 0x0D
IDX_TIME_HRS = 0x0E
IDX_WEEK_NUM = 0x0F
IDX_DAY      = 0x10
IDX_MONTH    = 0x11
IDX_PORT     = 0x1A
IDX_CMD      = 0x26 

# Posible values for IDX_CMD
# Command transmission values
CMD_tx_Hello    = 0x6
CMD_tx_Discover = 0x1a
CMD_tx_Join     = 0x14
CMD_tx_Auth     = 0x65
CMD_tx_Command  = 0x6a

# Command response values
CMD_rx_Hello    = 0x7
CMD_rx_Discover = 0x1b
CMD_rx_Join     = 0x15
CMD_rx_Auth     = 0x3e9
CMD_rx_Command  = 0x3ee

class sp2mini2(device):

    def __init__ (self, host, mac):
        device.__init__(self, host, mac)
        self.type = "SP2Mini2"

    # returns a buffer of the given size, initialized to 0s
    def init_buffer(size):
        buf = bytearray(size)
    
        for i in range(0,size):
            buf[i] = 0
            
        return buf

    def build_static_msg(self, command, payload):
        self.count = (self.count + 1) & 0xffff

        packet = self.init_buffer(0x38)

        # static header
        packet[0x00] = 0x5a
        packet[0x01] = 0xa5
        packet[0x02] = 0xaa
        packet[0x03] = 0x55
        packet[0x04] = 0x5a
        packet[0x05] = 0xa5
        packet[0x06] = 0xaa
        packet[0x07] = 0x55

        # device Id
        packet[0x24] = 0x28
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

        return packet

    # overwritting the method adapted to SP2Mini2
    def send_packet(self, command, payload):
        packet = self.build_static_msg(command, payload)
        starttime = time.time()

        print "Dump buffer to send..."
        print dump_hex_buffer(packet)

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

    def enter_learning(self):
        print "creating buffer"
        packet = bytearray(16)
        packet[0] = 3
        print "Dump learning packet to send..."
        print dump_hex_buffer(packet)
        self.send_packet(0x6a, packet)

    def set_power(self, state):
        """Sets the power state of the smart plug."""
        packet = self.init_buffer(16)
        packet[0] = 2 # Set command
        packet[4] = 1 if state else 0
        response = self.send_packet(CMD_tx_Command, packet)
        print "Dump buffer received..."
        print dump_hex_buffer(response)

    def check_power(self):
        """Returns the power state of the smart plug."""
        packet = self.init_buffer(16)
        packet[0] = 1 # Get Command
        response = self.send_packet(CMD_tx_Command, packet)
        err = response[0x22] | (response[0x23] << 8)
        state = -1

        if err == 0:
            print "Received correct response"
            payload = self.decrypt(bytes(response[0x38:]))
            if type(payload[0x4]) == int:
                state = bool(payload[0x4])
            else:
                state = bool(ord(payload[0x4]))
            print "state %d" % state
        return state

