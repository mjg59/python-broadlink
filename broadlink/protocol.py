import datetime as dt
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import exceptions as e


class Datetime:
    """Helps to pack and unpack datetime objects for the Broadlink protocol."""

    @staticmethod
    def pack(datetime: dt.datetime) -> bytes:
        """Pack the timestamp to be sent over the Broadlink protocol."""
        data = bytearray(12)
        utcoffset = int(datetime.utcoffset().total_seconds() / 3600)
        data[:0x04] = utcoffset.to_bytes(4, "little", signed=True)
        data[0x04:0x06] = datetime.year.to_bytes(2, "little")
        data[0x06] = datetime.minute
        data[0x07] = datetime.hour
        data[0x08] = int(datetime.strftime('%y'))
        data[0x09] = datetime.isoweekday()
        data[0x0A] = datetime.day
        data[0x0B] = datetime.month
        return data

    @staticmethod
    def unpack(data: bytes) -> dt.datetime:
        """Unpack a timestamp received over the Broadlink protocol."""
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
        if int(datetime.strftime('%y')) != subyear:
            raise ValueError("subyear does not match")

        return datetime

    @staticmethod
    def now() -> dt.datetime:
        """Return the current date and time with timezone info."""
        tz_info = dt.timezone(dt.timedelta(seconds=-time.timezone))
        return dt.datetime.now(tz_info)


class BlockSizeHandler:
    """Helps to pack and unpack messages for encryption.

    The block size must be a multiple of 16.
    """

    @staticmethod
    def pack(payload: bytes) -> bytes:
        """Pad a message for encryption."""
        padding = bytes((16 - len(payload)) % 16)
        return payload + padding

    @staticmethod
    def unpack(payload: bytes) -> bytes:
        """Unpad a message after decryption."""
        return payload


class ExtBlockSizeHandler:
    """Helps to pack and unpack messages for encryption.

    The block size must be a multiple of 16 and the message must be
    preceded by its length when packing and sliced accordingly when
    unpacking.
    """

    @staticmethod
    def pack(payload: bytes) -> bytes:
        """Pad a message for encryption."""
        payload = len(payload).to_bytes(2, "little") + payload
        padding = bytes((16 - len(payload)) % 16)
        return payload + padding

    @staticmethod
    def unpack(payload: bytes) -> bytes:
        """Unpad a message after decryption."""
        p_len = int.from_bytes(payload[:0x02], "little")

        try:
            return payload[0x02:p_len+0x02]
        except IndexError:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected {p_len} bytes and received {len(payload[0x2:])}",
            )


class EncryptionHandler:
    """Helps to handle AES-128 encryption."""

    __INITIAL_KEY = "097628343fe99e23765c1513accf8b02"
    __INITIAL_VECT = "562e17996d093d28ddb3ba695a2e6f58"

    def __init__(self) -> None:
        """Initialize the handler."""
        self.aes = None
        self.id = None
        self.reset()

    def pack(self, payload: bytes = b"") -> bytes:
        """Pack an encrypted message to be sent over the Broadlink protocol."""
        packet = bytearray(0x08)
        packet[:0x04] = self.id.to_bytes(4, "little")

        checksum = sum(payload, 0xBEAF) & 0xFFFF
        packet[0x04:0x06] = checksum.to_bytes(2, "little")

        padding = bytes((16 - len(payload)) % 16)
        payload = self._encrypt(payload + padding)
        packet.extend(payload)
        return bytes(packet)

    def unpack(self, packet: bytes, checksum: int = None) -> bytes:
        """Unpack an encrypted message received over the Broadlink protocol."""
        if len(packet) < 0x08:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected at least 8 bytes and received {len(packet)}",
            )

        conn_id = int.from_bytes(packet[:0x04], "little")
        nom_checksum = int.from_bytes(packet[0x04:0x06], "little")
        payload = packet[0x08:]

        if self.id and self.id != conn_id:
            raise e.AuthorizationError(
                -4012,
                "Device control ID error",
                f"Expected {self.id} and received {conn_id}",
            )

        if len(payload) % 16:
            raise e.DataValidationError(
                -4010,
                "Received encrypted data packet length error",
                f"Expected a multiple of 16 and received {len(payload)}",
            )

        payload = self._decrypt(payload)
        real_checksum = sum(payload, 0xBEAF) & 0xFFFF

        if payload and nom_checksum != real_checksum:
            raise e.DataValidationError(
                -4011,
                "Received encrypted data packet check error",
                f"Expected a checksum of {nom_checksum} and received {real_checksum}",
            )
        return payload

    def update(self, conn_id: int, key: bytes) -> None:
        """Update connection ID and AES key."""
        self.id = conn_id
        self.aes = Cipher(
            algorithms.AES(bytes(key)),
            modes.CBC(bytes.fromhex(self.__INITIAL_VECT)),
            backend=default_backend(),
        )

    def reset(self) -> None:
        """Reset connection ID and AES key."""
        self.update(0, bytes.fromhex(self.__INITIAL_KEY))

    def _encrypt(self, payload: bytes) -> bytes:
        """Encrypt the payload."""
        encryptor = self.aes.encryptor()
        return encryptor.update(bytes(payload)) + encryptor.finalize()

    def _decrypt(self, payload: bytes) -> bytes:
        """Decrypt the payload."""
        decryptor = self.aes.decryptor()
        return decryptor.update(bytes(payload)) + decryptor.finalize()
