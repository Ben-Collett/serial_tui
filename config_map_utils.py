from dataclasses import dataclass


@dataclass
class DeviceSettings:
    baud_rate: int | None
    description_regex: str | None


def get_device_settings(config_map: dict):
    return
