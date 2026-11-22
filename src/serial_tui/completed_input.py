from collections import deque

from rich.text import Text as RichText
from textual.app import App, ComposeResult
from textual.events import Key, Resize
from textual.widgets import Input, ListView, ListItem,  Static


class _SuggestionList(ListView):
    def __init__(self, on_selected):
        super().__init__()
        self._on_selected = on_selected

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._on_selected(event)


class CompletedInput(Input):
    """
    features:
        a drop down showing auto complete suggestions
        the ability to navigate through input history
        the ability to define custom suggestions and assign weght to them
    """

    def __init__(self, suggestions=None, max_height=6, max_width=40, history_size=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_suggestions = max_height
        self._max_width = max_width
        self._autocomplete_enabled = True
        self._set_suggestion_data(suggestions)
        self._current_filtered = []
        self._list_view = _SuggestionList(self._on_suggestion_selected)
        self._shown = False
        self._user_navigated = False
        self.history: deque = deque(maxlen=history_size)
        self.history_index: int | None = None
        self._suppress_suggestions = False

    def update_suggestion_overlay_size(self, max_width: int, max_height: int) -> None:
        self._max_width = max_width
        self._max_suggestions = max_height
        self._list_view.styles.width = max_width
        self._list_view.styles.max_height = max_height
        if self._shown:
            self._position_list()

    def set_autocomplete_enabled(self, val: bool) -> None:
        if val ^ self._autocomplete_enabled:
            self._toggle_autocomplete()

    def send(self, text: str) -> None:
        if text:
            self.history.append(text)
        self.history_index = None
        self.value = ""

    def update_history_size(self, size: int) -> None:
        new_history = deque(maxlen=size)
        items = list(self.history)
        if len(items) > size:
            items = items[-size:]
        for item in items:
            new_history.append(item)
        self.history = new_history
        if self.history_index is not None and self.history_index >= size:
            self.history_index = size - 1

    def history_up(self) -> None:
        if not self.history:
            return

        history_index = self.history_index
        if history_index is None:
            history_index = len(self.history) - 1
        else:
            history_index -= 1

        if history_index < 0:
            return

        self.history_index = history_index

        text = self.history[self.history_index]
        self._suppress_suggestions = True
        self.value = text
        self.cursor_position = len(text)

    def history_down(self) -> None:
        if not self.history:
            return
        history_index = self.history_index
        if history_index is None:
            return
        else:
            history_index += 1

        if history_index < 0:
            return
        if history_index >= len(self.history):
            self.history_index = None
            self.value = ""
            return

        self.history_index = history_index
        text = self.history[self.history_index]
        self._suppress_suggestions = True
        self.value = text
        self.cursor_position = len(text)

    def _toggle_autocomplete(self) -> None:
        self._autocomplete_enabled = not self._autocomplete_enabled
        if not self._autocomplete_enabled:
            self._hide_suggestions()

    @property
    def autocomplete_enabled(self) -> bool:
        return self._autocomplete_enabled

    def update_suggestions(self, raw_suggestions: list) -> None:
        self._set_suggestion_data(raw_suggestions)
        self._current_filtered = []
        if self._autocomplete_enabled and self.value:
            if self._update_suggestions(self.value):
                self._show_suggestions()
            else:
                self._hide_suggestions()

    def _set_suggestion_data(self, raw):
        if raw is None:
            raw = [
                "aab", "aac", "aad", "aae", "aaf", "abc",
                ("dhi", "hello there human person like this"),
                "dnone", ("dlong", "this is a super duper long description beldev it or not")]
        self._suggestion_data = []
        for s in raw:
            if isinstance(s, str):
                self._suggestion_data.append((s, None))
            else:
                self._suggestion_data.append(
                    (s[0], s[1] if len(s) > 1 else None))

    def on_mount(self) -> None:
        self.screen.mount(self._list_view)
        self._list_view.styles.position = "absolute"
        self._list_view.styles.layer = "overlay"
        self._list_view.styles.width = self._max_width
        self._list_view.styles.height = "auto"
        self._list_view.styles.max_height = self._max_suggestions
        self._list_view.styles.display = "none"

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._suppress_suggestions:
            self._suppress_suggestions = False
            return
        self.history_index = None
        if not self._autocomplete_enabled:
            return
        has_suggestions = self._update_suggestions(event.value)
        if has_suggestions and event.value:
            self._show_suggestions()
        else:
            self._hide_suggestions()

    def on_focus(self) -> None:
        if not self._autocomplete_enabled:
            return
        if self.value:
            if self._update_suggestions(self.value):
                self._show_suggestions()

    def on_blur(self) -> None:
        self._hide_suggestions()

    def key_down(self, event: Key) -> bool:
        if self._shown:
            event.stop()
            self._user_navigated = True
            self._highlight_next()
            return True
        self.history_down()
        event.stop()
        return True

    def key_up(self, event: Key) -> bool:
        if self._shown:
            event.stop()
            self._user_navigated = True
            self._highlight_prev()
            return True
        self.history_up()
        event.stop()
        return True

    def key_ctrl_k(self, event: Key) -> bool:
        if self._shown:
            event.stop()
            self._user_navigated = True
            self._highlight_prev()
            return True
        self.history_up()
        event.stop()
        return True

    def key_ctrl_j(self, event: Key) -> bool:
        if self._shown:
            event.stop()
            self._user_navigated = True
            self._highlight_next()
            return True
        self.history_down()
        event.stop()
        return True

    def key_tab(self, event: Key) -> bool:
        if not self._shown:
            return False
        event.stop()
        index = self._list_view.index if self._list_view.index is not None else 0
        item = self._list_view.children[index]
        self._on_suggestion_selected(ListView.Selected(
            self._list_view, item, index))
        return True

    def key_enter(self, event: Key) -> bool:
        if self._shown and self._user_navigated and self._list_view.index is not None:
            event.stop()
            item = self._list_view.children[self._list_view.index]
            self._on_suggestion_selected(ListView.Selected(
                self._list_view, item, self._list_view.index))
            return True
        if self._shown:
            self._hide_suggestions()
        return False

    def key_escape(self, event: Key) -> bool:
        if not self._shown:
            return False
        event.stop()
        self._hide_suggestions()
        return True

    def key_backspace(self, event: Key):
        """
        this is a hack to get around how textual handles
        inputs currently if the user types backpace without
        it will create a race condition when using
        highspeed devices like charchorder or my fuzzy chips program
        I am going to try to get a fix upstreamed.
        """
        self.action_delete_left()
        event.stop()

    def _get_filtered(self, value: str) -> list[tuple[str, str | None]]:
        lower_val = value.lower()
        matching = [
            (data, i) for i, data in enumerate(self._suggestion_data)
            if data[0].lower().startswith(lower_val)
        ]
        matching.sort(key=lambda x: (
            0 if x[0][0].startswith(value) else 1, x[1]))
        return [data for data, _ in matching]

    def _update_suggestions(self, value: str) -> bool:
        filtered = self._get_filtered(value)
        filtered_texts = [t for t, _ in filtered]
        if filtered_texts == self._current_filtered:
            return bool(self._list_view.children)

        self._current_filtered = filtered_texts
        self._list_view.clear()
        if not filtered:
            self._hide_suggestions()
            return False
        for text, desc in filtered:
            if desc:
                rich_text = RichText(text)
                rich_text.append("  ")
                rich_text.append(desc, style="dim")
                self._list_view.append(ListItem(Static(rich_text)))
            else:
                self._list_view.append(ListItem(Static(text)))
        self._user_navigated = False
        return True

    def _highlight_next(self) -> None:
        if self._list_view.index is None:
            self._list_view.index = 0
        else:
            self._list_view.index = min(
                len(self._list_view.children) - 1, self._list_view.index + 1
            )

    def _highlight_prev(self) -> None:
        if self._list_view.index is None:
            self._list_view.index = len(self._list_view.children) - 1
        else:
            self._list_view.index = max(0, self._list_view.index - 1)

    def _show_suggestions(self) -> None:
        if not self._list_view.children:
            self._hide_suggestions()
            return
        if self._shown:
            self._position_list()
            return
        self._shown = True
        self._position_list()
        self._list_view.styles.display = "block"

    def on_resize(self, event: Resize) -> None:
        if self._shown:
            self._position_list()

    def _position_list(self) -> None:
        cx, cy = self.cursor_screen_offset
        x = max(0, cx - 1)
        y = cy + 1
        self._list_view.styles.offset = (x, y)
        remaining = self.screen.size.width - x
        self._list_view.styles.width = min(self._max_width, remaining)
        remaining_height = self.screen.size.height - y
        self._list_view.styles.max_height = min(
            self._max_suggestions, remaining_height)

    def _hide_suggestions(self) -> None:
        if not self._shown:
            return
        self._shown = False
        self._list_view.styles.display = "none"
        self._list_view.index = None

    def _on_suggestion_selected(self, event: ListView.Selected) -> None:
        text = self._current_filtered[event.index]
        self.value = text
        self.cursor_position = len(text)
        self._hide_suggestions()
        self.focus()


class CompletedInputApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    CompletedInput {
        width: 40;
    }
    """

    def compose(self) -> ComposeResult:
        yield CompletedInput(placeholder="Type something...")


if __name__ == "__main__":
    app = CompletedInputApp()
    app.run()
