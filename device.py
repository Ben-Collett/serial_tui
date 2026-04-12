import serial.tools.list_ports
from dataclasses import dataclass
from typing import Self


def _list_ports():
    return serial.tools.list_ports.comports()


@dataclass
class Device:
    name: str
    port: str
    description: str  # used for heuristics for filtering

    @staticmethod
    def _from_port(port) -> Self:
        return Device(port.name, port.device, port.description)

    @staticmethod
    def available_devices() -> list[Self]:
        return [Device._from_port(port) for port in _list_ports()]
