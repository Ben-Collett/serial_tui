from rich.text import Text as RichText
from textual.app import App, ComposeResult, RenderResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.geometry import Size
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Placeholder,  Static
from debug_utils import logger

ELLIPS = "..."


def get_text(keybindings, width, height, key_style=None, cmd_style=None) -> RichText:
    remaining_height = height
    out_text: RichText = RichText("", no_wrap=True, end="")
    current_width = 0
    i = 0
    while i < len(keybindings):
        key, cmd = keybindings[i]
        padded_key = f"{key} "
        needed_width = len(padded_key) + len(cmd)
        not_last_binding = i != len(keybindings) - 1

        if not_last_binding and remaining_height == 1:
            needed_width += 3  # " | ", the separator character and a space after it

        remaining_width = width - current_width
        can_not_fit_on_current_row = remaining_width <= needed_width

        if can_not_fit_on_current_row:
            if remaining_height == 1:
                out_text.append(ELLIPS)
                break
            else:
                out_text.remove_suffix(" | ")
                out_text.append("\n")
                remaining_height -= 1
                current_width = 0
                continue

        no_space_for_ellips_if_rendered = remaining_width - \
            needed_width < len(ELLIPS)

        if not_last_binding and no_space_for_ellips_if_rendered and remaining_height == 1:
            out_text.append(ELLIPS)
            break

        out_text.append(padded_key, key_style)
        current_width += len(padded_key)
        out_text.append(cmd, cmd_style)
        current_width += len(cmd)
        if not_last_binding:
            out_text.append(" | ")
            current_width += 3

        i += 1

    if not out_text:
        out_text.append("no keybindings detected")

    return out_text


def get_recommended_height(keybindings, width, max_height):
    return len(get_text(keybindings, width, max_height).split("\n"))


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

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        css_max_height = self.styles.max_height
        max_h = css_max_height.value if css_max_height is not None else 999
        recommended = get_recommended_height(self.keybindings, width, max_h)
        return min(recommended, max_h)

    def update_bindings(self, bindings: list[tuple[str, str]]):
        self.keybindings = bindings
        self.refresh(layout=True)

    def render(self) -> RenderResult:
        key_text_style = self.get_component_rich_style("footer-key--key")
        description_style = self.get_component_rich_style(
            "footer-key--description")

        rich_text = get_text(self.keybindings, self.size.width,
                             self.size.height, key_text_style, description_style)

        rich_text.stylize_before(self.rich_style)
        logger.log_debug(f"size={self.size}")
        logger.log_debug(f"content_size={self.content_size}")
        logger.log_debug(f"region={self.region}")
        for line in rich_text.split("\n"):
            logger.log_debug(repr(line.plain))
            logger.log_debug(len(line.plain))
        # lines = rich_text.split("\n")
        # raise Exception(lines)
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
