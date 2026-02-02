import logging
import os
from collections.abc import Callable
from typing import Any

from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from appkit_commons.configuration.secret_provider import SECRET, get_secret
from appkit_commons.configuration.yaml import YamlConfigSettingsSource

logger = logging.getLogger(__name__)


def _starts_with_secret(s: str) -> bool:
    return s.lower().startswith(SECRET)


def _replace_value_if_secret(
    key: str, value: Any, secret_function: Callable[[str], str]
) -> Any:
    if isinstance(value, list):
        return [_replace_value_if_secret(key, item, secret_function) for item in value]

    if not isinstance(value, str):
        return value

    value = str(value)
    if not _starts_with_secret(value):
        return value

    # remove SECRET from value
    # 1. secret:mysecret -> mysecret
    secret_len = len(SECRET)
    value = value[secret_len:]
    key = value if len(value) > 0 else key
    return secret_function(key)


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_nested_delimiter="__")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        profiles: list[str] = [
            profile.strip() for profile in os.getenv("PROFILES", "").split(",")
        ]

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls, profiles=profiles),
        )

    @model_validator(mode="before")
    @classmethod
    def secret_update(cls, values: dict[str, Any]) -> dict[str, Any]:
        return {
            k: _replace_value_if_secret(k, v, get_secret) for k, v in values.items()
        }
