import platform as _platform
import os as _os
from pathlib import Path


class _PlatformWrapper:
    def get_env(self, name: str):
        return _os.getenv(name)

    def mkdir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)

    def exists(self, path: Path):
        return path.exists()

    @property
    def _is_on_windowns(self) -> bool:
        return _platform.system() == "Windows"

    @property
    def _is_on_linux(self) -> bool:
        return _platform.system() == "Linux"

    @property
    def _sudo_id(self):
        return _os.getenv("SUDO_UID")

    @property
    def _is_on_mac(self) -> bool:
        return _platform.system() == "Darwin"


class ConfigManager:
    def __init__(
        self,
        project_name: str,
        path_override_variable_name: str | None = None,
        _platform_wrapper=None,  # only for testing
    ):
        self.project_name: str = project_name
        self.path_override_variable_name = path_override_variable_name
        self._platform_wrapper: _PlatformWrapper = (
            _platform_wrapper if _platform_wrapper else _PlatformWrapper()
        )

    def config_dir_exists(self) -> bool:
        return self._platform_wrapper.exists(self.find_config_dir_path())

    def config_file_exists(self, file_name: str) -> bool:
        return self._platform_wrapper.exists(self.find_config_file(file_name))

    def create_config_dir(self):
        self._platform_wrapper.mkdir(self.find_config_dir_path())

    def create_config_file(self, file_name: str):
        config_dir = self.find_config_dir_path()
        self._platform_wrapper.mkdir(config_dir)

        config_file = config_dir / file_name
        if not config_file.exists():
            config_file.touch()

    def find_config_dir_path(self) -> Path:
        platform = self._platform_wrapper

        if self.path_override_variable_name:
            env = platform.get_env(self.path_override_variable_name)
            if env:
                return Path(env).expanduser()

        if platform._is_on_linux:
            return self._linux_dir_path
        if platform._is_on_windowns:
            return self._windows_config_path
        if platform._is_on_mac:
            return self._macos_config_path

        raise RuntimeError("Unsupported platform")

    def find_config_file(self, file_name: str) -> Path:
        return self.find_config_dir_path() / file_name

    @property
    def _macos_config_path(self) -> Path:
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / self.project_name
        )

    @property
    def _windows_config_path(self) -> Path:
        appdata = self._platform_wrapper.get_env("APPDATA")
        if not appdata:
            # extremely rare, but a safe fallback
            appdata = Path.home() / "AppData" / "Roaming"
        return Path(appdata) / self.project_name

    @property
    def _linux_dir_path(self) -> Path:
        program_name = self.project_name
        platform_wrapper = self._platform_wrapper
        sudo_uid = platform_wrapper._sudo_id

        if sudo_uid:
            # Script was run via sudo → use original user's home
            import pwd as _pwd
            pw = _pwd.getpwuid(int(sudo_uid))
            home = Path(pw.pw_dir)
        else:
            home = Path.home()

        config_home = platform_wrapper.get_env("XDG_CONFIG_HOME")
        if not config_home:
            config_home = home / ".config"

        return Path(config_home).joinpath(program_name).expanduser()
