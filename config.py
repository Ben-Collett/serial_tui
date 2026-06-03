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
