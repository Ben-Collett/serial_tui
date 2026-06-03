from config_manager import ConfigManager
from load_config_map import parse
from pathlib import Path
import json
from constants import PROGRAM_NAME, CONFIG_FILE_NAME, DEVICES_DIR_NAME, DEVICES_EXTENSION

_NAME_KEY = "n"
_DESCRIPTION_KEY = "d"
_manager = ConfigManager(PROGRAM_NAME)


def get_config_dir() -> Path:
    """
    if a directory called config is in the same directory as the script return that
    otherwise return the config directory determend by serial tui
    """
    local_config = Path(__file__).parent / "config"
    if local_config.is_dir():
        return local_config
    return _manager.find_config_dir_path()


def load_config() -> dict:
    return read_config(get_config_toml())


def read_config(file_path: Path) -> dict:
    out = None
    try:
        out = parse(file_path)
    except FileNotFoundError:
        pass
    return out or {}


def _parse_json(txt: str) -> dict:
    try:
        return json.loads(txt)
    except Exception:
        return {}


def _load_device_compleitions(device_name: str) -> dict[str, str]:
    device_file = get_device_config(device_name)
    out: dict[str, str] = {}
    try:
        content = device_file.read_text()
        for line in content:
            data = _parse_json(line)
            if data == {}:
                continue
            if _NAME_KEY not in data:
                print("no name in device line", line)
                continue
            out[data[_NAME_KEY]] = data.get(_DESCRIPTION_KEY) or ""
    except FileNotFoundError:
        pass
    return out


def get_device_dir() -> Path:
    return get_config_dir()/DEVICES_DIR_NAME


def get_config_toml() -> Path:
    return get_config_dir()/CONFIG_FILE_NAME


def get_device_config(device_name: str) -> Path:
    return get_device_dir()/f"{device_name}{DEVICES_EXTENSION}"
