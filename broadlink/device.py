"""Support for Broadlink devices."""
import abc
import json
import logging
import platform
import random
import socket
import threading
import time
import typing as t

from . import exceptions as e
from . import protocol as p
from .common import JSONCommand

_LOGGER = logging.getLogger(__name__)


class DeviceCore(abc.ABC):
    """Base class common to all device cores."""

    BlockSizeHandler = p.BlockSizeHandler
    EncryptionHandler = p.EncryptionHandler

    def __init__(self, device) -> None:
        """Initialize the core."""
        self._device = device
        self._pkt_no = random.randint(0x8000, 0xFFFF)
        self._bsize_hdlr = self.BlockSizeHandler()
        self._enc_hdlr = self.EncryptionHandler(device)
        self._lock = threading.Lock()

    def send_packet(
        self,
        info_type: int,
        payload: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> t.Union[bytes, None]:
        """Send a packet to the device."""
        device = self._device
        payload = bytes(payload)
        packet = bytearray(0x30)

        # Encrypted request.
        if info_type >> 5 == 3:
            self._pkt_no = exp_pkt_no = ((self._pkt_no + 1) | 0x8000) & 0xFFFF
            exp_resp_type = info_type + 900

            packet[0x00:0x08] = [0x5A, 0xA5, 0xAA, 0x55, 0x5A, 0xA5, 0xAA, 0x55]
            packet[0x24:0x26] = device.devtype.to_bytes(2, "little")
            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet[0x28:0x2A] = self._pkt_no.to_bytes(2, "little")
            packet[0x2A:0x30] = device.mac[::-1]
            packet.extend(self._enc_hdlr.pack(payload))

        # Public packet.
        elif info_type >> 5 == 0:
            if not info_type % 2:  # Request.
                exp_resp_type = info_type + 1
                exp_pkt_no = 0
            else:  # Response.
                exp_resp_type = None

            packet[0x26:0x28] = info_type.to_bytes(2, "little")
            packet.extend(payload)

        # Encrypted response.
        else:
            raise ValueError("Not supported")

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x20:0x22] = checksum.to_bytes(2, "little")
        packet = bytes(packet)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
            timeout = device.timeout
            start_time = time.time()
            should_wait = False
            errors = []

            while True:
                if should_wait:
                    time.sleep(retry_intvl)

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

                conn.sendto(packet, device.host)
                _LOGGER.debug("%s sent to %s", packet, device.host)

                if exp_resp_type is None:
                    return None

                conn.settimeout(min(retry_intvl, time_left))
                try:
                    return self._recv(conn, exp_resp_type, exp_pkt_no)

                except socket.timeout:
                    should_wait = False
                    continue

                except e.AuthorizationError:
                    raise

                except e.BroadlinkException as err:
                    _LOGGER.debug(err)
                    errors.append(err)
                    should_wait = True
                    continue

    def _recv(
        self,
        conn: socket.socket,
        exp_resp_type: int,
        exp_pkt_no: int,
    ):
        """Receive a packet from the device."""
        resp, src = conn.recvfrom(2048)
        _LOGGER.debug("%s received from %s", resp, src)

        if len(resp) < 0x30:
            raise e.DataValidationError(
                -4007,
                "Received data packet length error",
                f"Expected at least 48 bytes and received {len(resp)}",
            )

        nom_checksum = int.from_bytes(resp[0x20:0x22], "little")
        real_checksum = sum(resp, 0xBEAF) - sum(resp[0x20:0x22]) & 0xFFFF

        if nom_checksum != real_checksum:
            raise e.DataValidationError(
                -4008,
                "Received data packet check error",
                f"Expected a checksum of {nom_checksum} and received {real_checksum}",
            )

        err_code = int.from_bytes(resp[0x22:0x24], "little", signed=True)
        resp_type = int.from_bytes(resp[0x26:0x28], "little")

        if resp_type != exp_resp_type:
            raise e.DataValidationError(
                -4009,
                "Received data packet information type error",
                f"Expected {exp_resp_type} and received {resp_type}",
            )

        pkt_header = resp[:0x08]
        if not any(pkt_header):
            return resp[0x30:], err_code

        pkt_no = int.from_bytes(resp[0x28:0x2A], "little")
        if pkt_no != exp_pkt_no:
            raise e.DataValidationError(f"Invalid packet number: {exp_pkt_no}")

        return self._enc_hdlr.unpack(resp[0x30:]), err_code

    @abc.abstractmethod
    def ping(self) -> None:
        """Send a Ping Response packet to the device."""

    @abc.abstractmethod
    def hello(self) -> dict:
        """Send a Client Hello packet to the device."""

    @abc.abstractmethod
    def auth(
        self,
        unique_id: str,
        hostname: str,
        client_key: str = "",
        app_data: dict = None,
    ) -> t.Tuple[int, bytes]:
        """Send a Client Key Exchange packet to the device."""

    @abc.abstractmethod
    def send_cmd(
        self,
        command: int,
        data: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a Command packet to the device."""


class V2Core(DeviceCore):
    """Controls a V2 device."""

    def ping(self) -> None:
        """Send a Ping Response packet to the device."""
        self.send_packet(0x01)

    def hello(self) -> dict:
        """Send a Client Hello packet to the device."""
        resp = self.send_packet(0x06)[0]
        return {
            "pid": int.from_bytes(resp[0x04:0x06], "little"),
            "ip_addr": socket.inet_ntoa(resp[0x6:0xA][::-1]),
            "mac_addr": resp[0x0A:0x10][::-1],
            "name": resp[0x10:].split(b"\x00")[0].decode(),
            "is_locked": bool(resp[-1]),
        }

    def auth(
        self,
        unique_id: str,
        hostname: str,
        client_key: str = "",
        app_data: dict = None,
    ) -> t.Tuple[int, bytes]:
        """Send a Client Key Exchange packet to the device."""
        unique_id = unique_id[:0x14].encode()
        hostname = hostname[:0x20].encode()
        client_key = bytes.fromhex(client_key[:0x10])

        if app_data:
            app_data = json.dumps(app_data, separators=(",", ":")).encode()
        else:
            app_data = b""

        payload = bytearray(0x64)
        payload[0x04 : 0x04 + len(unique_id)] = unique_id
        payload[0x30 : 0x30 + len(hostname)] = hostname
        payload[0x54:0x64] = client_key
        payload.extend(app_data)
        resp, err = self.send_packet(0x65, payload)
        e.check_error(err)

        conn_id = int.from_bytes(resp[:0x4], "little")
        server_key = resp[0x04:0x14].hex()
        return conn_id, server_key

    def send_cmd(
        self,
        command: int,
        data: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a Command packet to the device."""
        data = bytes(data)
        payload = command.to_bytes(4, "little") + data
        payload = self._bsize_hdlr.pack(payload)
        resp, err = self.send_packet(0x6A, payload, retry_intvl=retry_intvl)
        e.check_error(err)
        return self._bsize_hdlr.unpack(resp)[0x4:]

    def get_fwversion(self) -> int:
        """Get firmware version."""
        packet = bytearray(0x10)
        packet[0] = 0x68
        resp, err = self.send_packet(0x6A, packet)
        e.check_error(err)
        return int.from_bytes(resp[0x04:0x06], "little")

    def set_devinfo(self, name: str, is_locked: bool) -> dict:
        """Set device name and lock status."""
        name = name[:0x3F].encode()
        packet = bytearray(0x50)
        packet[0x04 : 0x04 + len(name)] = name
        packet[0x43] = bool(is_locked)
        resp, err = self.send_packet(0x6A, packet)
        e.check_error(err)
        return {
            "name": resp[0x04:0x43],
            "is_locked": resp[0x43],
        }

    def get_devinfo(self) -> None:
        """Update device name and lock status."""
        resp = self.send_cmd(0x01)
        return {
            "name": resp[0x48:].split(b"\x00")[0].decode(),
            "is_locked": bool(resp[0x87]),
        }


class V1Core(V2Core):
    """Controls a V1 device.

    If you have this device, please open an issue so we can improve
    support. It seems like it never worked.
    """

    def send_cmd(
        self,
        command: int,
        data: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a Command packet to the device."""
        data = bytes(data)
        payload = self._bsize_hdlr.pack(data)
        resp, err = self.send_packet(command, payload, retry_intvl=retry_intvl)
        e.check_error(err)
        return self._bsize_hdlr.unpack(resp)

    def set_devinfo(self, name: str, is_locked: bool) -> dict:
        """Set device name."""
        name = name[:0x3F].encode()
        packet = bytearray(0x40)
        packet[0x00 : 0x04 + len(name)] = name
        packet[0x39] = bool(is_locked)
        err = self.send_packet(0x00, packet)[1]
        e.check_error(err)
        return {
            "name": packet[0x04:0x39],
            "is_locked": packet[0x39],
        }


class V3Core(V2Core):
    """Controls a V3 device."""


class V4Core(V3Core):
    """Controls a V4 device."""

    BlockSizeHandler = p.ExtBlockSizeHandler

    def send_json_cmd(self, command, data, eoh=0x0B):
        """Send a JSON command to the device."""
        js_pkt = JSONCommand.pack(command, data, eoh=eoh)
        resp = self.send_cmd(0x5A5AA5A5, js_pkt)
        return JSONCommand.unpack(resp)[1]


class V5Core(V4Core):
    """Controls a V5 device."""

    BlockSizeHandler = p.BlockSizeHandler


class BroadlinkDevice:
    """Controls a Broadlink device."""

    _TYPE = "Unknown"

    __INIT_KEY = "097628343fe99e23765c1513accf8b02"
    __INIT_VECT = "562e17996d093d28ddb3ba695a2e6f58"

    Core = V2Core

    def __init__(
        self,
        host: t.Tuple[str, int],
        mac: t.Union[bytes, str],
        devtype: int,
        timeout: int = 10,
        name: str = None,
        model: str = None,
        manufacturer: str = None,
        is_locked: bool = None,
    ) -> None:
        """Initialize the device."""
        self.host = host
        self.mac = bytes.fromhex(mac) if isinstance(mac, str) else mac
        self.devtype = devtype
        self.timeout = timeout
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.is_locked = is_locked

        self.conn_id = 0
        self.key = self.__INIT_KEY
        self.init_vect = self.__INIT_VECT

        self._core = self.Core(self)
        self._lock = threading.Lock()

        # For backwards compatibility.
        # Use the idiomatic type(self).__name__ instead.
        self.type = self._TYPE

    def __repr__(self) -> str:
        """Return a formal representation of the device."""
        return (
            "%s.%s(%s, mac=%r, devtype=%r, timeout=%r, name=%r, "
            "model=%r, manufacturer=%r, is_locked=%r)"
        ) % (
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

    def send_packet(
        self,
        info_type: int,
        payload: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> t.Union[bytes, None]:
        """Send a packet to the device."""
        resp, err = self._core.send_packet(
            info_type, payload=payload, retry_intvl=retry_intvl
        )
        e.check_error(err)
        return resp

    def ping(self) -> None:
        """Send a Ping Response packet to the device."""
        self._core.ping()

    def hello(self) -> dict:
        """Send a Client Hello packet to the device."""
        return self._core.hello()

    def auth(self) -> bool:
        """Send a Client Key Exchange packet to the device."""
        # The unique ID does not have to be unique, but it cannot change.
        # The MAC address is not reliable for this. The IMEI and BIOS UUID
        # are great options, but there is no platform-independent way to
        # obtain this information with the Python Standard Library.
        # Leaving it as it is perfectly fine for local control, but it
        # exposes the device to spoofing techniques in case an attacker
        # gains access to the local network.

        unique_id = "1581e97d-f410-4211-8"  # It would be nice to have this.
        hostname = platform.node().split(".")[0]

        self.conn_id = 0
        self.key = self.__INIT_KEY

        conn_id, key = self._core.auth(unique_id, hostname)

        self.conn_id = conn_id
        self.key = key
        return True

    def send_cmd(
        self,
        command: int,
        data: t.Sequence[int] = b"",
        retry_intvl: float = 1.0,
    ) -> bytes:
        """Send a Command packet to the device."""
        return self._core.send_cmd(command, data=data, retry_intvl=retry_intvl)

    def get_fwversion(self) -> int:
        """Get firmware version."""
        return self._core.get_fwversion()

    def set_name(self, name: str) -> None:
        """Set device name."""
        resp = self._core.set_devinfo(name, self.is_locked)
        self.name = resp["name"]
        self.is_locked = resp["is_locked"]

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        resp = self._core.set_devinfo(self.name, state)
        self.name = resp["name"]
        self.is_locked = resp["is_locked"]

    def update(self) -> None:
        """Update device name and lock status."""
        resp = self._core.get_devinfo()
        self.name = resp["name"]
        self.is_locked = resp["is_locked"]

    def get_type(self) -> str:
        """Return device type.

        For backwards compatibility. Use the idiomatic
        type(self).__name__ instead.
        """
        return self.type


def v1_core(cls):
    """Decorator to inject a V1 core into a device class."""
    cls.Core = V1Core
    return cls


def v2_core(cls):
    """Decorator to inject a V2 core into a device class."""
    cls.Core = V2Core
    return cls


def v3_core(cls):
    """Decorator to inject a V3 core into a device class."""
    cls.Core = V3Core
    return cls


def v4_core(cls):
    """Decorator to inject a V4 core into a device class."""
    cls.Core = V4Core
    cls.send_json_cmd = V4Core.send_json_cmd
    return cls


def v5_core(cls):
    """Decorator to inject a V5 core into a device class."""
    cls.Core = V5Core
    cls.send_json_cmd = V5Core.send_json_cmd
    return cls
