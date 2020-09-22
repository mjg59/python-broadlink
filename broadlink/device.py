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
        discover_ip_address: str = '255.255.255.255',
        discover_ip_port: int = 80,
) -> Generator[HelloResponse, None, None]:
    """Broadcast a hello message and yield responses."""
    cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if local_ip_address:
        cs.bind((local_ip_address, 0))
        port = cs.getsockname()[1]
    else:
        local_ip_address = "0.0.0.0"
        port = 0

    address = local_ip_address.split('.')
    starttime = time.time()

    timezone = int(time.timezone / -3600)
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
    packet[0x18] = int(address[3])
    packet[0x19] = int(address[2])
    packet[0x1a] = int(address[1])
    packet[0x1b] = int(address[0])
    packet[0x1c] = port & 0xff
    packet[0x1d] = port >> 8
    packet[0x26] = 6

    checksum = sum(packet, 0xbeaf) & 0xffff
    packet[0x20] = checksum & 0xff
    packet[0x21] = checksum >> 8

    cs.sendto(packet, (discover_ip_address, discover_ip_port))

    try:
        while (time.time() - starttime) < timeout:
            cs.settimeout(timeout - (time.time() - starttime))
            try:
                response, host = cs.recvfrom(1024)
            except socket.timeout:
                break

            devtype = response[0x34] | response[0x35] << 8
            mac = bytes(reversed(response[0x3a:0x40]))
            name = response[0x40:].split(b'\x00')[0].decode('utf-8')
            is_locked = bool(response[-1])
            yield devtype, host, mac, name, is_locked
    finally:
        cs.close()


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
        self.mac = mac.encode() if isinstance(mac, str) else mac
        self.devtype = devtype if devtype is not None else 0x272a
        self.timeout = timeout
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.is_locked = is_locked
        self.count = random.randrange(0xffff)
        self.iv = bytes(
            [0x56, 0x2e, 0x17, 0x99, 0x6d, 0x09, 0x3d, 0x28, 0xdd, 0xb3, 0xba, 0x69, 0x5a, 0x2e, 0x6f, 0x58])
        self.id = bytes(4)
        self.type = "Unknown"
        self.lock = threading.Lock()

        self.aes = None
        key = bytes(
            [0x09, 0x76, 0x28, 0x34, 0x3f, 0xe9, 0x9e, 0x23, 0x76, 0x5c, 0x15, 0x13, 0xac, 0xcf, 0x8b, 0x02])
        self.update_aes(key)

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
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])

        key = payload[0x04:0x14]
        if len(key) % 16 != 0:
            return False

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
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x4] | payload[0x5] << 8

    def set_name(self, name: str) -> None:
        """Set device name."""
        packet = bytearray(4)
        packet += name.encode('utf-8')
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(self.is_locked)
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        self.name = name

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        packet = bytearray(4)
        packet += self.name.encode('utf-8')
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(state)
        response = self.send_packet(0x6a, packet)
        check_error(response[0x22:0x24])
        self.is_locked = bool(state)

    def get_type(self) -> str:
        """Return device type."""
        return self.type

    def send_packet(self, command: int, payload: bytes) -> bytes:
        """Send a packet to the device."""
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
        packet[0x24] = self.devtype & 0xff
        packet[0x25] = self.devtype >> 8
        packet[0x26] = command
        packet[0x28] = self.count & 0xff
        packet[0x29] = self.count >> 8
        packet[0x2a] = self.mac[5]
        packet[0x2b] = self.mac[4]
        packet[0x2c] = self.mac[3]
        packet[0x2d] = self.mac[2]
        packet[0x2e] = self.mac[1]
        packet[0x2f] = self.mac[0]
        packet[0x30] = self.id[3]
        packet[0x31] = self.id[2]
        packet[0x32] = self.id[1]
        packet[0x33] = self.id[0]

        # pad the payload for AES encryption
        padding = (16 - len(payload)) % 16
        if padding:
            payload = bytearray(payload)
            payload += bytearray(padding)

        checksum = sum(payload, 0xbeaf) & 0xffff
        packet[0x34] = checksum & 0xff
        packet[0x35] = checksum >> 8

        payload = self.encrypt(payload)
        for i in range(len(payload)):
            packet.append(payload[i])

        checksum = sum(packet, 0xbeaf) & 0xffff
        packet[0x20] = checksum & 0xff
        packet[0x21] = checksum >> 8

        start_time = time.time()
        with self.lock:
            cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            while True:
                try:
                    cs.sendto(packet, self.host)
                    cs.settimeout(1)
                    resp, _ = cs.recvfrom(2048)
                    break
                except socket.timeout:
                    if (time.time() - start_time) > self.timeout:
                        cs.close()
                        raise exception(-4000)  # Network timeout.
            cs.close()

        if len(resp) < 0x30:
            raise exception(-4007)  # Length error.

        checksum = resp[0x20] | (resp[0x21] << 8)
        if sum(resp, 0xbeaf) - sum(resp[0x20:0x22]) & 0xffff != checksum:
            raise exception(-4008)  # Checksum error.

        return resp
