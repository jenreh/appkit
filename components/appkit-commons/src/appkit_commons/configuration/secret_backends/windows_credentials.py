"""Windows Credential Manager store backed by pywin32 (`win32cred`).

Secrets are generic credentials with the target name `<namespace>:<name>`.
"""

import logging
import sys
from typing import Any

from appkit_commons.configuration.secret_backends.base import (
    SecretNotFoundError,
    SecretStoreError,
)

logger = logging.getLogger(__name__)

ERROR_NOT_FOUND = 1168
MAX_BLOB_BYTES = 2560


def _load_win32cred() -> Any:
    try:
        import win32cred  # noqa: PLC0415  # ty: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Optional Windows dependencies are required to use "
            "SecretProvider.WINDOWS. Install 'appkit-commons[windows]' ('pywin32')."
        ) from exc
    return win32cred


def _is_not_found(exc: Exception) -> bool:
    return getattr(exc, "winerror", None) == ERROR_NOT_FOUND


def _decode_blob(blob: Any) -> str:
    if isinstance(blob, bytes):
        return blob.decode("utf-16-le")
    return str(blob)


class WindowsCredentialStore:
    def __init__(
        self,
        namespace: str,
        cred_module: Any | None = None,
        platform: str | None = None,
    ) -> None:
        if (platform or sys.platform) != "win32":
            raise SecretStoreError(
                "The Windows Credential Manager is only available on Windows."
            )
        self._namespace = namespace
        self._cred = cred_module or _load_win32cred()

    def _target(self, name: str) -> str:
        return f"{self._namespace}:{name}"

    def _read(self, name: str) -> dict[str, Any] | None:
        try:
            return self._cred.CredRead(
                Type=self._cred.CRED_TYPE_GENERIC, TargetName=self._target(name)
            )
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def exists(self, name: str) -> bool:
        return self._read(name) is not None

    def get(self, name: str) -> str:
        logger.debug("Reading secret %s from Windows Credential Manager", name)
        credential = self._read(name)
        if credential is None:
            raise SecretNotFoundError(
                f"Secret '{name}' not found in Windows Credential Manager "
                f"(target '{self._target(name)}')"
            )
        return _decode_blob(credential["CredentialBlob"])

    def set(self, name: str, value: str) -> None:
        if len(value.encode("utf-16-le")) > MAX_BLOB_BYTES:
            raise SecretStoreError(
                f"Secret '{name}' is too large for the Windows Credential Manager "
                f"(max {MAX_BLOB_BYTES} bytes as UTF-16)"
            )
        logger.debug("Writing secret %s to Windows Credential Manager", name)
        self._cred.CredWrite(
            {
                "Type": self._cred.CRED_TYPE_GENERIC,
                "TargetName": self._target(name),
                "UserName": self._namespace,
                "CredentialBlob": value,
                "Persist": self._cred.CRED_PERSIST_LOCAL_MACHINE,
            },
            0,
        )

    def delete(self, name: str) -> None:
        logger.debug("Deleting secret %s from Windows Credential Manager", name)
        try:
            self._cred.CredDelete(
                Type=self._cred.CRED_TYPE_GENERIC, TargetName=self._target(name)
            )
        except Exception as exc:
            if _is_not_found(exc):
                raise SecretNotFoundError(
                    f"Secret '{name}' not found in Windows Credential Manager"
                ) from exc
            raise

    def list_names(self) -> list[str]:
        prefix = f"{self._namespace}:"
        try:
            credentials = self._cred.CredEnumerate(Filter=f"{prefix}*", Flags=0)
        except Exception as exc:
            if _is_not_found(exc):
                return []
            raise
        return sorted(
            str(credential["TargetName"]).removeprefix(prefix)
            for credential in credentials or ()
            if str(credential["TargetName"]).startswith(prefix)
        )
