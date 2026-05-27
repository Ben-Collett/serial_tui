from dataclasses import dataclass, field
from typing import Optional
from device import Device
from connection import Connection, ConnectionManager
from threading import Thread
import time
from events import SerialEvent, DataEvent, Connect, Disconnect


@dataclass
class SerialManager:
    devices_override: Optional[list[Device]] = None
    selected_device: Optional[Device] = None
    baudrate: int = 115200
    _connection_manager: ConnectionManager = field(
        default_factory=ConnectionManager)
    _hooks: list = field(default_factory=list)
    _event_dispatcher: Optional[Thread] = None

    def get_devices(self):
        if self.devices_override is not None:
            return self.devices_override
        return Device.available_devices()

    def connect(self):
        self.disconnect()
        connection = Connection(self.selected_device, self.baudrate)
        self._connection_manager.connect(connection)
        self._event_dispatcher = Thread(
            target=self._dispatch_loop, daemon=True)
        self._event_dispatcher.start()

    def hook(self, func):
        """
        registers a function which recienves every serial event
        """
        self._hooks.append(func)

    def _dispatch_loop(self):
        while self._connection_manager._connection is not None:
            event = self._connection_manager.read_event()
            for hook in self._hooks:
                hook(event)

    def write(self, to_write: bytes):
        self._connection_manager.write(to_write)

    def disconnect(self):
        self._connection_manager.disconnect()


def my_print(event: SerialEvent):
    if isinstance(event, DataEvent):
        print(event.msg, end="")
    elif isinstance(event, Connect):
        print("connected", event.device)
    elif isinstance(event, Disconnect):
        print("disconnected", event.device)


if __name__ == "__main__":
    manager = SerialManager()
    manager.selected_device = Device(
        name="ttyACM0",
        port="/dev/ttyACM0",
        description="CharaChorder Two S3 - CharaChorder Two USB Serial",
    )
    manager.hook(my_print)
    manager.connect()
    manager.write(b"CMD\r\n")
    time.sleep(.2)
    # manager.disconnect()
    time.sleep(.3)
    manager.connect()
    manager.write(b"CMD\r\n")
    time.sleep(.2)
    manager.disconnect()
    time.sleep(.2)
