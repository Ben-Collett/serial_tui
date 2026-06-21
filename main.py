import codecs
from collections.abc import Callable
from dataclasses import dataclass
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Button, Header, Input, Label, Switch
from custom_log import AutoScrollMode, CustomLog
from completed_input import CompletedInput
from device import Device
from my_footer import CustomFooter
from strings import not_reigistered_theme, unknown_command
from popups import SelectDeviceData, SelectDeviceScreen
from my_manager import manager
from events import DataEvent, Connect, Disconnect, ErrorEvent, SerialEvent, BufferUpdate
from config import (get_auto_scroll_duration, get_auto_complete_enabled,
                    get_auto_scroll_mode, get_command_descriptions_override,
                    get_commands_override, get_devices_config,
                    get_header_visible, get_footer_max_height, get_history_size,
                    get_keybindings, get_shorten_binding,
                    get_suggestion_overlay_max_height,
                    get_suggestion_overlay_max_width, get_theme)
from config_utils import load_config, get_themes_dir, theme_from_file
from constants import DEFAULT_THEME
from recommended_settings_resolver import RecommendedSettingsResolver


@dataclass
class Command:
    names: list[str]
    description: str
    callback: Callable[[str], None]


def _unescape_escapes(text: str) -> str:
    """Convert escape sequences like \\r, \\n into actual control chars.
    \\\\ -> \\, \\r -> \\r, \\n -> \\n, \\xNN -> hex byte, etc.
    Malformed sequences (trailing \\, \\x without hex) fall back to original."""
    try:
        return codecs.decode(text.encode("latin-1"), "unicode_escape")
    except (ValueError, SyntaxError):

        return text


# probably not the greatest this is stored external to the command declaration
GLOBAL_COMMANDS = ["rl", "reload", "reload_config", "q",
                   "quit", "p", "pallett", "command_pallett"]


class SerialTui(App):
    CSS_PATH = "main_screen.scss"

    # prevents default pallett binding
    COMMAND_PALETTE_BINDING = ""
    BINDINGS = [
        Binding("ctrl+q", "do_nothing"),
        Binding("ctrl+c", "do_nothing"),
    ]

    def __init__(self):
        super().__init__()
        self._connected = False
        self._resolver = RecommendedSettingsResolver()

        self.REAL_COMMANDS: list[Command] = [
            Command(["r"], r"toggle \r newline", self._cmd_toggle_r),
            Command(["n"], r"toggle \n newline", self._cmd_toggle_n),
            Command(["rl", "reload", "reload_config"],
                    r"reloads the config", self._cmd_reload),
            Command(["rn"], r"toggle both \r and \n", self._cmd_toggle_rn),
            Command(["ren"], r"toggle \r, \n and echo", self._cmd_toggle_ren),
            Command(["q", "quit"], r"terminates the program",
                    self._cmd_quit),
            Command(["e", "echo"], "toggle local echo", self._cmd_toggle_echo),
            Command(["p", "pallett", "command_pallett"], "shows command pallett",
                    self._cmd_pallett),
            Command(["toggle_connection", "c"], "toggles device connection",
                    self._cmd_toggle_connection),
            Command(["con", "connect"],
                    "connect to device", self._cmd_connect),
            Command(["dis", "disconnect"],
                    "disconnect from device", self._cmd_disconnect),
            Command(["s", "select", "select_device"], "open device selection",
                    self._cmd_prompt_select_device),
            Command(["clear", "l"], "clear output terminal", self._cmd_clear),
            Command(["th", "throttle"], "set or view throttle ms",
                    self._cmd_throttle),
            Command(["flush", "fl", "flush_buf"],
                    "flush buffered commands", self._cmd_flush),
            Command(["cmds"], "prints out all available commands to the output section",
                    self._cmd_print_cmds),
            Command(
                ["keys"], "prints all keybindings to the output section", self._cmd_print_keys),
            Command(
                ["device_info"], "prints selected device info to the output section", self._cmd_print_device),
            Command(["send"], "send data to device", self._cmd_send),
        ]

        self._real_command_map: dict[str, Command] = {}
        self._user_command_map: dict[str, str | list[str]] = {}
        self._command_completion_suggestions: list[tuple[str, str]] = []
        self._keybinding_map: dict[str, str | list[str]] = {}
        self._device_completion_suggestions: list[tuple[str, str]] = []
        self._footer = CustomFooter(keybindings=[])
        for _cmd in self.REAL_COMMANDS:
            for _name in _cmd.names:
                self._real_command_map[_name] = _cmd

    def _cmd_toggle_ren(self, *_):
        self._cmd_toggle_r()
        self._cmd_toggle_n()
        self._cmd_toggle_echo()

    def _cmd_quit(self, *_):
        exit()

    def _cmd_toggle_rn(self, *_):
        self._cmd_toggle_r()
        self._cmd_toggle_n()

    def _cmd_toggle_n(self, *_):
        self._toggle_newline(r"\n")

    def _cmd_toggle_echo(self, *_):
        self._toggle_newline("echo")

    def _cmd_toggle_r(self, *_):
        self._toggle_newline(r"\r")

    def _cmd_toggle_connection(self, *_):
        self._toggle_connect()

    def _cmd_connect(self, *_):
        self._connect()

    def _cmd_disconnect(self, *_):
        manager.disconnect()

    def _cmd_prompt_select_device(self, *_):
        self.push_screen(SelectDeviceScreen(
            self._resolver), self._device_selected)

    def _cmd_reload(self, *_):
        self.reload_config()

    def _cmd_pallett(self, *_):
        self.action_command_palette()

    def _cmd_print_keys(self, *_):
        self._print_keys()

    def _cmd_print_cmds(self, *_):
        self._print_cmds()

    def _cmd_print_device(self, *_):
        device = manager.selected_device
        self._print_device_info(device)

    def _get_user_command_description(self, cmd: str) -> str | None:
        real_cmd = self._real_command_map.get(cmd)
        if real_cmd is None:
            out = cmd  # cases like throttle 50 being a command
        else:
            out = real_cmd.description
        return out

    def notify_error(self, message: str) -> None:
        self.notify(message, severity="error", timeout=5)

    def compose(self) -> ComposeResult:
        yield Header()
        yield TopBar(id="topbar")
        yield CustomLog(id="output")
        yield StatusBar(id="statusbar")
        yield self._footer

    def on_mount(self) -> None:
        self.reload_config()
        manager.hook(self._handle_event)

    def update_themes(self):
        for file in get_themes_dir().glob("*.toml"):
            theme = theme_from_file(file)
            if theme is not None:
                self.register_theme(theme)

    def _default_commands(self):
        out = {}
        for command in self._real_command_map.keys():
            out[command] = command
        return out

    def _update_device_suggestions(self):
        device = manager.selected_device
        suggestions = []
        if device is not None:
            matched = self._resolver.get_device_settings(device)
            settings = matched[0]
            suggestions = settings.auto_complete_suggestions or []

        self._device_completion_suggestions = suggestions

    def _update_input_suggestions(self):
        suggestions = list(self._command_completion_suggestions)
        suggestions.extend(self._device_completion_suggestions)
        self.query_one("#input", CompletedInput).update_suggestions(
            suggestions)

    def _get_real_command_description(self, cmd: str) -> str:
        """
        takes a command and returns it's description
        from the command map
        if it is not in the command map it will return the original string
        this is to easily handle cases like 'th 50'
        """
        command = self._real_command_map.get(cmd)
        if command is None:
            return cmd  # cases like th 50
        return command.description

    def action_do_nothing(self, *_):
        """
        used to override default behavior of ctrl+c and ctrl+q
        """
        pass

    def _print_cmds(self):
        lines = []
        for name, cmd in self._user_command_map.items():
            if isinstance(cmd, str):
                description = self._get_user_command_description(
                    cmd)
                if description is None:
                    description = str(cmd)

            else:
                description = str(cmd)
            lines.append(f"!{name} -> {description}")
        lines.append("")
        lines.append("")
        self._append_data("\n".join(lines))

    def _print_device_info(self, device: Device | None):
        auto_complete = self._device_completion_suggestions
        if device is None:
            self._log_message("no selected device to print info of")
            return
        lines = []
        lines.append(f"name: {device.name}")
        lines.append(f"description: {device.description}")
        if len(auto_complete) > 1:
            lines.append("")  # extra new line
            lines.append("auto complete suggestions:")  # extra new line
            for key, description in self._device_completion_suggestions:
                lines.append(f"{key} -> {description}")
        lines.append("")  # extra new line
        self._append_data("\n".join(lines))

    def _print_keys(self):
        """
        prints the keybindings and there commands description to the output section
        if there is multiple commands then just print them 
        example:
            ctrl+p -> open command pallett
            ctrl+t -> fl, th 50
        """
        lines = []
        for key, val in self._keybinding_map.items():
            description = ""
            if isinstance(val, str):
                description = self._get_real_command_description(val)
            elif isinstance(val, list):
                description = ", ".join(val)
            else:
                self.notify_error("unexpected keybinding command type")
                description = str(val)
            lines.append(f"{key} -> {description}")

        if len(lines) == 0:
            lines.append("no set keybindings")
        else:
            lines.append("")
        lines.append("")

        self._append_data("\n".join(lines))

    def on_key(self, event):
        cmd_name = self._keybinding_map.get(event.key)
        if cmd_name is not None:
            self._screen_safe_execute_real_commands(cmd_name, "")
        event.stop()

    def _update_keybindings(self, config: dict) -> None:
        self._keybinding_map.clear()

        footer_bindings: list[tuple[str, str]] = []
        keybindings = get_keybindings(config)
        for keys, cmd_name in keybindings.items():
            if isinstance(cmd_name, list):
                cmds = cmd_name
                valid = True
                for cmd in cmds:
                    base_name = cmd.split(maxsplit=1)[0]
                    if self._real_command_map.get(base_name) is None:
                        self._log_message(
                            f"keybinding '{keys}': command '{cmd}' not found")
                        valid = False
                        break
                if not valid:
                    continue
                self._keybinding_map[keys] = cmds
                footer_bindings.append((keys, "["+", ".join(cmd_name)+"]"))
            else:
                base_name = cmd_name.split(maxsplit=1)[0]
                cmd = self._real_command_map.get(base_name)
                if cmd is None:
                    self._log_message(
                        f"keybinding '{keys}': command '{cmd_name}' not found")
                    continue
                self._keybinding_map[keys] = cmd_name
                footer_bindings.append((keys, cmd_name))

        if get_shorten_binding(config):
            footer_bindings = [(k.replace("ctrl+", "^"), v)
                               for k, v in footer_bindings]

        self._footer.update_bindings(footer_bindings)

    def reload_config(self):
        self.update_themes()
        config = load_config()

        self._user_command_map = get_commands_override(
            config) or self._default_commands()

        theme = get_theme(config)
        if theme not in self.available_themes:
            self.notify_error(not_reigistered_theme(theme, DEFAULT_THEME))
            theme = DEFAULT_THEME
        self.theme = theme

        autocomplete_enabled = get_auto_complete_enabled(config)
        self.query_one("#input", CompletedInput).set_autocomplete_enabled(
            autocomplete_enabled)

        self._resolver.auto_complete_enabled = autocomplete_enabled
        self._resolver.update(get_devices_config(config))

        self._update_device_suggestions()

        if autocomplete_enabled:
            description_override = get_command_descriptions_override(config)
            self._command_completion_suggestions = _make_user_command_completions(
                self._user_command_map, description_override, self._real_command_map, self.notify_error)
            self._update_input_suggestions()

        self._update_keybindings(config)

        header_visible = get_header_visible(config)
        self.query_one(Header).display = "block" if header_visible else "none"

        footer_max_height = get_footer_max_height(config)
        self._footer.styles.max_height = footer_max_height

        history_size = get_history_size(config)
        self.query_one("#input", CompletedInput).update_history_size(
            history_size)

        overlay_max_width = get_suggestion_overlay_max_width(config)
        overlay_max_height = get_suggestion_overlay_max_height(config)
        self.query_one("#input", CompletedInput).update_suggestion_overlay_size(
            overlay_max_width, overlay_max_height)

        auto_scroll_str = get_auto_scroll_mode(config)
        try:
            auto_scroll_mode = AutoScrollMode[auto_scroll_str]
        except KeyError:
            self.notify_error(
                f"Invalid auto_scroll value '{auto_scroll_str}', using 'bottom'")
            auto_scroll_mode = AutoScrollMode.bottom
        self.query_one("#output", CustomLog).auto_scroll = auto_scroll_mode

        auto_scroll_duration = get_auto_scroll_duration(config)
        self.query_one(
            "#output", CustomLog).auto_scroll_duration = auto_scroll_duration

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
        rl = self.query_one("#output", CustomLog)
        rl.write(msg)

    def _on_connected(self) -> None:
        self._connected = True
        dev = manager.selected_device
        if dev is None:
            self.notify_error(
                "Some how the device was none _on_connected. That shouldn't happen. \nCongratulations, you have discovered a bug.\n Let us know on the issue tracker especially if you found a away to reproduce the bug.")
            return
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
            self.push_screen(SelectDeviceScreen(
                self._resolver), self._device_selected)
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
        if data.recommend_settings is not None:
            rs = data.recommend_settings
            if data.settings_accepted:
                for section in self.query_one("#newlineset", NewLineSet).query(ToggleSection):
                    if r"\n" in section.label and rs.auto_new_line is not None:
                        section.query_one(Switch).value = rs.auto_new_line
                    elif r"\r" in section.label and rs.auto_return_carry is not None:
                        section.query_one(Switch).value = rs.auto_return_carry
                if rs.throttle_ms is not None:
                    manager.throttle_ms = rs.throttle_ms
                    self._update_buffer_display()
            if rs.auto_complete_suggestions:
                self._device_completion_suggestions = rs.auto_complete_suggestions
            else:
                self._device_completion_suggestions = []
        self._update_device_display(manager.selected_device)
        self._update_input_suggestions()

    def _update_device_display(self, dev: Device):
        self.query_one("#data", Label).update(
            f"baud-rate:{manager.baudrate}\r\nport:{dev.port}\r\ndevice:{dev.name}"
        )

    def _toggle_newline(self, check: str) -> None:
        for section in self.query_one("#newlineset", NewLineSet).query(ToggleSection):
            if check in section.label:
                sw = section.query_one(Switch)
                sw.value = not sw.value
                break

    def _cmd_clear(self, *_) -> None:
        self.query_one("#output", CustomLog).clear_content()

    def _cmd_throttle(self, args: str) -> None:
        if args:
            try:
                ms = int(args)
                if ms < 0:
                    self._log_message("throttle must be >= 0")
                else:
                    manager.throttle_ms = ms
                    self._update_buffer_display()
                    self._log_message(f"throttle set to {ms}ms")
            except ValueError:
                self._log_message("usage: !throttle <ms>")
        else:
            self._log_message(f"throttle: {manager.throttle_ms}ms")

    def _cmd_flush(self, *_) -> None:
        count = manager.buffer_size
        if count > 0:
            manager.flush()
            self._log_message(f"flushed {count} buffered command(s)")
        else:
            self._log_message("buffer empty")

    def _cmd_send(self, args: str) -> None:
        if not args:
            self._log_message("usage: !send <data>")
            return
        if not self._connected:
            self._log_message("no device connected")
            return
        text = _unescape_escapes(args)
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

    def _screen_safe_execute_real_commands(self, commands: str | list[str], args: str) -> None:
        """
        executes the real commands when you are on the main screen
        if you are off the main screen then only GLOBAL_COMMANDS can execute
        """
        if isinstance(commands, str):
            commands = [commands]
        if len(self.screen_stack) > 1:
            for command in commands:
                if command not in GLOBAL_COMMANDS:
                    return
        self._execute_real_commands(commands, args)

    def _execute_real_commands(self, commands: str | list[str], args: str) -> None:
        if isinstance(commands, str):
            commands = [commands]
        if len(self.screen_stack) > 1:
            for command in commands:
                if command not in GLOBAL_COMMANDS:
                    return

        for entry in commands:
            parts = entry.split(maxsplit=1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else args
            cmd = self._real_command_map.get(cmd_name)
            if cmd is None:
                self._log_message(f"real command '{cmd_name}' not found")
            else:
                cmd.callback(cmd_args)

    def _handle_user_command(self, text: str) -> None:
        text = text.lstrip("!")
        parts = text.split(maxsplit=1)
        if not parts:
            self.notify_error(
                "! is not a command — use !! to send a literal !")
            return
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        commands = self._user_command_map.get(name)
        if commands is not None:
            self._execute_real_commands(commands, args)
            return

        self.notify_error(unknown_command(f"!{name}"))

    def _send_data(self) -> None:
        inp = self.query_one("#input", CompletedInput)
        text = inp.value
        if not text:
            return

        inp.send(text)

        if text.startswith("!!"):
            text = text[1:]
        elif text.startswith("!"):
            self._handle_user_command(text)
            return

        if not self._connected:
            self._log_message("no device connected")
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

    def _toggle_connect(self) -> None:
        if not self._connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        """
        if already connected then disconnects and reconnects
        """
        if manager.selected_device is None:
            self._log_message(
                "no device selected – use 'select device' first.")
            return
        try:
            manager.connect()
        except Exception as e:
            self._log_message(f"connection failed: {e}")

    def _disconnect(self):
        if manager.selected_device is None:
            self._log_message(
                "no device selected – use 'select device' first.")
            return
        manager.disconnect()

    def on_unmount(self) -> None:
        manager.disconnect()

    def action_toggle_dark(self) -> None:
        pass

    def action_command(self, cmd_name: str) -> None:
        self._execute_real_commands(cmd_name, "")


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
        yield CompletedInput(id="input", suggestions=[])
        yield Button("send", id="send")


def _make_user_command_completions(user_commands: dict, description_override: dict, real_commands: dict, on_error: Callable) -> list[tuple[str, str]]:
    completion_suggestions: list[tuple[str, str]] = []
    for name, command in user_commands.items():
        original_name = name
        name = "!"+name
        if original_name in description_override:
            completion_suggestions.append(
                (name, description_override[original_name]))
        elif isinstance(command, str):
            cmd_name = command.split(maxsplit=1)[0]
            real_command = real_commands.get(cmd_name)
            if real_command is None:
                on_error(f"{command} is not a real command not adding")
                continue
            completion_suggestions.append(
                (name, real_command.description))
        else:
            descriptions = []
            for entry in command:
                cmd_name = entry.split(maxsplit=1)[0]
                cmd = real_commands.get(cmd_name)
                if cmd:
                    descriptions.append(cmd.description)
                else:
                    descriptions.append(entry)
            completion_suggestions.append((name, ", ".join(descriptions)))
    return completion_suggestions


if __name__ == "__main__":
    app = SerialTui()
    app.run()
