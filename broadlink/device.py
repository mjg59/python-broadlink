"""Support for Broadlink devices."""
import socket
import threading
import random
import time
from datetime import datetime
from typing import Generator, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .exceptions import check_error, exception

HelloResponse = Tuple[int, Tuple[str, int], str, str, bool]


def scan(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> Generator[HelloResponse, None, None]:
    """Broadcast a hello message and yield responses."""
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if local_ip_address:
        conn.bind((local_ip_address, 0))
        port = conn.getsockname()[1]
    else:
        local_ip_address = "0.0.0.0"
        port = 0

    packet = bytearray(0x30)

    timezone = int(time.timezone / -3600)
    if timezone < 0:
        packet[0x08] = 0xFF + timezone - 1
        packet[0x09] = 0xFF
        packet[0x0A] = 0xFF
        packet[0x0B] = 0xFF
    else:
        packet[0x08] = timezone
        packet[0x09] = 0
        packet[0x0A] = 0
        packet[0x0B] = 0

    year = datetime.now().year
    packet[0x0C] = year & 0xFF
    packet[0x0D] = year >> 8
    packet[0x0E] = datetime.now().minute
    packet[0x0F] = datetime.now().hour
    subyear = str(year)[2:]
    packet[0x10] = int(subyear)
    packet[0x11] = datetime.now().isoweekday()
    packet[0x12] = datetime.now().day
    packet[0x13] = datetime.now().month

    address = local_ip_address.split(".")
    packet[0x18] = int(address[3])
    packet[0x19] = int(address[2])
    packet[0x1A] = int(address[1])
    packet[0x1B] = int(address[0])
    packet[0x1C] = port & 0xFF
    packet[0x1D] = port >> 8
    packet[0x26] = 6

    checksum = sum(packet, 0xBEAF) & 0xFFFF
    packet[0x20] = checksum & 0xFF
    packet[0x21] = checksum >> 8

    starttime = time.time()
    discovered = []

    try:
        while (time.time() - starttime) < timeout:
            conn.sendto(packet, (discover_ip_address, discover_ip_port))
            conn.settimeout(1)

            while True:
                try:
                    response, host = conn.recvfrom(1024)
                except socket.timeout:
                    break

                devtype = response[0x34] | response[0x35] << 8
                mac = bytes(reversed(response[0x3A:0x40]))
                if (host, mac, devtype) in discovered:
                    continue
                discovered.append((host, mac, devtype))

                name = response[0x40:].split(b"\x00")[0].decode("utf-8")
                is_locked = bool(response[-1])
                yield devtype, host, mac, name, is_locked
    finally:
        conn.close()


class device:
    """Controls a Broadlink device."""

    def __init__(
        self,
        host: Tuple[str, int],
        mac: Union[bytes, str],
        devtype: int,
        timeout: int = 10,
        name: str = None,
        model: str = None,
        manufacturer: str = None,
        is_locked: bool = None,
    ) -> None:
        """Initialize the controller."""
        self.host = host
        self.mac = bytes.fromhex(mac) if isinstance(mac, str) else mac
        self.devtype = devtype if devtype is not None else 0x272A
        self.timeout = timeout
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.is_locked = is_locked
        self.count = random.randrange(0xFFFF)
        self.iv = bytes.fromhex("562e17996d093d28ddb3ba695a2e6f58")
        self.id = bytes(4)
        self.type = "Unknown"
        self.lock = threading.Lock()

        self.aes = None
        key = bytes.fromhex("097628343fe99e23765c1513accf8b02")
        self.update_aes(key)

    def __repr__(self):
        return "<%s: %s %s (%s) at %s:%s | %s | %s | %s>" % (
            type(self).__name__,
            self.manufacturer,
            self.model,
            hex(self.devtype),
            self.host[0],
            self.host[1],
            ":".join(format(x, "02x") for x in self.mac),
            self.name,
            "Locked" if self.is_locked else "Unlocked",
        )

    def __str__(self):
        return "%s (%s at %s)" % (
            self.name,
            self.model or hex(self.devtype),
            self.host[0],
        )

    def update_aes(self, key: bytes) -> None:
        """Update AES."""
        self.aes = Cipher(
            algorithms.AES(key), modes.CBC(self.iv), backend=default_backend()
        )

    def encrypt(self, payload: bytes) -> bytes:
        """Encrypt the payload."""
        encryptor = self.aes.encryptor()
        return encryptor.update(payload) + encryptor.finalize()

    def decrypt(self, payload: bytes) -> bytes:
        """Decrypt the payload."""
        decryptor = self.aes.decryptor()
        return decryptor.update(payload) + decryptor.finalize()

    def auth(self) -> bool:
        """Authenticate to the device."""
        payload = bytearray(0x50)
        payload[0x04] = 0x31
        payload[0x05] = 0x31
        payload[0x06] = 0x31
        payload[0x07] = 0x31
        payload[0x08] = 0x31
        payload[0x09] = 0x31
        payload[0x0A] = 0x31
        payload[0x0B] = 0x31
        payload[0x0C] = 0x31
        payload[0x0D] = 0x31
        payload[0x0E] = 0x31
        payload[0x0F] = 0x31
        payload[0x10] = 0x31
        payload[0x11] = 0x31
        payload[0x12] = 0x31
        payload[0x1E] = 0x01
        payload[0x2D] = 0x01
        payload[0x30] = ord("T")
        payload[0x31] = ord("e")
        payload[0x32] = ord("s")
        payload[0x33] = ord("t")
        payload[0x34] = ord(" ")
        payload[0x35] = ord(" ")
        payload[0x36] = ord("1")

        response = self.send_packet(0x65, payload)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])

        key = payload[0x04:0x14]
        if len(key) % 16 != 0:
            return False

        self.count = int.from_bytes(response[0x28:0x30], "little")
        self.id = payload[0x03::-1]
        self.update_aes(key)
        return True

    def hello(self, local_ip_address=None) -> bool:
        """Send a hello message to the device.

        Device information is checked before updating name and lock status.
        """
        responses = scan(
            timeout=self.timeout,
            local_ip_address=local_ip_address,
            discover_ip_address=self.host[0],
            discover_ip_port=self.host[1],
        )
        try:
            devtype, host, mac, name, is_locked = next(responses)
        except StopIteration:
            raise exception(-4000)  # Network timeout.

        if (devtype, host, mac) != (self.devtype, self.host, self.mac):
            raise exception(-2040)  # Device information is not intact.

        self.name = name
        self.is_locked = is_locked
        return True

    def get_fwversion(self) -> int:
        """Get firmware version."""
        packet = bytearray([0x68])
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x4] | payload[0x5] << 8

    def set_name(self, name: str) -> None:
        """Set device name."""
        packet = bytearray(4)
        packet += name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(self.is_locked)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        self.name = name

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        packet = bytearray(4)
        packet += self.name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(state)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        self.is_locked = bool(state)

    def get_type(self) -> str:
        """Return device type."""
        return self.type

    def send_packet(self, command: int, payload: bytes) -> bytes:
        """Send a packet to the device."""
        self.count = (self.count + 1) & 0xFFFF
        packet = bytearray(0x38)
        packet[0x00] = 0x5A
        packet[0x01] = 0xA5
        packet[0x02] = 0xAA
        packet[0x03] = 0x55
        packet[0x04] = 0x5A
        packet[0x05] = 0xA5
        packet[0x06] = 0xAA
        packet[0x07] = 0x55
        packet[0x24] = self.devtype & 0xFF
        packet[0x25] = self.devtype >> 8
        packet[0x26] = command
        packet[0x28] = self.count & 0xFF
        packet[0x29] = self.count >> 8
        packet[0x2A] = self.mac[5]
        packet[0x2B] = self.mac[4]
        packet[0x2C] = self.mac[3]
        packet[0x2D] = self.mac[2]
        packet[0x2E] = self.mac[1]
        packet[0x2F] = self.mac[0]
        packet[0x30] = self.id[3]
        packet[0x31] = self.id[2]
        packet[0x32] = self.id[1]
        packet[0x33] = self.id[0]

        # pad the payload for AES encryption
        padding = (16 - len(payload)) % 16
        if padding:
            payload = bytearray(payload)
            payload += bytearray(padding)

        checksum = sum(payload, 0xBEAF) & 0xFFFF
        packet[0x34] = checksum & 0xFF
        packet[0x35] = checksum >> 8

        payload = self.encrypt(payload)
        for i in range(len(payload)):
            packet.append(payload[i])

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x20] = checksum & 0xFF
        packet[0x21] = checksum >> 8

        start_time = time.time()
        with self.lock:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            while True:
                try:
                    conn.sendto(packet, self.host)
                    conn.settimeout(1)
                    resp, _ = conn.recvfrom(2048)
                    break
                except socket.timeout:
                    if (time.time() - start_time) > self.timeout:
                        conn.close()
                        raise exception(-4000)  # Network timeout.
            conn.close()

        if len(resp) < 0x30:
            raise exception(-4007)  # Length error.

        checksum = resp[0x20] | (resp[0x21] << 8)
        if sum(resp, 0xBEAF) - sum(resp[0x20:0x22]) & 0xFFFF != checksum:
            raise exception(-4008)  # Checksum error.

        return resp
