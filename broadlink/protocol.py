"""The protocol."""
import datetime as dt
import logging
import socket
import time
import typing as t

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import exceptions as e

_LOGGER = logging.getLogger(__name__)


class Datetime:
    """Helps to pack and unpack datetime objects."""

    @staticmethod
    def pack(datetime: t.Union[dt.datetime, None]) -> bytes:
        """Pack a datetime object to be sent over the Broadlink protocol."""
        data = bytearray(12)
        if datetime is None:
            return data

        utcoffset = int(datetime.utcoffset().total_seconds() / 3600)
        data[:0x04] = utcoffset.to_bytes(4, "little", signed=True)
        data[0x04:0x06] = datetime.year.to_bytes(2, "little")
        data[0x06] = datetime.minute
        data[0x07] = datetime.hour
        data[0x08] = int(datetime.strftime("%y"))
        data[0x09] = datetime.isoweekday()
        data[0x0A] = datetime.day
        data[0x0B] = datetime.month
        return data

    @staticmethod
    def unpack(data: bytes) -> t.Union[dt.datetime, None]:
        """Unpack a datetime object received over the Broadlink protocol."""
        if not any(data):
            return None

        utcoffset = int.from_bytes(data[0x00:0x04], "little", signed=True)
        year = int.from_bytes(data[0x04:0x06], "little")
        minute = data[0x06]
        hour = data[0x07]
        subyear = data[0x08]
        isoweekday = data[0x09]
        day = data[0x0A]
        month = data[0x0B]

        tz_info = dt.timezone(dt.timedelta(hours=utcoffset))
        datetime = dt.datetime(year, month, day, hour, minute, 0, 0, tz_info)

        if datetime.isoweekday() != isoweekday:
            raise ValueError("isoweekday does not match")
        if int(datetime.strftime("%y")) != subyear:
            raise ValueError("subyear does not match")

        return datetime

    @staticmethod
    def now() -> dt.datetime:
        """Return the current date and time with timezone info."""
        tz_info = dt.timezone(dt.timedelta(seconds=-time.timezone))
        return dt.datetime.now(tz_info)


class Address:
    """Helper functions to pack and unpack addresses."""

    @staticmethod
    def pack(address: t.Union[t.Tuple[str, int], None]) -> bytes:
        """Pack an address to be sent over the Broadlink protocol."""
        data = bytearray(6)
        if address is None:
            return data

        data[:0x04] = socket.inet_aton(address[0])[::-1]
        data[0x04:0x06] = address[1].to_bytes(2, "little")
        return data

    @staticmethod
    def unpack(data: bytes) -> t.Union[t.Tuple[str, int], None]:
        """Unpack an address received over the Broadlink protocol."""
        if not any(data):
            return None

        ip_addr = socket.inet_ntoa(data[:0x04][::-1])
        port = int.from_bytes(data[0x04:0x06], "little")
        return (ip_addr, port)


class BlockSizeHandler:
    """Helps to handle the block size before encryption/after decryption.

    The block size must be a multiple of 16.
    """

    @staticmethod
    def pack(payload: bytes) -> bytes:
        """Pad a message for encryption."""
        padding = bytes((16 - len(payload)) % 16)
        return payload + padding

    @staticmethod
    def unpack(data: bytes) -> bytes:
        """Unpad a message after decryption."""
        return data


class ExtBlockSizeHandler:
    """Helps to handle the block size before encryption/after decryption.

    The block size must be a multiple of 16 and the message must be
    prefixed to its length before encryption and sliced accordingly after
    decryption.
    """

    @staticmethod
    def pack(payload: bytes) -> bytes:
        """Pad a message for encryption."""
        payload = len(payload).to_bytes(2, "little") + payload
        padding = bytes((16 - len(payload)) % 16)
        return payload + padding

    @staticmethod
    def unpack(data: bytes) -> bytes:
        """Unpad a message after decryption."""
        p_len = int.from_bytes(data[:0x02], "little")

        try:
            return data[0x02 : p_len + 0x02]
        except IndexError as err:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected {p_len} bytes and received {len(data[0x2:])}",
            ) from err


class EncryptionHandler:
    """Helps to pack and unpack encrypted messages."""

    def __init__(self, device) -> None:
        """Initialize the handler."""
        self._device = device

    def pack(self, payload: bytes = b"") -> bytes:
        """Pack an encrypted message to be sent over the Broadlink protocol."""
        device = self._device
        packet = bytearray(0x08)

        payload = bytes(payload + bytes((16 - len(payload)) % 16))
        checksum = sum(payload, 0xBEAF) & 0xFFFF

        packet[0x00:0x04] = device.conn_id.to_bytes(4, "little")
        packet[0x04:0x06] = checksum.to_bytes(2, "little")

        aes = Cipher(
            algorithms.AES(bytes.fromhex(device.key)),
            modes.CBC(bytes.fromhex(device.init_vect)),
            backend=default_backend(),
        )
        encryptor = aes.encryptor()
        encrypted_payload = encryptor.update(payload) + encryptor.finalize()
        _LOGGER.debug("Encryption: %s -> %s", payload, encrypted_payload)

        packet.extend(encrypted_payload)
        return bytes(packet)

    def unpack(self, data: bytes) -> bytes:
        """Unpack an encrypted message received over the Broadlink protocol."""
        device = self._device

        if len(data) < 0x08:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected at least 8 bytes and received {len(data)}",
            )

        conn_id = int.from_bytes(data[:0x04], "little")
        nom_checksum = int.from_bytes(data[0x04:0x06], "little")
        payload = data[0x08:]

        if device.conn_id and device.conn_id != conn_id:
            raise e.AuthorizationError(
                -4012,
                "Device control ID error",
                f"Expected {device.conn_id} and received {conn_id}",
            )

        if len(payload) % 16:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected a multiple of 16 and received {len(payload)}",
            )

        aes = Cipher(
            algorithms.AES(bytes.fromhex(device.key)),
            modes.CBC(bytes.fromhex(device.init_vect)),
            backend=default_backend(),
        )
        decryptor = aes.decryptor()
        decrypted_payload = decryptor.update(payload) + decryptor.finalize()
        _LOGGER.debug("Decryption: %s -> %s", payload, decrypted_payload)

        real_checksum = sum(decrypted_payload, 0xBEAF) & 0xFFFF
        if decrypted_payload and nom_checksum != real_checksum:
            raise e.DataValidationError(
                -4011,
                "Received encrypted data packet check error",
                f"Expected a checksum of {nom_checksum} and received {real_checksum}",
            )
        return decrypted_payload
