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
    return safe_get(config, str, DEFAULT_THEME, "appearance", "theme")


def get_auto_complete_enabled(config: dict):
    return safe_get(config, bool, True, "autocomplete", "enabled")


def get_commands_override(config: dict) -> dict[str, str | list[str]] | None:
    # TODO enforce typing
    return config.get("commands")


def get_command_descriptions_override(config: dict) -> dict[str, str]:
    # TODO enforce typing
    return config.get("command_descriptions") or {}


def get_devices_config(config: dict) -> list[dict]:
    return config.get("devices") or []
