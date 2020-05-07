"""Exceptions for Broadlink devices."""


class BroadlinkException(Exception):
    """Common base class for all Broadlink exceptions."""
    pass


class AuthenticationError(BroadlinkException):
    """Authentication error."""
    pass


class AuthorizationError(BroadlinkException):
    """Authorization error."""
    pass


class CommandNotSupportedError(BroadlinkException):
    """Command not supported error."""
    pass


class ConnectionClosedError(BroadlinkException):
    """Connection closed error."""
    pass


class DataValidationError(BroadlinkException):
    """Data validation error."""
    pass


class DeviceOfflineError(BroadlinkException):
    """Device offline error."""
    pass


class ReadError(BroadlinkException):
    """Read error."""
    pass


class SendError(BroadlinkException):
    """Send error."""
    pass


class SSIDNotFoundError(BroadlinkException):
    """SSID not found error."""
    pass


class StorageError(BroadlinkException):
    """Storage error."""
    pass


class UnknownError(BroadlinkException):
    """Unknown error."""
    pass


class WriteError(BroadlinkException):
    """Write error."""
    pass


FIRMWARE_ERRORS = {
    0xffff: (AuthenticationError, "Authentication failed"),
    0xfffe: (ConnectionClosedError, "You have been logged out"),
    0xfffd: (DeviceOfflineError, "The device is offline"),
    0xfffc: (CommandNotSupportedError, "Command not supported"),
    0xfffb: (StorageError, "The device storage is full"),
    0xfffa: (DataValidationError, "Structure is abnormal"),
    0xfff9: (AuthorizationError, "Control key is expired"),
    0xfff8: (SendError, "Send error"),
    0xfff7: (WriteError, "Write error"),
    0xfff6: (ReadError, "Read error"),
    0xfff5: (SSIDNotFoundError, "SSID could not be found in AP configuration"),
}


def exception(error_code):
    """Return exception corresponding to an error code."""
    try:
        exc, msg = FIRMWARE_ERRORS[error_code]
        return exc(msg)
    except KeyError:
        return UnknownError("Unknown error: " + hex(error_code))


def check_error(error):
    """Raise exception if an error occurred."""
    error_code = error[0] | (error[1] << 8)
    if error_code:
        raise exception(error_code)
