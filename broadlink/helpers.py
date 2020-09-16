"""Helper functions."""
import socket

from .exceptions import exception


def get_local_ip() -> str:
    """Try to determine the local IP address of the machine."""
    # Useful for VPNs.
    try:
        local_ip_address = socket.gethostbyname(socket.gethostname())
        if not local_ip_address.startswith('127.'):
            return local_ip_address
    except socket.gaierror:
        raise exception(-4013)  # DNS Error

    # Connecting to UDP address does not send packets.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 53))
        return s.getsockname()[0]
