"""Device discovery."""
import socket
import time
import typing as t

from . import alarm, climate, cover, device
from . import exceptions as e
from . import light, remote, sensor, switch
from .protocol import Address, Datetime

SUPPORTED_TYPES = {
    0x0000: (switch.sp1, "SP1", "Broadlink"),
    0x2717: (switch.sp2, "NEO", "Ankuoo"),
    0x2719: (switch.sp2, "SP2-compatible", "Honeywell"),
    0x271A: (switch.sp2, "SP2-compatible", "Honeywell"),
    0x2720: (switch.sp2, "SP mini", "Broadlink"),
    0x2728: (switch.sp2, "SP2-compatible", "URANT"),
    0x273E: (switch.sp2, "SP mini", "Broadlink"),
    0x7530: (switch.sp2, "SP2", "Broadlink (OEM)"),
    0x7539: (switch.sp2, "SP2-IL", "Broadlink (OEM)"),
    0x753E: (switch.sp2, "SP mini 3", "Broadlink"),
    0x7540: (switch.sp2, "MP2", "Broadlink"),
    0x7544: (switch.sp2, "SP2-CL", "Broadlink"),
    0x7546: (switch.sp2, "SP2-UK/BR/IN", "Broadlink (OEM)"),
    0x7547: (switch.sp2, "SC1", "Broadlink"),
    0x7918: (switch.sp2, "SP2", "Broadlink (OEM)"),
    0x7919: (switch.sp2, "SP2-compatible", "Honeywell"),
    0x791A: (switch.sp2, "SP2-compatible", "Honeywell"),
    0x7D0D: (switch.sp2, "SP mini 3", "Broadlink (OEM)"),
    0x2711: (switch.sp2s, "SP2", "Broadlink"),
    0x2716: (switch.sp2s, "NEO PRO", "Ankuoo"),
    0x271D: (switch.sp2s, "Ego", "Efergy"),
    0x2736: (switch.sp2s, "SP mini+", "Broadlink"),
    0x2733: (switch.sp3, "SP3", "Broadlink"),
    0x7D00: (switch.sp3, "SP3-EU", "Broadlink (OEM)"),
    0x9479: (switch.sp3s, "SP3S-US", "Broadlink"),
    0x947A: (switch.sp3s, "SP3S-EU", "Broadlink"),
    0x756C: (switch.sp4, "SP4M", "Broadlink"),
    0x756F: (switch.sp4, "MCB1", "Broadlink"),
    0x7579: (switch.sp4, "SP4L-EU", "Broadlink"),
    0x7583: (switch.sp4, "SP mini 3", "Broadlink"),
    0x7D11: (switch.sp4, "SP mini 3", "Broadlink"),
    0xA56A: (switch.sp4, "MCB1", "Broadlink"),
    0xA589: (switch.sp4, "SP4L-UK", "Broadlink"),
    0x5115: (switch.sp4b, "SCB1E", "Broadlink"),
    0x51E2: (switch.sp4b, "AHC/U-01", "BG Electrical"),
    0x6111: (switch.sp4b, "MCB1", "Broadlink"),
    0x6113: (switch.sp4b, "SCB1E", "Broadlink"),
    0x618B: (switch.sp4b, "SP4L-EU", "Broadlink"),
    0x6489: (switch.sp4b, "SP4L-AU", "Broadlink"),
    0x648B: (switch.sp4b, "SP4M-US", "Broadlink"),
    0x2737: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x278F: (remote.rmmini, "RM mini", "Broadlink"),
    0x27C2: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27C7: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27CC: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27CD: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27D0: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27D1: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27D3: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x27DE: (remote.rmmini, "RM mini 3", "Broadlink"),
    0x2712: (remote.rmpro, "RM pro/pro+", "Broadlink"),
    0x272A: (remote.rmpro, "RM pro", "Broadlink"),
    0x273D: (remote.rmpro, "RM pro", "Broadlink"),
    0x277C: (remote.rmpro, "RM home", "Broadlink"),
    0x2783: (remote.rmpro, "RM home", "Broadlink"),
    0x2787: (remote.rmpro, "RM pro", "Broadlink"),
    0x278B: (remote.rmpro, "RM plus", "Broadlink"),
    0x2797: (remote.rmpro, "RM pro+", "Broadlink"),
    0x279D: (remote.rmpro, "RM pro+", "Broadlink"),
    0x27A1: (remote.rmpro, "RM plus", "Broadlink"),
    0x27A6: (remote.rmpro, "RM plus", "Broadlink"),
    0x27A9: (remote.rmpro, "RM pro+", "Broadlink"),
    0x27C3: (remote.rmpro, "RM pro+", "Broadlink"),
    0x5F36: (remote.rmminib, "RM mini 3", "Broadlink"),
    0x6508: (remote.rmminib, "RM mini 3", "Broadlink"),
    0x51DA: (remote.rm4mini, "RM4 mini", "Broadlink"),
    0x6070: (remote.rm4mini, "RM4C mini", "Broadlink"),
    0x610E: (remote.rm4mini, "RM4 mini", "Broadlink"),
    0x610F: (remote.rm4mini, "RM4C mini", "Broadlink"),
    0x62BC: (remote.rm4mini, "RM4 mini", "Broadlink"),
    0x62BE: (remote.rm4mini, "RM4C mini", "Broadlink"),
    0x6364: (remote.rm4mini, "RM4S", "Broadlink"),
    0x648D: (remote.rm4mini, "RM4 mini", "Broadlink"),
    0x6539: (remote.rm4mini, "RM4C mini", "Broadlink"),
    0x653A: (remote.rm4mini, "RM4 mini", "Broadlink"),
    0x6026: (remote.rm4pro, "RM4 pro", "Broadlink"),
    0x61A2: (remote.rm4pro, "RM4 pro", "Broadlink"),
    0x649B: (remote.rm4pro, "RM4 pro", "Broadlink"),
    0x653C: (remote.rm4pro, "RM4 pro", "Broadlink"),
    0x2714: (sensor.a1, "e-Sensor", "Broadlink"),
    0x2722: (alarm.S1C, "S2KIT", "Broadlink"),
    0x4E4D: (cover.dooya, "DT360E-45/20", "Dooya"),
    0x4EAD: (climate.hysen, "HY02B05H", "Hysen"),
    0x4EB5: (switch.mp1, "MP1-1K4S", "Broadlink"),
    0x4EF7: (switch.mp1, "MP1-1K4S", "Broadlink (OEM)"),
    0x4F1B: (switch.mp1, "MP1-1K3S2U", "Broadlink (OEM)"),
    0x4F65: (switch.mp1, "MP1-1K3S2U", "Broadlink"),
    0x51E3: (switch.bg1, "BG800/BG900", "BG Electrical"),
    0x5043: (light.lb1, "SB800TD", "Broadlink (OEM)"),
    0x504E: (light.lb1, "LB1", "Broadlink"),
    0x60C7: (light.lb1, "LB1", "Broadlink"),
    0x60C8: (light.lb1, "LB1", "Broadlink"),
    0x6112: (light.lb1, "LB1", "Broadlink"),
    0xA4F4: (light.lb27, "LB27 R1", "Broadlink"),
}


def gendevice(
    dev_type: int,
    host: t.Tuple[str, int],
    mac: t.Union[bytes, str],
    name: str = None,
    is_locked: bool = None,
) -> device.BroadlinkDevice:
    """Generate a device."""
    try:
        dev_class, model, manufacturer = SUPPORTED_TYPES[dev_type]

    except KeyError:
        return device.UnknownDevice(host, mac, dev_type, name=name, is_locked=is_locked)

    return dev_class(
        host,
        mac,
        dev_type,
        name=name,
        model=model,
        manufacturer=manufacturer,
        is_locked=is_locked,
    )


def hello(
    address: str,
    port: int = 80,
    timeout: int = 10,
    local_ip_address: str = None,
) -> device.BroadlinkDevice:
    """Direct device discovery.

    Useful if the device is locked.
    """
    try:
        return next(xdiscover(timeout, local_ip_address, address, port))
    except StopIteration as err:
        raise e.NetworkTimeoutError(
            -4000,
            "Network timeout",
            f"No response received within {timeout}s",
        ) from err


def discover(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> t.List[device.BroadlinkDevice]:
    """Discover devices connected to the local network."""
    dev_generator = xdiscover(
        timeout, local_ip_address, discover_ip_address, discover_ip_port
    )
    return [*dev_generator]


def xdiscover(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> t.Generator[device.BroadlinkDevice, None, None]:
    """Discover devices connected to the local network.

    This function generates devices instantly.
    """
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if local_ip_address:
        conn.bind((local_ip_address, 0))
        port = conn.getsockname()[1]
        source = (local_ip_address, port)
    else:
        source = None

    packet = bytearray(0x30)
    packet[0x08:0x14] = Datetime.pack(Datetime.now())
    packet[0x18:0x1E] = Address.pack(source)
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
                yield gendevice(devtype, host, mac, name, is_locked)
    finally:
        conn.close()
