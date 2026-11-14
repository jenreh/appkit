"""Find the `secret:` references a YAML configuration needs."""

from pathlib import Path
from typing import Any

from appkit_commons.configuration.secret_provider import SECRET
from appkit_commons.configuration.yaml import DEFAULT_CONFIG_YAML, YamlConfigReader


def collect_secret_names(data: Any, key: str | None = None) -> set[str]:
    """
    Every secret name referenced by `secret:<name>` values in `data`.

    An empty name after the prefix stands for the YAML key, the same rule
    `BaseConfig` applies when it resolves the value.
    """
    names: set[str] = set()
    if isinstance(data, dict):
        for child_key, value in data.items():
            names |= collect_secret_names(value, str(child_key))
    elif isinstance(data, list):
        for item in data:
            names |= collect_secret_names(item, key)
    elif isinstance(data, str) and data.lower().startswith(SECRET):
        name = data[len(SECRET) :].strip() or key
        if name:
            names.add(name)
    return names


def parse_profiles(value: str | None) -> list[str]:
    return [profile.strip() for profile in (value or "").split(",") if profile.strip()]


def required_secret_names(
    config_dir: Path, profiles: list[str], all_profiles: bool = False
) -> set[str]:
    """Secrets needed by `config.yaml` merged with `profiles`, or by every file."""
    reader = YamlConfigReader(yaml_file_path=config_dir)
    if not all_profiles:
        return collect_secret_names(reader.read_and_merge_files(profiles))

    stem, suffix = DEFAULT_CONFIG_YAML.stem, DEFAULT_CONFIG_YAML.suffix
    files = [config_dir / DEFAULT_CONFIG_YAML, *config_dir.glob(f"{stem}.*{suffix}")]
    names: set[str] = set()
    for file in files:
        names |= collect_secret_names(reader.read_file(file))
    return names
