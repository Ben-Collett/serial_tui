from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal

class KeyBinding(Static):
    def __init__(self, key: str, description: str):
        super().__init__()
        self.key = key
        self.description = description

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(self.key, classes="key"),
            Static(self.description, classes="desc"),
            classes="binding"
        )

class FooterBar(Horizontal):
    def compose(self) -> ComposeResult:
        yield KeyBinding("Ctrl+C", "Quit")
        yield KeyBinding("Ctrl+L", "Clear Output")
        yield KeyBinding("Enter", "Send")
        yield KeyBinding("Tab", "Focus Input")
