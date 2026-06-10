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

    COMPONENT_CLASSES = {
        "footer-key--key",
        "footer-key--description",
    }

    DEFAULT_CSS = """
    CustomFooter {
        .footer-key--key {
            color: $footer-key-foreground;
            background: $footer-key-background;
            text-style: bold;
        }
        .footer-key--description {
            color: $footer-description-foreground;
            background: $footer-description-background;
        }
    }
    """

    def __init__(self, keybindings: list[tuple[str, str]] | None):
        super().__init__()
        self.keybindings: list[tuple[str, str]] = keybindings or []

    def update_bindings(self, bindings: list[tuple[str, str]]):
        self.keybindings = bindings
        self.refresh()

    def render(self) -> RenderResult:
        width = self.size.width
        key_text_style = self.get_component_rich_style("footer-key--key")
        description_style = self.get_component_rich_style(
            "footer-key--description")

        rich_text = RichText("")
        current_width = 0
        i = 0
        while i < len(self.keybindings):
            key, cmd = self.keybindings[i]
            padded_key = f"{key} "
            needed_width = len(padded_key) + len(cmd) + 1
            not_last_binding = i != len(self.keybindings) - 1

            if not_last_binding:
                needed_width += 2  # "| ", the separator character and a space after it

            remaining_width = width - current_width
            can_not_fit_on_current_row = remaining_width <= needed_width
            if can_not_fit_on_current_row:
                rich_text.append(ELLIPS)
                break

            no_space_for_ellips_if_rendered = remaining_width - \
                needed_width < len(ELLIPS)

            if not_last_binding and no_space_for_ellips_if_rendered:
                rich_text.append(ELLIPS)
                break

            rich_text.append(padded_key, key_text_style)
            rich_text.append(f"{cmd} ", description_style)
            if not_last_binding:
                rich_text.append("| ")

            current_width += needed_width
            i += 1

        if not rich_text:
            rich_text = RichText("no keybindings detected")

        rich_text.stylize_before(self.rich_style)
        return rich_text


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
