import logging
import os
import re
from typing import Any

from appkit_commons.configuration.secret_backends.base import SecretNotFoundError

logger = logging.getLogger(__name__)

_INVALID_VAULT_CHARS = re.compile(r"[/_.]+")


def create_azure_client() -> Any:
    """Key Vault client authenticated through DefaultAzureCredential (az login)."""
    try:
        from azure.identity import (  # noqa: PLC0415
            DefaultAzureCredential,
        )
        from azure.keyvault.secrets import SecretClient  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Optional Azure dependencies are required to use SecretProvider.AZURE. "
            "Install 'appkit-commons[azure]' "
            "('azure-identity' and 'azure-keyvault-secrets')."
        ) from exc

    vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
    if not vault_url:
        raise RuntimeError(
            "Environment variable 'AZURE_KEY_VAULT_URL' must be set to use "
            "SecretProvider.AZURE"
        )
    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


def azure_secret_name(name: str, namespace: str | None) -> str:
    """`<namespace>-<name>` lowercased; Key Vault allows only letters, digits, -."""
    if not namespace:
        return name.lower()
    prefix = _INVALID_VAULT_CHARS.sub("-", namespace).strip("-")
    return f"{prefix}-{name}".lower() if prefix else name.lower()


class AzureKeyVaultBackend:
    def __init__(self, client: Any, namespace: str | None = None) -> None:
        self._client = client
        self._namespace = namespace

    def get(self, name: str) -> str:
        vault_name = azure_secret_name(name, self._namespace)
        logger.debug("Reading secret %s from Azure Key Vault", vault_name)
        try:
            secret = self._client.get_secret(vault_name)
        except Exception as exc:
            if type(exc).__name__ == "ResourceNotFoundError":
                raise SecretNotFoundError(
                    f"Secret '{name}' not found in Azure Key Vault"
                ) from exc
            raise
        if not secret.value:
            raise SecretNotFoundError(f"Secret '{name}' not found in Azure Key Vault")
        return str(secret.value)
