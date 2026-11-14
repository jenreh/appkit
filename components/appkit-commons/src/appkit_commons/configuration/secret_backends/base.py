from typing import Protocol


class SecretNotFoundError(Exception):
    pass


class SecretStoreError(Exception):
    """A local secret store cannot be used or rejected an operation."""


class SecretBackend(Protocol):
    def get(self, name: str) -> str:
        """Return the secret value or raise SecretNotFoundError."""
        ...


class SecretStore(SecretBackend, Protocol):
    """A writable store on the developer machine (Keychain, Credential Manager)."""

    def exists(self, name: str) -> bool: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None:
        """Remove the secret or raise SecretNotFoundError."""
        ...

    def list_names(self) -> list[str]: ...
