import serial
from serial import Serial
from device import Device
from threading import Thread, Event
from queue import Queue, Empty
from typing import Optional
from dataclasses import dataclass, field
from events import SerialEvent, Connect, DataEvent, Disconnect, BufferUpdate
import time


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
    throttle_ms: int = 0
    _write_buffer: Queue = field(default_factory=Queue)
    _last_write_time: float = 0.0
    _consumer_thread: Optional[Thread] = None
    _consumer_stop: Event = field(default_factory=Event)
    _disconnect_sent: bool = False

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
        if not self._disconnect_sent:
            self._inject_event(Disconnect(connection.device))

    def read_event(self):
        return self._event_queue.get()

    def disconnect(self):
        if not self._connection or self._disconnect_sent:
            return
        self._consumer_stop.set()
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join()
        while not self._write_buffer.empty():
            try:
                self._write_buffer.get_nowait()
            except Empty:
                break
        self._inject_event(BufferUpdate(self._connection.device if self._connection else None))
        dev = self._connection.device
        self._inject_event(Disconnect(dev))
        self._disconnect_sent = True
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
        if not self._connection or not self._connection.is_connected:
            return
        if self.throttle_ms <= 0:
            self._connection.write(data)
            return
        self._write_buffer.put(data)
        self._inject_event(BufferUpdate(self._connection.device))
        if self._consumer_thread is None or not self._consumer_thread.is_alive():
            self._consumer_stop.clear()
            self._consumer_thread = Thread(target=self._write_consumer_loop, daemon=True)
            self._consumer_thread.start()

    def flush(self):
        while not self._write_buffer.empty():
            try:
                data = self._write_buffer.get_nowait()
                if self._connection and self._connection.is_connected:
                    self._connection.write(data)
            except Empty:
                break
        self._inject_event(BufferUpdate(device=None))

    @property
    def buffer_size(self) -> int:
        return self._write_buffer.qsize()

    def _write_consumer_loop(self):
        while not self._consumer_stop.is_set():
            try:
                data = self._write_buffer.get(timeout=0.1)
                self._inject_event(BufferUpdate(device=None))
            except Empty:
                continue
            if self._consumer_stop.is_set():
                break
            if not self._connection or not self._connection.is_connected:
                break
            elapsed = time.monotonic() - self._last_write_time
            min_interval = self.throttle_ms / 1000.0
            if elapsed < min_interval:
                self._consumer_stop.wait(min_interval - elapsed)
                if self._consumer_stop.is_set():
                    break
            try:
                self._connection.write(data)
            except Exception:
                break
            self._last_write_time = time.monotonic()

    def _inject_event(self, event: SerialEvent):
        self._event_queue.put(event)
