import os
from enum import StrEnum
from functools import lru_cache
from typing import Final

from dotenv import load_dotenv

load_dotenv()


SECRET_PROVIDER: Final[str] = os.getenv("SECRET_PROVIDER", "local").lower()
SECRET: Final[str] = "secret:"  # noqa: S105


class SecretNotFoundError(Exception):
    pass


class SecretProvider(StrEnum):
    AZURE = "azure"
    LOCAL = "local"


@lru_cache(maxsize=1)
def _get_azure_client():
    try:
        from azure.identity import (  # type: ignore # noqa: PLC0415
            DefaultAzureCredential,
        )
        from azure.keyvault.secrets import SecretClient  # type: ignore # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Optional Azure dependencies are required to use SecretProvider.AZURE. "
            "Install 'azure-identity' and 'azure-keyvault-secrets'."
        ) from exc

    vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
    if not vault_url:
        raise RuntimeError(
            "Environment variable 'AZURE_KEY_VAULT_URL' must be set to use "
            "SecretProvider.AZURE"
        )
    credential = DefaultAzureCredential()
    return SecretClient(vault_url=vault_url, credential=credential)


def _get_secret_from_azure(key: str) -> str:
    client = _get_azure_client()
    secret = client.get_secret(key.lower())
    if not secret.value:
        raise SecretNotFoundError(f"Secret '{key}' not found in Azure Key Vault")
    return secret.value


def _get_secret_from_env(key: str) -> str:
    """
    Get secret from environment variables.

    This function supports multiple naming conventions:
    - Direct key lookup: key -> env[key]
    - Uppercase transformation: key -> env[key.upper()]
    - Dash-to-underscore: avui-db-user -> AVUI_DB_USER
    """
    # Try direct lookup first
    value = os.getenv(key)
    if value is not None:
        return value

    # Try uppercase
    value = os.getenv(key.upper())
    if value is not None:
        return value

    # Try dash-to-underscore + uppercase transformation
    transformed_key = key.replace("-", "_").upper()
    value = os.getenv(transformed_key)
    if value is not None:
        return value

    # Try dash-to-underscore + lowercase transformation
    value = os.getenv(transformed_key.lower())
    if value is not None:
        return value

    error_msg = (
        f"Secret '{key}' not found in environment variables. "
        f"Tried: {key}, {key.upper()}, {transformed_key}, {transformed_key.lower()}"
    )
    raise SecretNotFoundError(error_msg)


def get_secret(key: str) -> str:
    if SECRET_PROVIDER == SecretProvider.AZURE:
        return _get_secret_from_azure(key)
    return _get_secret_from_env(key)
