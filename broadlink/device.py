"""Support for Broadlink devices."""
import logging
import socket
import threading
import random
import time
from typing import Generator, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import exceptions as e
from .protocol import Datetime

_LOGGER = logging.getLogger(__name__)

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
    packet[0x08:0x14] = Datetime.pack(Datetime.now())
    packet[0x18:0x1C] = socket.inet_aton(local_ip_address)[::-1]
    packet[0x1C:0x1E] = port.to_bytes(2, "little")
    packet[0x26] = 6

    checksum = sum(packet, 0xBEAF) & 0xFFFF
    packet[0x20:0x22] = checksum.to_bytes(2, "little")

    start_time = time.time()
    discovered = []

    try:
        while (time.time() - start_time) < timeout:
            time_left = timeout - (time.time() - start_time)
            conn.settimeout(min(1, time_left))
            conn.sendto(packet, (discover_ip_address, discover_ip_port))

            while True:
                try:
                    resp, host = conn.recvfrom(1024)
                except socket.timeout:
                    break

                devtype = resp[0x34] | resp[0x35] << 8
                mac = resp[0x3A:0x40][::-1]

                if (host, mac, devtype) in discovered:
                    continue
                discovered.append((host, mac, devtype))

                name = resp[0x40:].split(b"\x00")[0].decode()
                is_locked = bool(resp[-1])
                yield devtype, host, mac, name, is_locked
    finally:
        conn.close()


def ping(address: str, port: int = 80) -> None:
    """Send a ping packet to an address.

    This packet feeds the watchdog timer of firmwares >= v53.
    Useful to prevent reboots when the cloud cannot be reached.
    It must be sent every 2 minutes in such cases.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        packet = bytearray(0x30)
        packet[0x26] = 1
        conn.sendto(packet, (address, port))


class device:
    """Controls a Broadlink device."""

    TYPE = "Unknown"

    __INITIAL_KEY = "097628343fe99e23765c1513accf8b02"
    __INITIAL_VECT = "562e17996d093d28ddb3ba695a2e6f58"

    def __init__(
        self,
        host: Tuple[str, int],
        mac: Union[bytes, str] = None,
        devtype: int = None,
        timeout: int = 10,
        name: str = None,
        model: str = None,
        manufacturer: str = None,
        is_locked: bool = None,
    ) -> None:
        """Initialize the controller."""
        self.host = host
        self.mac = bytes.fromhex(mac) if isinstance(mac, str) else mac
        self.devtype = devtype
        self.timeout = timeout
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.is_locked = is_locked

        self.count = random.randint(0x8000, 0xFFFF)
        self.id = 0
        self.aes = None
        self.update_aes(bytes.fromhex(self.__INITIAL_KEY))
        self.lock = threading.Lock()
        self.type = self.TYPE  # For backwards compatibility.

    def __repr__(self) -> str:
        """Return a formal representation of the device."""
        return "%s.%s(%s, mac=%r, devtype=%r, timeout=%r, name=%r, model=%r, manufacturer=%r, is_locked=%r)" % (
            self.__class__.__module__,
            self.__class__.__qualname__,
            self.host,
            self.mac,
            self.devtype,
            self.timeout,
            self.name,
            self.model,
            self.manufacturer,
            self.is_locked,
        )

    def __str__(self) -> str:
        """Return a readable representation of the device."""
        model = []
        if self.manufacturer is not None:
            model.append(self.manufacturer)
        if self.model is not None:
            model.append(self.model)
        if self.devtype is not None:
            model.append(hex(self.devtype))
        model = " ".join(model)

        info = []
        if model:
            info.append(model)
        if self.mac is not None:
            info.append(":".join(format(x, "02x") for x in self.mac).upper())
        info.append(f"{self.host[0]}:{self.host[1]}")
        info = " / ".join(info)
        return "%s (%s)" % (self.name or "Unknown", info)

    def update_aes(self, key: bytes) -> None:
        """Update AES."""
        self.aes = Cipher(
            algorithms.AES(bytes(key)),
            modes.CBC(bytes.fromhex(self.__INITIAL_VECT)),
            backend=default_backend(),
        )

    def encrypt(self, payload: bytes) -> bytes:
        """Encrypt the payload."""
        encryptor = self.aes.encryptor()
        return encryptor.update(bytes(payload)) + encryptor.finalize()

    def decrypt(self, payload: bytes) -> bytes:
        """Decrypt the payload."""
        decryptor = self.aes.decryptor()
        return decryptor.update(bytes(payload)) + decryptor.finalize()

    def auth(self) -> bool:
        """Authenticate to the device.

        Send a Client Key Exchange packet to the device and update
        device control ID and AES key with the response.
        """
        with self.lock:
            self.id = 0
            self.update_aes(bytes.fromhex(self.__INITIAL_KEY))

            payload = bytearray(0x50)
            payload[0x04:0x13] = [0x31] * 15
            payload[0x1E] = 0x01
            payload[0x2D] = 0x01
            payload[0x30:0x36] = "Test 1".encode()
            resp, err = self.send_packet(0x65, payload)
            if err:
                raise e.exception(err)

            key = resp[0x04:0x14]
            self.id = int.from_bytes(resp[:0x4], "little")
            self.update_aes(key)
            return True

    def hello(self) -> None:
        """Start communicating with the device.

        Send a Client Hello packet to the device and update product ID,
        MAC address, model, manufacturer, name and lock status with the
        response.
        """
        resp = self.send_packet(0x06)[0]
        devtype = int.from_bytes(resp[0x04:0x06], "little")
        mac = resp[0x0A:0x10][::-1]

        if self.mac is None:
            self.mac = mac
        elif self.mac != mac:
            raise e.DataValidationError(
                -2040,
                "Device information is not intact",
                "Invalid MAC address",
                f"Expected {self.mac} and received {mac}",
            )

        if self.devtype is None:
            self.devtype = devtype
        elif self.devtype != devtype:
            raise e.DataValidationError(
                -2040,
                "Device information is not intact",
                "Invalid product ID",
                f"Expected {self.devtype} and received {devtype}",
            )

        if self.model is None or self.manufacturer is None:
            from . import SUPPORTED_TYPES

            try:
                self.model, self.manufacturer = SUPPORTED_TYPES[devtype][1:3]
            except KeyError:
                pass

        self.name = resp[0x10:].split(b"\x00")[0].decode()
        self.is_locked = bool(resp[-1])

    def ping(self) -> None:
        """Ping the device.

        This packet feeds the watchdog timer of firmwares >= v53.
        Useful to prevent reboots when the cloud cannot be reached.
        It must be sent every 2 minutes in such cases.
        """
        ping(self.host[0], port=self.host[1])

    def get_fwversion(self) -> int:
        """Get firmware version."""
        packet = bytearray([0x68])
        resp, err = self.send_packet(0x6A, packet)
        if err:
            raise e.exception(err)
        return resp[0x04] | resp[0x05] << 8

    def set_name(self, name: str) -> None:
        """Set device name."""
        packet = bytearray(4)
        packet += name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(self.is_locked)
        err = self.send_packet(0x6A, packet)[1]
        if err:
            raise e.exception(err)
        self.name = name

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        packet = bytearray(4)
        packet += self.name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(state)
        err = self.send_packet(0x6A, packet)[1]
        if err:
            raise e.exception(err)
        self.is_locked = bool(state)

    def get_type(self) -> str:
        """Return device type."""
        return self.type

    def send_packet(
        self,
        info_type: int,
        payload: bytes = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a packet to the device."""
        payload = bytes(payload)

        # Encrypted request.
        if info_type >> 5 == 3:
            if self.mac is None or self.devtype is None:
                self.hello()

            if info_type != 0x65 and not self.id:
                self.auth()

            self.count = count = ((self.count + 1) | 0x8000) & 0xFFFF
            conn_id = bytes([0x5A, 0xA5, 0xAA, 0x55, 0x5A, 0xA5, 0xAA, 0x55])
            exp_resp_type = info_type + 900

            packet = bytearray(0x38)
            packet[0x00:0x08] = conn_id
            packet[0x24:0x26] = self.devtype.to_bytes(2, "little")
            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet[0x28:0x2A] = self.count.to_bytes(2, "little")
            packet[0x2A:0x30] = self.mac[::-1]
            packet[0x30:0x34] = self.id.to_bytes(4, "little")

            p_checksum = sum(payload, 0xBEAF) & 0xFFFF
            packet[0x34:0x36] = p_checksum.to_bytes(2, "little")

            padding = bytes((16 - len(payload)) % 16)
            payload = self.encrypt(payload + padding)
            packet.extend(payload)

        # Public request.
        elif info_type >> 5 == 0 and not info_type % 2:
            exp_resp_type = info_type + 1

            packet = bytearray(0x30)
            packet[0x08:0x14] = Datetime.pack(Datetime.now())
            # packet[0x18:0x1E] = Address.pack((local_ip_addr, port))
            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet.extend(payload)

        # Encrypted response / public response.
        else:
            raise ValueError("Not supported")

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x20:0x22] = checksum.to_bytes(2, "little")
        packet = bytes(packet)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
            timeout = self.timeout
            start_time = time.time()
            should_wait = False
            errors = []

            while True:
                if should_wait:
                    time.sleep(retry_intvl)
                    should_wait = False

                time_left = timeout - (time.time() - start_time)
                if time_left < 0:
                    if not errors:
                        raise e.NetworkTimeoutError(
                            -4000,
                            "Network timeout",
                            f"No response received within {timeout}s",
                        )
                    if len(errors) == 1:
                        raise errors[0]
                    raise e.MultipleErrors(errors)

                conn.settimeout(min(retry_intvl, time_left))
                conn.sendto(packet, self.host)

                _LOGGER.debug("%s sent to %s", packet, self.host)

                try:
                    resp, src = conn.recvfrom(2048)
                except socket.timeout as err:
                    continue

                _LOGGER.debug("%s received from %s", resp, src)

                should_wait = True

                if len(resp) < 0x30:
                    err = e.DataValidationError(
                        -4007,
                        "Received data packet length error",
                        f"Expected at least 48 bytes and received {len(resp)}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                nom_checksum = int.from_bytes(resp[0x20:0x22], "little")
                real_checksum = sum(resp, 0xBEAF) - sum(resp[0x20:0x22]) & 0xFFFF

                if nom_checksum != real_checksum:
                    err = e.DataValidationError(
                        -4008,
                        "Received data packet check error",
                        f"Expected a checksum of {nom_checksum} and received {real_checksum}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                err_code = int.from_bytes(resp[0x22:0x24], "little", signed=True)
                resp_type = int.from_bytes(resp[0x26:0x28], "little")

                if resp_type != exp_resp_type:
                    err = e.DataValidationError(
                        -4009,
                        "Received data packet information type error",
                        f"Expected {exp_resp_type} and received {resp_type}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                if not any(resp[:0x08]):
                    return resp[0x30:], err_code

                if resp[:0x08] != conn_id:
                    continue

                if int.from_bytes(resp[0x28:0x2A], "little") != count:
                    continue

                if len(resp) < 0x38:
                    err = e.DataValidationError(
                        -4010,
                        "Received encrypted data packet length error",
                        f"Expected at least 56 bytes and received {len(resp)}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                payload = resp[0x38:]

                if len(payload) % 16:
                    err = e.DataValidationError(
                        -4010,
                        "Received encrypted data packet length error",
                        f"Expected a multiple of 16 and received {len(payload)}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                dev_ctrl_id = int.from_bytes(resp[0x30:0x34], "little")

                if self.id and self.id != dev_ctrl_id:
                    raise e.AuthorizationError(
                        -4012,
                        "Device control ID error",
                        f"Expected {self.id} and received {dev_ctrl_id}",
                    )

                payload = self.decrypt(payload)
                nom_p_checksum = int.from_bytes(resp[0x34:0x36], "little")
                real_p_checksum = (
                    p_checksum if err_code else sum(payload, 0xBEAF) & 0xFFFF
                )

                if nom_p_checksum != real_p_checksum:
                    err = e.DataValidationError(
                        -4011,
                        "Received encrypted data packet check error",
                        f"Expected a checksum of {nom_p_checksum} and received {real_p_checksum}",
                    )
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue

                return payload, err_code
