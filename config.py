from typing import Type

from constants import DEFAULT_THEME


def safe_get(config: dict,  typ: Type, default, *keys):
    val = config
    for key in keys:
        val = val.get(key)
        if val is None:
            break
    if not isinstance(val, typ):
        return default
    return val


def get_theme(config: dict) -> str:
    return safe_get(config, str, DEFAULT_THEME, "ui", "theme")


def get_auto_complete_enabled(config: dict):
    return safe_get(config, bool, True, "autocomplete", "enabled")


def get_suggestion_overlay_max_width(config: dict) -> int:
    return safe_get(config, int, 40, "autocomplete", "suggestion_overlay_max_width")


def get_suggestion_overlay_max_height(config: dict) -> int:
    return safe_get(config, int, 9, "autocomplete", "suggestion_overlay_max_height")


def get_commands_override(config: dict) -> dict[str, str | list[str]] | None:
    # TODO enforce typing
    return config.get("commands")


def get_command_descriptions_override(config: dict) -> dict[str, str]:
    # TODO enforce typing
    return config.get("command_descriptions") or {}


def get_devices_config(config: dict) -> list[dict]:
    return config.get("devices") or []


def get_header_visible(config: dict) -> bool:
    return safe_get(config, bool, True, "ui", "header_visible")


def get_footer_max_height(config: dict) -> int | None:
    return safe_get(config, int, 2, "ui", "footer_max_height")


def get_shorten_binding(config: dict) -> bool:
    return safe_get(config, bool, False, "ui", "shorten_binding")


def get_auto_scroll_mode(config: dict) -> str:
    return safe_get(config, str, "bottom", "ui", "auto_scroll")


def get_animate_auto_scroll(config: dict) -> bool:
    return safe_get(config, bool, False, "ui", "animate_auto_scroll")


def get_history_size(config: dict) -> int:
    return safe_get(config, int, 100, "history", "size")


# TODO: force  to be dict[str,str|list[str]]
def get_keybindings(config: dict) -> dict:
    DEFAULT_BINDINGS = {
        "ctrl+s": "select_device",
        "ctrl+l": "clear",
        "ctrl+r": "r",
        "ctrl+n": "n",
        "ctrl+e": "echo",
        "ctrl+g": "reload_config",
        "ctrl+h": "toggle_connection",
        "ctrl+f": "flush_buf",
        "ctrl+p": "command_pallett",
        "ctrl+c": "quit",
    }
    return safe_get(config, dict, DEFAULT_BINDINGS, "keybindings")
