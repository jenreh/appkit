"""Secret backends: one strategy per SECRET_PROVIDER value."""

from appkit_commons.configuration.secret_backends.base import (
    SecretBackend,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)

LOCAL_STORE_PROVIDERS: frozenset[str] = frozenset({"macos", "windows"})


def create_local_store(provider: str, namespace: str) -> SecretStore:
    """Writable store on this machine for `macos` or `windows`."""
    if provider == "macos":
        from appkit_commons.configuration.secret_backends.macos_keychain import (  # noqa: PLC0415
            MacKeychainStore,
        )

        return MacKeychainStore(account=namespace)
    if provider == "windows":
        from appkit_commons.configuration.secret_backends.windows_credentials import (  # noqa: PLC0415
            WindowsCredentialStore,
        )

        return WindowsCredentialStore(namespace=namespace)
    raise SecretStoreError(
        f"'{provider}' is not a local secret store. "
        f"Use one of: {', '.join(sorted(LOCAL_STORE_PROVIDERS))}."
    )


__all__ = [
    "LOCAL_STORE_PROVIDERS",
    "SecretBackend",
    "SecretNotFoundError",
    "SecretStore",
    "SecretStoreError",
    "create_local_store",
]
