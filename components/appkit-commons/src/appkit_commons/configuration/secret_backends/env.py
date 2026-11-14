import os

from appkit_commons.configuration.secret_backends.base import SecretNotFoundError


class EnvSecretBackend:
    """
    Read secrets from environment variables.

    Supported naming conventions:
    - Direct key lookup: key -> env[key]
    - Uppercase transformation: key -> env[key.upper()]
    - Dash-to-underscore: avui-db-user -> AVUI_DB_USER (and lowercase variant)
    """

    def get(self, name: str) -> str:
        transformed = name.replace("-", "_").upper()
        candidates = (name, name.upper(), transformed, transformed.lower())
        for candidate in candidates:
            value = os.getenv(candidate)
            if value is not None:
                return value

        raise SecretNotFoundError(
            f"Secret '{name}' not found in environment variables. "
            f"Tried: {', '.join(candidates)}"
        )
