import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, InitSettingsSource

PROJECT_ROOT = Path.cwd()
DEFAULT_PATH: Path = PROJECT_ROOT / "configuration"
DEFAULT_CONFIG_YAML: Path = Path("config.yaml")

logger = logging.getLogger(__name__)


class YamlConfigReader:
    def __init__(
        self,
        yaml_file_path: Path = DEFAULT_PATH,
        yaml_file: Path = DEFAULT_CONFIG_YAML,
        yaml_file_encoding: str = "utf-8",
    ):
        self.yaml_file_path = yaml_file_path
        self.yaml_file = yaml_file
        self.yaml_file_encoding = yaml_file_encoding
        self.yaml_file_prefix = yaml_file.stem
        self.yaml_file_suffix = yaml_file.suffix

    @classmethod
    def __merge(cls, master: dict, updates: dict) -> dict:
        """
        Deep merge two dictionaries
        """
        # Safety check for None values
        if updates is None:
            return master
        if master is None:
            return updates if updates is not None else {}

        for key in updates:  # noqa
            if (
                key in master
                and isinstance(master[key], dict)
                and isinstance(updates[key], dict)
            ):
                cls.__merge(master[key], updates[key])
            else:
                master[key] = updates[key]

        return master

    @classmethod
    @lru_cache
    def read_file(cls, file_path: Path, encoding: str = "utf-8") -> Any:
        try:
            with Path.open(file_path, "r", encoding=encoding) as file:
                result = yaml.safe_load(file)
                # Handle case where YAML file is empty or contains only comments
                return result if result is not None else {}
        except yaml.YAMLError as ex:
            raise ex
        except FileNotFoundError:
            logger.warning("Configuration file '%s' not found.", file_path)
            return {}

    def read_and_merge_files(self, profiles: list[str] | None) -> dict[str, Any]:
        base_config: dict = self.read_file(
            self.yaml_file_path / self.yaml_file, self.yaml_file_encoding
        )

        if profiles is None:
            return base_config

        # Load profiles
        merged_config = base_config
        for environment in profiles:
            merge_config = (
                self.yaml_file_path
                / f"{self.yaml_file_prefix}.{environment}{self.yaml_file_suffix}"
            )
            updates: dict = self.read_file(merge_config, self.yaml_file_encoding)
            merged_config = self.__merge(master=merged_config, updates=updates)

        return merged_config


class YamlConfigSettingsSource(InitSettingsSource):
    """This class is designed to load variables from a YAML file with inheritance.

    The YAML file is loaded from the path specified in the `yaml_file_path` attribute.
    By default, the configuration file should be named "config.yaml" and located in the
    specified path. The default directory where `config.yaml` files are stored is
    `configuration` in the project root.

    To extend or override the configuration, you can set e.g. a `PROFILES` environment
    variable. Additional YAML files should follow the naming convention
    `config.{profile}.yaml` and be stored in the same directory as the default
    configuration.

    **Important Note:** The order in which profiles are specified in the `profiles` list
    matters. Profile files will be loaded and merged in the order
    they are listed. E.g. if `profiles` is set to `dev,prod`, the `dev` profile will be
    loaded first after the default config, and the `prod` profile will be loaded second,
    with the `prod` profile overriding any values from the `default`and `dev` profile.

    When setting the `yaml_file` attribute, the class will search for profiles by
    splitting the file name and using the first part as the prefix. For instance, if
    `yaml_file` is set to `my_config.yaml`, the class will look for profiles in files
    named `my_config.{profile}.yaml`.

    Usage:
    ```python
    class BaseConfig(BaseSettings):
        model_config = SettingsConfigDict(extra="ignore", env_nested_delimiter="__")

        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> Tuple[PydanticBaseSettingsSource, ...]:
            profiles: List[str] = [
                profile.strip() for profile in os.getenv("PROFILES", "").split(",")
            ]

            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
                YamlConfigSettingsSource(settings_cls, profiles=profiles),
            )
    ```
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        profiles: list[str] | None = None,
        yaml_file_path: Path = DEFAULT_PATH,
        yaml_file: Path = DEFAULT_CONFIG_YAML,
        yaml_file_encoding: str = "utf-8",
    ):
        reader = YamlConfigReader(
            yaml_file_path=yaml_file_path,
            yaml_file=yaml_file,
            yaml_file_encoding=yaml_file_encoding,
        )
        self.yaml_data = reader.read_and_merge_files(profiles=profiles)
        # Filter out YAML entries with no matching Pydantic field
        valid_yaml_data = {
            k: v for k, v in self.yaml_data.items() if k in settings_cls.model_fields
        }
        super().__init__(settings_cls, valid_yaml_data)

    def __repr__(self) -> str:
        return f"YamlConfigSettingsSource(yaml_data={self.yaml_data!r})"
