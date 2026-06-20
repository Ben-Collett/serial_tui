from __future__ import annotations
from enum import Enum, auto
from textual.widgets import TextArea
from textual.document._document import Selection
from textual.reactive import Reactive, reactive


class AutoScrollMode(Enum):
    never = auto()
    always = auto()
    bottom = auto()


class CustomTextArea(TextArea):
    """A TextArea with controllable auto-scrolling behavior.

    Suppresses the default cursor-following scroll that normal TextArea
    performs on every selection change, and provides append/scroll control
    for use as a scrollable text display with proper line wrapping.
    """

    auto_scroll: Reactive[AutoScrollMode] = reactive(AutoScrollMode.bottom)
    """Auto-scroll mode controlling behavior when text is appended."""

    animate_auto_scroll: Reactive[bool] = reactive(False)
    """Whether to animate the auto-scroll transition."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("read_only", True)
        super().__init__(*args, **kwargs)

    def _watch_selection(
        self, previous_selection: Selection, selection: Selection
    ) -> None:
        """Override to suppress automatic cursor-scrolling on selection change."""
        if not self.is_mounted:
            return

        self.app.clear_selection()

        cursor_location = selection.end
        cursor_row, cursor_column = cursor_location

        try:
            character = self.document[cursor_row][cursor_column]
        except IndexError:
            character = ""

        match_location = self.find_matching_bracket(character, cursor_location)
        self._matching_bracket_location = match_location
        if match_location is not None:
            self._recompute_cursor_offset()
            _, offset_y = self._cursor_offset
            self.refresh_lines(offset_y)

        self.app.cursor_position = self.cursor_screen_offset
        if previous_selection != selection:
            self.post_message(self.SelectionChanged(selection, self))

    def append_text(self, text: str) -> None:
        """Append text to the end of the document.

        Behavior depends on ``auto_scroll``:
        - ``always``: always scroll to the bottom.
        - ``bottom``: scroll to the bottom only if the user was already
          at the bottom.
        - ``never``: never auto-scroll.

        Args:
            text: The text to append.
        """
        was_at_bottom = self.is_vertical_scroll_end
        scroll_y = self.scroll_y
        end = self.document.end
        self.insert(text, end)
        should_scroll = (
            self.auto_scroll == AutoScrollMode.always
            or (self.auto_scroll == AutoScrollMode.bottom and was_at_bottom)
        )

        if should_scroll:
            if self.animate_auto_scroll:
                self.animate("scroll_y", self.max_scroll_y, duration=0.3)
            else:
                self.scroll_y = self.max_scroll_y
                self.scroll_target_y = self.max_scroll_y
        elif self.scroll_y != scroll_y:
            self.scroll_y = scroll_y


class CustomLog(CustomTextArea):
    def clear_content(self):
        self.clear()

    def write(self, msg: str) -> None:
        self.append_text(msg)

    def log_message(self, msg: str) -> None:
        self.append_text(f"SerialTui: {msg}\n")
