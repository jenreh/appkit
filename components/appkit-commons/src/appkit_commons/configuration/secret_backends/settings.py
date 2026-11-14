"""Environment variables shared by all secret backends and the CLI."""

import os
from typing import Final

SECRET_PROVIDER_ENV: Final[str] = "SECRET_PROVIDER"  # noqa: S105
SECRET_NAMESPACE_ENV: Final[str] = "SECRET_NAMESPACE"  # noqa: S105
DEFAULT_PROVIDER: Final[str] = "local"
DEFAULT_LOCAL_NAMESPACE: Final[str] = "appkit"


def provider_name() -> str:
    """The configured provider, lowercased; empty or unset means local."""
    value = os.getenv(SECRET_PROVIDER_ENV, "").strip().lower()
    return value or DEFAULT_PROVIDER


def namespace() -> str | None:
    """The shared namespace, or None when unset or blank."""
    value = os.getenv(SECRET_NAMESPACE_ENV, "").strip()
    return value or None


def local_namespace(value: str | None = None) -> str:
    """Namespace for local stores, which always need one to list their items."""
    chosen = (value or "").strip() or namespace()
    return chosen or DEFAULT_LOCAL_NAMESPACE
