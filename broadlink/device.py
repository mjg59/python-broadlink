"""Support for Broadlink devices."""
import logging
import socket
import threading
import random
import time
import typing as t

from . import exceptions as e
from . import protocol as p

_LOGGER = logging.getLogger(__name__)


class device:
    """Controls a Broadlink device."""

    TYPE = "Unknown"

    BlockSizeHandler = p.BlockSizeHandler
    EncryptionHandler = p.EncryptionHandler

    def __init__(
        self,
        host: t.Tuple[str, int],
        mac: t.Union[bytes, str] = None,
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
        self.type = self.TYPE  # For backwards compatibility.

        self._count = random.randint(0x8000, 0xFFFF)
        self._bs_hdlr = self.BlockSizeHandler()
        self._enc_hdlr = self.EncryptionHandler()
        self._lock = threading.Lock()

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

    def ping(self) -> None:
        """Send a Ping Response packet to the device.

        This packet feeds the watchdog timer of firmwares >= v53.
        Useful to prevent reboots when the cloud cannot be reached.
        It must be sent every 2 minutes in such cases.
        """
        self.send_packet(0x01)

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

    def auth(self) -> bool:
        """Authenticate to the device.

        Send a Client Key Exchange packet to the device and update
        device control ID and AES key with the response.
        """
        with self._lock:
            self._enc_hdlr.reset()
            payload = bytearray(0x50)
            payload[0x04:0x13] = [0x31] * 15
            payload[0x1E] = 0x01
            payload[0x2D] = 0x01
            payload[0x30:0x36] = "Test 1".encode()
            resp, err = self.send_packet(0x65, payload)
            e.check_error(err)

            conn_id = int.from_bytes(resp[:0x4], "little")
            key = resp[0x04:0x14]
            self._enc_hdlr.update(conn_id, key)
            return True

    def send_cmd(
        self,
        command: int,
        data: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a command to the device."""
        data = bytes(data)
        payload = command.to_bytes(4, "little") + data
        payload = self._bs_hdlr.pack(payload)
        resp, err = self.send_packet(0x6A, payload, retry_intvl=retry_intvl)
        e.check_error(err)
        return self._bs_hdlr.unpack(resp)[0x4:]

    def set_name(self, name: str) -> None:
        """Set device name."""
        name_b = name.encode()
        packet = bytearray(0x50)
        packet[0x04:0x04+len(name_b)] = name_b
        packet[0x43] = bool(self.is_locked)
        err = self.send_packet(0x6A, packet)[1]
        e.check_error(err)
        self.name = name

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        name_b = self.name.encode()
        packet = bytearray(0x50)
        packet[0x04:0x04+len(name_b)] = name_b
        packet[0x43] = bool(state)
        err = self.send_packet(0x6A, packet)[1]
        e.check_error(err)
        self.is_locked = bool(state)

    def update(self) -> None:
        """Update device name and lock status."""
        resp = self.send_cmd(0x01)
        self.name = resp[0x48:].split(b"\x00")[0].decode()
        self.is_locked = bool(resp[0x87])

    def get_fwversion(self) -> int:
        """Get firmware version."""
        packet = bytearray(0x10)
        packet[0] = 0x68
        resp, err = self.send_packet(0x6A, packet)
        e.check_error(err)
        return resp[0x04] | resp[0x05] << 8

    def get_type(self) -> str:
        """Return device type."""
        return self.type

    def send_packet(
        self,
        info_type: int,
        payload: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> t.Union[bytes, None]:
        """Send a packet to the device."""
        packet = bytearray(0x30)
        payload = bytes(payload)

        # Encrypted request.
        if info_type >> 5 == 3:
            if self.mac is None or self.devtype is None:
                self.hello()

            if info_type != 0x65 and not self._enc_hdlr.id:
                self.auth()

            self._count = count = ((self._count + 1) | 0x8000) & 0xFFFF
            conn_id = bytes([0x5A, 0xA5, 0xAA, 0x55, 0x5A, 0xA5, 0xAA, 0x55])
            exp_resp_type = info_type + 900

            packet[0x00:0x08] = conn_id
            packet[0x24:0x26] = self.devtype.to_bytes(2, "little")
            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet[0x28:0x2A] = self._count.to_bytes(2, "little")
            packet[0x2A:0x30] = self.mac[::-1]
            packet.extend(self._enc_hdlr.pack(payload))

        # Public request.
        elif info_type >> 5 == 0 and not info_type % 2:
            exp_resp_type = info_type + 1
            packet[0x08:0x14] = p.Datetime.pack(p.Datetime.now())
            # packet[0x18:0x1E] = Address.pack((local_ip_addr, port))
            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet.extend(payload)

        # Ping response.
        elif info_type == 1:
            exp_resp_type = None
            packet[0x26:0x28] = info_type.to_bytes(2, "little")

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

                if exp_resp_type is None:
                    return

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

                try:
                    r_payload = self._enc_hdlr.unpack(resp[0x30:])
                except e.AuthorizationError:
                    raise
                except e.BroadlinkException as err:
                    _LOGGER.debug(err)
                    errors.append(err)
                    continue
                return r_payload, err_code


class v4(type):
    """Metaclass to build V4 classes."""

    def __new__(cls, name, bases, dct):
        """Create a new device."""
        dev_cls = super().__new__(cls, name, bases, dct)
        dev_cls.BlockSizeHandler = p.ExtBlockSizeHandler
        return dev_cls
