import re
from device import RecommendedDeviceSettings, Device
from config_utils import load_device_compleitions
from known_devices import charachorder


def _default_recommendation(device: Device):
    if "charachorder" in device.description.lower():
        return charachorder()
    return RecommendedDeviceSettings()


class RecommendedSettingsResolver:
    auto_complete_enabled: bool = True
    _devices: list[dict] = []

    def update(self, devices: list[dict]):
        self._devices = devices

    def get_device_settings(self,  device: Device) -> list[RecommendedDeviceSettings]:
        """
        get's recommended device settings matching the current device object
        if for some reason the device matches multiple patterns then they are all returned
        if none are matched then a default RecommendedDeviceSetting is returned
        using known patterns or just an empty RecommendedDeviceSettings object
        should always have at least one RecommendedDevice
        will read the device jsonl file matching the name of the device in the config if one exist
        """
        description = device.description
        devices = self._devices
        if not isinstance(devices, list):
            devices = []

        matched = []
        for dev_config in devices:
            if not isinstance(dev_config, dict):
                continue
            pattern = dev_config.get("description_pattern")
            if not isinstance(pattern, str):
                continue
            if not re.search(pattern, description):
                continue

            rs = RecommendedDeviceSettings(
                baud_rate=dev_config.get("baud_rate"),
                auto_new_line=dev_config.get("auto_n"),
                auto_return_carry=dev_config.get("auto_r"),
                throttle_ms=dev_config.get("throttle_ms"),
            )

            name = dev_config.get("name")
            if isinstance(name, str) and self.auto_complete_enabled:
                suggestions = load_device_compleitions(name)
                if suggestions:
                    rs.auto_complete_suggestions = suggestions

            matched.append(rs)

        if matched:
            return matched
        return [_default_recommendation(device)]
