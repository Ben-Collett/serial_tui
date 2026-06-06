import serial.tools.list_ports
from dataclasses import dataclass


def _list_ports():
    return serial.tools.list_ports.comports()


@dataclass
class RecommendedDeviceSettings:
    baud_rate: int | None = None
    auto_new_line: bool | None = None
    auto_return_carry: bool | None = None
    throttle_ms: int | None = None
    auto_complete_suggestions: list[tuple[str, str]] | None = None


@dataclass
class Device:
    name: str
    port: str
    description: str  # used for heuristics for filtering

    @staticmethod
    def _from_port(port) -> "Device":
        return Device(port.name, port.device, port.description)

    @staticmethod
    def available_devices() -> list["Device"]:
        return [Device._from_port(port) for port in _list_ports()]
