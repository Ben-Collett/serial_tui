from pathlib import Path
from .parsers import Parser
from .auto_detect_parser import detect_parser
from .utils import merge_dicts as _merge_dicts


def parse(path: Path, defaults: dict | None = None, parser_override: Parser | None = None) -> dict | None:
    """
    path is the path to the file to parse


    defaults, let you set missing values in the parsed map.
    if a key is not set in the map but it is set the parser_override
    then it will be set in the returned dict to the default value

    WARNING: for performance a shallow copy of defaults is used when setting
    when setting the values


    parser_override lets you force which parser you want to use.

    if it is not set then the parser will be auto detected.
    if it ends with .toml then tomlkit will be used unless
    it is detected that tomlkit is not installed then tomllib
    will be used

    if it ends with .json then the json parser will be used

    all parsing libraries are loaded lazily
    """
    parser = parser_override or detect_parser(path)

    if not parser:
        return None

    parsed = parser.parse(path)

    if defaults:
        _merge_dicts(parsed, defaults)
    return parsed
