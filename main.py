import codecs
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, Right, VerticalGroup
from textual.widgets import Button, Footer, Header, Input, Label, Switch, TextArea
from popups import SelectDeviceData, SelectDeviceScreen
from my_manager import manager
from events import DataEvent, Connect, Disconnect, ErrorEvent, SerialEvent, BufferUpdate


def _unescape_escapes(text: str) -> str:
    """Convert escape sequences like \\r, \\n into actual control chars.
    \\\\ -> \\, \\r -> \\r, \\n -> \\n, \\xNN -> hex byte, etc.
    Malformed sequences (trailing \\, \\x without hex) fall back to original."""
    try:
        return codecs.decode(text.encode("latin-1"), "unicode_escape")
    except (ValueError, SyntaxError):
        return text


class SerialTui(App):
    CSS_PATH = "main_screen.scss"
    BINDINGS = []

    def __init__(self):
        super().__init__()
        self._connected = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield TopBar(id="topbar")
        yield TextArea(id="output", read_only=True)
        yield StatusBar(id="statusbar")
        yield Footer()

    def on_mount(self) -> None:
        manager.hook(self._handle_event)

    def _handle_event(self, event: SerialEvent) -> None:
        if isinstance(event, DataEvent):
            self.call_from_thread(self._append_data, event.msg)
        elif isinstance(event, Connect):
            self.call_from_thread(self._on_connected)
        elif isinstance(event, Disconnect):
            self.call_from_thread(self._on_disconnected)
        elif isinstance(event, ErrorEvent):
            self.call_from_thread(self._on_error, event.err)
        elif isinstance(event, BufferUpdate):
            self.call_from_thread(self._update_buffer_display)

    def _append_data(self, msg: str) -> None:
        ta = self.query_one("#output", TextArea)
        ta.insert(msg, location=ta.document.end)

    def _on_connected(self) -> None:
        self._connected = True
        dev = manager.selected_device
        self.query_one("#data", Label).update(
            f"baud-rate:{manager.baudrate}\r\nport:{dev.port}\r\ndevice:{dev.name}"
        )
        self._log_message(
            f"connected – {dev.name} @ {dev.port}:{manager.baudrate}")
        btn = self.query_one("#conbtn", Button)
        btn.label = "disconnect"
        btn.add_class("disconnect")

    def _log_message(self, msg: str) -> None:
        self._append_data(f"SerialTui: {msg}\n")

    def _on_disconnected(self) -> None:
        self._connected = False
        self._log_message("disconnection device")
        btn = self.query_one("#conbtn", Button)
        btn.label = "connect"
        btn.remove_class("disconnect")
        self.query_one("#bufcount", Label).update("")

    def _on_error(self, err: str) -> None:
        self._log_message(f"error: {err}")

    def _update_buffer_display(self) -> None:
        buf_count = manager.buffer_size
        self.query_one("#bufcount", Label).update(
            f"buf:{buf_count}"
        )
        ms = manager.throttle_ms
        self.query_one("#throttledisplay", Label).update(
            f"th:{ms}ms" if ms > 0 else "th:off"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "selectbtn":
            self.push_screen(SelectDeviceScreen(), self._device_selected)
        elif event.button.id == "send":
            self._send_data()
        elif event.button.id == "conbtn":
            self._toggle_connect()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._send_data()

    def _device_selected(self, data: SelectDeviceData | None) -> None:
        if data is None:
            return
        manager.selected_device = data.device
        manager.baudrate = data.baud_rate
        if data.settings_accepted and data.recommend_settings is not None:
            rs = data.recommend_settings
            for section in self.query_one("#newlineset", NewLineSet).query(ToggleSection):
                if r"\n" in section.label and rs.auto_new_line is not None:
                    section.query_one(Switch).value = rs.auto_new_line
                elif r"\r" in section.label and rs.auto_return_carry is not None:
                    section.query_one(Switch).value = rs.auto_return_carry
            if rs.throttle_ms is not None:
                manager.throttle_ms = rs.throttle_ms
        self._update_device_display()

    def _update_device_display(self):
        dev = manager.selected_device
        self.query_one("#data", Label).update(
            f"baud-rate:{manager.baudrate}\r\nport:{dev.port}\r\ndevice:{dev.name}"
        )

    def _toggle_newline(self, check: str) -> None:
        for section in self.query_one("#newlineset", NewLineSet).query(ToggleSection):
            if check in section.label:
                sw = section.query_one(Switch)
                sw.value = not sw.value
                break

    def _handle_command(self, text: str) -> None:
        cmd = text[1:].strip().lower()

        if cmd == "r":
            self._toggle_newline(r"\r")
        elif cmd == "n":
            self._toggle_newline(r"\n")
        elif cmd == "rn":
            self._toggle_newline(r"\r")
            self._toggle_newline(r"\n")
        elif cmd == "echo":
            self._toggle_newline("echo")
        elif cmd in ("connect", "con"):
            self._toggle_connect()
        elif cmd in ("disconnect", "dis"):
            manager.disconnect()
        elif cmd == "c":
            self._toggle_connect()
        elif cmd in ("s", "select"):
            self.push_screen(SelectDeviceScreen(), self._device_selected)
        elif cmd in ("clear", "l"):
            self.query_one("#output", TextArea).text = ""
        elif cmd.startswith("throttle") or cmd == "th" or cmd.startswith("th "):
            parts = cmd.split()
            if len(parts) == 2:
                try:
                    ms = int(parts[1])
                    if ms < 0:
                        self._log_message("throttle must be >= 0")
                    else:
                        manager.throttle_ms = ms
                        self._log_message(f"throttle set to {ms}ms")
                except ValueError:
                    self._log_message("usage: !throttle <ms>")
            else:
                self._log_message(f"throttle: {manager.throttle_ms}ms")
        elif cmd == "flush":
            count = manager.buffer_size
            if count > 0:
                manager.flush()
                self._log_message(f"flushed {count} buffered command(s)")
            else:
                self._log_message("buffer empty")
        else:
            self._log_message(
                f"unknown command '{
                    text}' — use !! to send literal '!', or use a valid command."
            )

    def _send_data(self) -> None:
        inp = self.query_one("#input", Input)
        text = inp.value
        if not text:
            return

        if text.startswith("!!"):
            text = text[1:]
        elif text.startswith("!"):
            inp.value = ""
            self._handle_command(text)
            return

        if not self._connected:
            self._log_message("no device connected")
            inp.value = ""
            return

        text = _unescape_escapes(text)

        suffix = ""
        echo = False
        for section in self.query_one("#newlineset", NewLineSet).query(ToggleSection):
            sw = section.query_one(Switch)
            if not sw.value:
                continue
            if r"\r" in section.label:
                suffix += "\r"
            elif r"\n" in section.label:
                suffix += "\n"
            elif "echo" in section.label:
                echo = True

        data = text + suffix
        try:
            manager.write(data.encode())
        except Exception as e:
            self._log_message(f"send failed: {e}")
            return
        if echo:
            self._append_data(data)
        inp.value = ""

    def _toggle_connect(self) -> None:
        if not self._connected:
            if manager.selected_device is None:
                self._log_message(
                    "no device selected – use 'select device' first.")
                return
            try:
                manager.connect()
            except Exception as e:
                self._log_message(f"connection failed: {e}")
        else:
            manager.disconnect()

    def on_unmount(self) -> None:
        manager.disconnect()

    def action_toggle_dark(self) -> None:
        pass


class StatusBar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("select device", id="selectbtn")
        yield Label("baud-rate:N/A\r\nport:N/A\r\ndevice:N/A", id="data")
        yield VerticalGroup(
            Label("th:off", id="throttledisplay"),
            Label("buf:0", id="bufcount"),
            id="throttle-buf-group",
        )

        yield NewLineSet(id="newlineset")
        yield Button("connect", id="conbtn")


class ToggleSection(HorizontalGroup):
    def __init__(self, name: str):
        self.label = name
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.label, shrink=True, id="sectionlabel")
        yield Switch(False, id="sectionswitch")


class NewLineSet(VerticalGroup):
    def compose(self) -> ComposeResult:
        yield ToggleSection(r" \r   ")
        yield ToggleSection(r" \n   ")
        yield ToggleSection(r" echo ")


class TopBar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Input(id="input")
        yield Button("send", id="send")


if __name__ == "__main__":
    app = SerialTui()
    app.run()
