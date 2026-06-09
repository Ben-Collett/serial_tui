from typing import Container
from rich.text import Text as RichText
from textual.app import App, ComposeResult, RenderResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Placeholder,  Static
from debug_utils import logger

ELLIPS = "..."


class CustomFooter(Widget):
    """
    features:
        display keybindings in a row
        allowed to span multiple rows
        use ellipse if overflow
    """

    def __init__(self, keybindings: list[tuple[str, str]] | None):
        super().__init__()
        self.keybindings: list[tuple[str, str]] = keybindings or []

    def update_bindings(self, bindings: list[tuple[str, str]]):
        self.keybindings = bindings
        self.refresh()

    def render(self) -> RenderResult:
        width = self.size.width
        # height = self.size.height
        lines = ""
        current_width = 0
        i: int = 0
        while i < len(self.keybindings):
            key, cmd = self.keybindings[i]
            needed_width = len(key)+len(cmd)+1  # +1 for a space
            not_last_binding = i != len(self.keybindings)-1
            if not_last_binding:
                needed_width += 3  # an extra space between bindings
            remaining_width = width - current_width
            if remaining_width < needed_width:
                lines += ELLIPS
                break
            # if where not the last binding
            # and we cannot fit an ellipse after displaying
            # then we should just display the elispe instead
            if not_last_binding and remaining_width-needed_width < len(ELLIPS):
                lines += ELLIPS
                break

            lines += f"[b]{key}[/b] {cmd}"
            if not_last_binding:
                lines += " | "

            current_width += needed_width
            i += 1

        if lines == "":
            lines = "no keybindings detected"
        return lines


class CompletedInputApp(App):
    CSS = """
    Vertical {
        height: 100%;
    }
    CustomFooter {
        height: 1;
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        bindings = [
            ("ctrl+h", "connect"),
            ("ctrl+f", "flush me"),
            ("ctrl+s", "select device"),
            ("ctrl+r", "toggling r"),
            ("ctrl+n", "toggling n"),
            ("ctrl+e", "toggling echo"),
            ("ctrl+g", "reloading the config man"),
            ("ctrl+p", "opending the command pallet"),
            ("ctrl+l", "clearing all the output, what am I your janitor?"),
            ("ctrl+c", "quitting this"),
        ]

        yield Vertical(
            Placeholder(),
            CustomFooter(keybindings=bindings),)


if __name__ == "__main__":
    app = CompletedInputApp()
    app.run()
