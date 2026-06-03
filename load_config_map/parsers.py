from pathlib import Path


class Parser:
    def parse(self, file: Path) -> dict:
        raise NotImplementedError()


class TomlkitParser(Parser):
    def parse(self, file: Path) -> dict:
        import tomlkit
        with open(file, 'rb') as f:
            return tomlkit.load(f)


class TomllibParser(Parser):
    def parse(self, file: Path) -> dict:
        import tomllib
        with open(file, 'rb') as f:
            return tomllib.load(f)


class JsonParser(Parser):
    def parse(self, file: Path) -> dict:
        import json
        with open(file) as f:
            return json.load(f)
