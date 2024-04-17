"""The networking part of the python-broadlink library."""
import datetime as dt
import time


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
        data[0x08] = int(datetime.strftime("%y"))
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
        if int(datetime.strftime("%y")) != subyear:
            raise ValueError("subyear does not match")

        return datetime

    @staticmethod
    def now() -> dt.datetime:
        """Return the current date and time with timezone info."""
        tz_info = dt.timezone(dt.timedelta(seconds=-time.timezone))
        return dt.datetime.now(tz_info)
