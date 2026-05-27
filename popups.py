from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Button, Label, ListView, ListItem
from my_manager import manager


class SelectDeviceScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        self.devices = manager.get_devices()
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
            self.dismiss(self.devices[event.list_view.index])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
