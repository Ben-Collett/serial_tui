from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, HorizontalGroup
from textual.widgets import Button, Input, Label, ListView, ListItem
from device import Device, RecommendedDeviceSettings
from my_manager import manager


@dataclass
class SelectDeviceData:
    device: Device
    baud_rate: int
    recommend_settings: RecommendedDeviceSettings | None = None
    settings_accepted: bool = False


class SelectDeviceScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        self.devices = manager.get_devices()
        self._selected_device: Device | None = None
        self._selected_baudrate: int | None = None
        self._recommend_settings: RecommendedDeviceSettings | None = None
        self._settings_accepted: bool = False
        items = [
            ListItem(Label(f"{d.port}  {d.name}  {d.description}"))
            for d in self.devices
        ]
        yield Container(
            Label("Select a device:"),
            ListView(*items, id="device-list"),
            Button("Cancel", id="cancel"),
            id="popup",
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self.devices and event.list_view.index is not None:
            self._selected_device = self.devices[event.list_view.index]
            self._push_baud_rate_screen()

    def _push_baud_rate_screen(self):
        self.app.push_screen(BaudRateScreen(self._selected_device),
                             self._on_baud_rate_done)

    def _on_baud_rate_done(self, baudrate: int | None) -> None:
        if baudrate is None:
            return
        self._selected_baudrate = baudrate
        self._check_recommended_settings()

    def _check_recommended_settings(self):
        settings = self._selected_device.recommended_settings()
        if settings.auto_new_line is not None or settings.auto_return_carry is not None:
            self._recommend_settings = settings
            self.app.push_screen(RecommendedSettingsScreen(
                settings), self._on_settings_done)
        else:
            self._finalize()

    def _on_settings_done(self, result: bool | None) -> None:
        if result is None:
            self._push_baud_rate_screen()
            return
        self._settings_accepted = result
        self._finalize()

    def _finalize(self):
        self.dismiss(SelectDeviceData(
            device=self._selected_device,
            baud_rate=self._selected_baudrate,
            recommend_settings=self._recommend_settings,
            settings_accepted=self._settings_accepted,
        ))

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)

    def key_j(self) -> None:
        lv = self.query_one(ListView)
        if lv.index is not None and lv.index < len(lv) - 1:
            lv.index += 1

    def key_k(self) -> None:
        lv = self.query_one(ListView)
        if lv.index is not None and lv.index > 0:
            lv.index -= 1

    def key_l(self) -> None:
        lv = self.query_one(ListView)
        if self.devices and lv.index is not None:
            self._selected_device = self.devices[lv.index]
            self._push_baud_rate_screen()


class BaudRateScreen(ModalScreen):
    def __init__(self, device: Device):
        self.device = device
        self.standard_rates = [300, 1200, 2400,
                               9600, 19200, 38400, 57600, 115200]
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Label("Select baud rate:"),
                ListView(id="rate-list"),
                Button("Back", id="cancel"),
                id="list-view",
            ),
            Container(
                Label("Enter custom baud rate:"),
                Input(id="custom-input", placeholder="e.g. 9600"),
                Button("Back", id="cancel-custom"),
                id="custom-view",
            ),
            id="popup",
        )

    def on_mount(self) -> None:
        self.query_one("#custom-view").display = False
        self._show_list()

    def _get_rates(self):
        recommended = self.device.recommended_settings().baud_rate
        rates_set = set(self.standard_rates)
        all_rates = list(self.standard_rates)
        if recommended and recommended not in rates_set:
            all_rates.append(recommended)
            all_rates.sort()
        return all_rates, recommended

    def _show_list(self):
        all_rates, recommended = self._get_rates()
        items = []
        for rate in all_rates:
            label = str(rate)
            if rate == recommended:
                label += " (recommended)"
            items.append(ListItem(Label(label)))
        items.append(ListItem(Label("Custom baud rate...")))

        initial = all_rates.index(9600) if 9600 in all_rates else 0
        if recommended and recommended in all_rates:
            initial = all_rates.index(recommended)

        lv = self.query_one("#rate-list", ListView)
        lv.clear()
        for item in items:
            lv.append(item)
        lv.index = initial

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None:
            idx = event.list_view.index
            all_rates, _ = self._get_rates()
            if idx < len(all_rates):
                self.dismiss(all_rates[idx])
            else:
                self._show_custom_input()

    def _show_custom_input(self):
        self.query_one("#list-view").display = False
        self.query_one("#custom-view").display = True
        self.query_one("#custom-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-input":
            try:
                rate = int(event.input.value.strip())
                if rate > 0:
                    self.dismiss(rate)
            except ValueError:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("cancel", "cancel-custom"):
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_j(self) -> None:
        if not self.query_one("#list-view").display:
            return
        lv = self.query_one("#rate-list", ListView)
        if lv.index is not None and lv.index < len(lv) - 1:
            lv.index += 1

    def key_k(self) -> None:
        if not self.query_one("#list-view").display:
            return
        lv = self.query_one("#rate-list", ListView)
        if lv.index is not None and lv.index > 0:
            lv.index -= 1

    def key_l(self) -> None:
        if not self.query_one("#list-view").display:
            return
        lv = self.query_one("#rate-list", ListView)
        if lv.index is not None:
            idx = lv.index
            all_rates, _ = self._get_rates()
            if idx < len(all_rates):
                self.dismiss(all_rates[idx])
            else:
                self._show_custom_input()


class RecommendedSettingsScreen(ModalScreen):
    def __init__(self, settings: RecommendedDeviceSettings):
        self.settings = settings
        super().__init__()

    def compose(self) -> ComposeResult:
        lines = []
        if self.settings.auto_new_line is not None:
            val = "On" if self.settings.auto_new_line else "Off"
            lines.append(f"Auto new line (\\n): {val}")
        if self.settings.auto_return_carry is not None:
            val = "On" if self.settings.auto_return_carry else "Off"
            lines.append(f"Auto return carry (\\r): {val}")

        yield Container(
            Label("Recommended device settings:"),
            Label("\n".join(lines)),
            HorizontalGroup(
                Button("Back", id="back"),
                Button("Decline", id="decline"),
                Button("Accept", id="accept", variant="primary"),
            ),
            id="popup",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "accept":
            self.dismiss(True)
        elif event.button.id == "decline":
            self.dismiss(False)
        elif event.button.id == "back":
            self.dismiss(None)

    def key_a(self) -> None:
        self.dismiss(True)

    def key_A(self) -> None:
        self.dismiss(True)

    def key_d(self) -> None:
        self.dismiss(False)

    def key_D(self) -> None:
        self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(None)
