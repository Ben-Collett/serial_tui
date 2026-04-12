from dataclasses import dataclass
from typing import Optional 
from device import Device
@dataclass
class SerialEvent:
    device: Optional[Device]


class Connect(SerialEvent):
    pass


class Disconnect(SerialEvent):
    pass


@dataclass
class ErrorEvent(SerialEvent):
    err: str


@dataclass
class DataEvent(SerialEvent):
    msg: str

