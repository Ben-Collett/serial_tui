from pathlib import Path
from .parsers import Parser, TomllibParser, TomlkitParser, JsonParser


def detect_parser(path: Path) -> Parser | None:
    suffix = path.suffix.lower()
    if suffix == '.toml':
        try:
            import tomlkit
            return TomlkitParser()
        except ImportError:
            return TomllibParser()
    if suffix == '.json':
        return JsonParser()
    return None
