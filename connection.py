import serial
from serial import Serial
from device import Device
from threading import Thread
from queue import Queue
from typing import Optional
from dataclasses import dataclass
from events import SerialEvent, Connect, DataEvent, Disconnect


class Connection:
    _serial: Serial
    device: Device

    def __init__(self, device, baudrate):
        # can't pass parameters in to constructor because it auto opens the port
        # and I don't want that
        self._serial = Serial()
        self._serial.port = device.port
        self._serial.baudrate = baudrate
        self.device = device

    def open(self):
        self._serial.open()

    def close(self):
        self._serial.close()

    def write(self, data: bytes):
        self._serial.write(data)

    def read_byte(self) -> bytes:
        return self._serial.read()

    @property
    def is_connected(self):
        return self._serial.is_open

    @property
    def baudrate(self):

        return self._serial.baudrate


@dataclass
class ConnectionManager:
    _connection: Optional[Connection] = None
    _event_queue: Queue[SerialEvent] = Queue()
    _reader: Optional[Thread] = None

    def read_loop(self, connection: Connection):
        while connection.is_connected:
            try:
                data = connection.read_byte()
                if data:
                    self._inject_event(
                        DataEvent(
                            connection.device, data.decode("utf-8", errors="replace")
                        )
                    )
            except (TypeError, OSError, serial.SerialException):
                break

        self._connection = None
        self._inject_event(Disconnect(connection.device))

    def read_event(self):
        return self._event_queue.get()

    def disconnect(self):
        if not self._connection or self._disconnect_sent:
            return
        if self._connection.is_connected:
            self._connection.close()
        self._connection = None
        if self._reader and self._reader.is_alive():
            self._reader.join()

    def connect(self, connection: Connection):
        self.disconnect()
        self._disconnect_sent = False
        self._inject_event(Connect(connection.device))
        self._connection = connection
        connection.open()
        self._reader = Thread(target=self.read_loop, args=(connection,), daemon=True)
        self._reader.start()

    def write(self, data: bytes):
        if self._connection and self._connection.is_connected:
            self._connection.write(data)

    def _inject_event(self, event: SerialEvent):
        self._event_queue.put(event)
