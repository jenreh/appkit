import os
from enum import StrEnum
from functools import lru_cache
from typing import Any, Final

from dotenv import load_dotenv

from appkit_commons.configuration.secret_backends import (
    SecretNotFoundError,
    create_local_store,
    settings,
)
from appkit_commons.configuration.secret_backends.aws_ssm import (
    AwsSsmBackend,
    create_ssm_client,
)
from appkit_commons.configuration.secret_backends.azure import (
    AzureKeyVaultBackend,
    create_azure_client,
)
from appkit_commons.configuration.secret_backends.env import EnvSecretBackend

load_dotenv()


SECRET_PROVIDER: Final[str] = os.getenv("SECRET_PROVIDER", "local").lower()
SECRET: Final[str] = "secret:"  # noqa: S105

__all__ = [
    "SECRET",
    "SECRET_PROVIDER",
    "SecretNotFoundError",
    "SecretProvider",
    "get_secret",
]


class SecretProvider(StrEnum):
    AZURE = "azure"
    LOCAL = "local"
    AWS_SSM = "aws_ssm"
    MACOS = "macos"
    WINDOWS = "windows"


@lru_cache(maxsize=1)
def _get_azure_client() -> Any:
    return create_azure_client()


@lru_cache(maxsize=1)
def _get_ssm_client() -> Any:
    return create_ssm_client()


def _get_secret_from_azure(key: str) -> str:
    client = _get_azure_client()
    return AzureKeyVaultBackend(client, settings.namespace()).get(key)


def _get_secret_from_aws_ssm(key: str) -> str:
    client = _get_ssm_client()
    return AwsSsmBackend(client, settings.namespace()).get(key)


def _get_secret_from_local_store(provider: str, key: str) -> str:
    return create_local_store(provider, settings.local_namespace()).get(key)


def _get_secret_from_env(key: str) -> str:
    return EnvSecretBackend().get(key)


def _get_secret_provider() -> str:
    return settings.provider_name()


def _resolve_provider() -> SecretProvider:
    name = _get_secret_provider()
    try:
        return SecretProvider(name)
    except ValueError:
        allowed = ", ".join(provider.value for provider in SecretProvider)
        raise ValueError(
            f"Unknown SECRET_PROVIDER '{name}'. Allowed values: {allowed}"
        ) from None


def get_secret(key: str) -> str:
    match _resolve_provider():
        case SecretProvider.AZURE:
            return _get_secret_from_azure(key)
        case SecretProvider.AWS_SSM:
            return _get_secret_from_aws_ssm(key)
        case SecretProvider.MACOS | SecretProvider.WINDOWS as provider:
            return _get_secret_from_local_store(provider.value, key)
        case _:
            return _get_secret_from_env(key)
