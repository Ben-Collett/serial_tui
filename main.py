import codecs
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, Right, VerticalGroup
from textual.widgets import Button, Footer, Header, Input, Label, Switch, TextArea
from popups import SelectDeviceScreen
from my_manager import manager
from events import DataEvent, Connect, Disconnect, ErrorEvent, SerialEvent


def _unescape_escapes(text: str) -> str:
    """Convert escape sequences like \\r, \\n into actual control chars.
    \\\\ -> \\, \\r -> \\r, \\n -> \\n, \\xNN -> hex byte, etc.
    Malformed sequences (trailing \\, \\x without hex) fall back to original."""
    try:
        return codecs.decode(text.encode("latin-1"), "unicode_escape")
    except (ValueError, SyntaxError):
        return text


class SerailTui(App):
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

    def _append_data(self, msg: str) -> None:
        ta = self.query_one("#output", TextArea)
        ta.insert(msg, location=ta.document.end)

    def _on_connected(self) -> None:
        self._connected = True
        dev = manager.selected_device
        self.query_one("#data", Label).update(
            f"baud-rate:{manager.baudrate}\r\nport:{dev.port}\r\ndevice:{dev.name}"
        )
        self.query_one("#conbtn", Button).label = "disconnect"

    def _on_disconnected(self) -> None:
        self._connected = False
        self.query_one("#data", Label).update("disconnected")
        self.query_one("#conbtn", Button).label = "connect"

    def _on_error(self, err: str) -> None:
        ta = self.query_one("#output", TextArea)
        ta.insert(f"\n[error] {err}\n", location=ta.document.end)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "selectbtn":
            self.push_screen(SelectDeviceScreen(), self._device_selected)
        elif event.button.id == "send":
            self._send_data()
        elif event.button.id == "conbtn":
            self._toggle_connect()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._send_data()

    def _device_selected(self, device) -> None:
        if device is None:
            return
        manager.selected_device = device
        self.query_one("#data", Label).update(
            f"baud-rate:{manager.baudrate}\r\nport:{device.port}\r\ndevice:{device.name}"
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
        else:
            self._append_data(
                f"Unknown command '{
                    text}' — use !! to send literal '!', or use a valid command.\n"
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
            self._append_data(f"Send failed: {e}\n")
            return
        if echo:
            self._append_data(data)
        inp.value = ""

    def _toggle_connect(self) -> None:
        if not self._connected:
            if manager.selected_device is None:
                self._append_data(
                    "No device selected – use 'select device' first.\n")
                return
            try:
                manager.connect()
            except Exception as e:
                self._append_data(f"Connection failed: {e}\n")
        else:
            manager.disconnect()

    def on_unmount(self) -> None:
        manager.disconnect()

    def action_toggle_dark(self) -> None:
        pass


class StatusBar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("select device", id="selectbtn")
        yield Label("baud-rate:115200\r\nport:/dev/TCAM0\r\ndevice:unknown", id="data")
        yield Right(NewLineSet(id="newlineset"))
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
        yield ToggleSection(r"\r   ")
        yield ToggleSection(r"\n   ")
        yield ToggleSection(r"echo ")


class TopBar(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Input(id="input")
        yield Button("send", id="send")


if __name__ == "__main__":
    app = SerailTui()
    app.run()
