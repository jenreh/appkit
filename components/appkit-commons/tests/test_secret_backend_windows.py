"""Tests for the Windows Credential Manager store with a fake win32cred."""

import builtins
import sys
from typing import Any

import pytest

from appkit_commons.configuration.secret_backends.base import (
    SecretNotFoundError,
    SecretStoreError,
)
from appkit_commons.configuration.secret_backends.windows_credentials import (
    ERROR_NOT_FOUND,
    MAX_BLOB_BYTES,
    WindowsCredentialStore,
)


class FakeWinError(Exception):
    def __init__(self, winerror: int) -> None:
        super().__init__(winerror)
        self.winerror = winerror


class FakeWin32Cred:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    def __init__(self) -> None:
        self.credentials: dict[str, dict[str, Any]] = {}
        self.filters: list[str] = []

    def CredRead(self, Type: int, TargetName: str) -> dict[str, Any]:  # noqa: N802, N803
        assert Type == self.CRED_TYPE_GENERIC
        if TargetName not in self.credentials:
            raise FakeWinError(ERROR_NOT_FOUND)
        stored = dict(self.credentials[TargetName])
        stored["CredentialBlob"] = stored["CredentialBlob"].encode("utf-16-le")
        return stored

    def CredWrite(self, credential: dict[str, Any], flags: int) -> None:  # noqa: N802
        assert flags == 0
        self.credentials[credential["TargetName"]] = credential

    def CredDelete(self, Type: int, TargetName: str) -> None:  # noqa: N802, N803
        if TargetName not in self.credentials:
            raise FakeWinError(ERROR_NOT_FOUND)
        del self.credentials[TargetName]

    def CredEnumerate(self, Filter: str, Flags: int) -> tuple[dict[str, Any], ...]:  # noqa: N802, N803
        self.filters.append(Filter)
        prefix = Filter.removesuffix("*")
        found = tuple(
            {"TargetName": target}
            for target in self.credentials
            if target.startswith(prefix)
        )
        if not found:
            raise FakeWinError(ERROR_NOT_FOUND)
        return found


@pytest.fixture
def cred() -> FakeWin32Cred:
    return FakeWin32Cred()


@pytest.fixture
def store(cred: FakeWin32Cred) -> WindowsCredentialStore:
    return WindowsCredentialStore("myapp", cred_module=cred, platform="win32")


class TestWindowsCredentialStore:
    def test_rejects_other_platforms(self, cred: FakeWin32Cred) -> None:
        with pytest.raises(SecretStoreError, match="only available on Windows"):
            WindowsCredentialStore("myapp", cred_module=cred, platform="darwin")

    def test_set_and_get_round_trip(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        # Act
        store.set("db-password", "Grüße")

        # Assert
        written = cred.credentials["myapp:db-password"]
        assert written["UserName"] == "myapp"
        assert written["Persist"] == cred.CRED_PERSIST_LOCAL_MACHINE
        assert store.get("db-password") == "Grüße"
        assert store.exists("db-password") is True

    def test_get_missing(self, store: WindowsCredentialStore) -> None:
        with pytest.raises(SecretNotFoundError, match="myapp:nope"):
            store.get("nope")
        assert store.exists("nope") is False

    def test_get_string_blob(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        cred.CredRead = lambda **_: {"CredentialBlob": "as-str"}  # type: ignore[method-assign]
        assert store.get("x") == "as-str"

    def test_read_errors_other_than_not_found_propagate(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        def denied(**_: Any) -> None:
            raise FakeWinError(5)

        cred.CredRead = denied  # type: ignore[method-assign]
        with pytest.raises(FakeWinError):
            store.get("x")

    def test_rejects_too_large_values(self, store: WindowsCredentialStore) -> None:
        with pytest.raises(SecretStoreError, match="too large"):
            store.set("big", "x" * (MAX_BLOB_BYTES // 2 + 1))

    def test_delete(self, store: WindowsCredentialStore, cred: FakeWin32Cred) -> None:
        store.set("a", "1")
        store.delete("a")
        assert cred.credentials == {}

    def test_delete_missing(self, store: WindowsCredentialStore) -> None:
        with pytest.raises(SecretNotFoundError):
            store.delete("a")

    def test_delete_other_errors_propagate(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        def denied(**_: Any) -> None:
            raise FakeWinError(5)

        cred.CredDelete = denied  # type: ignore[method-assign]
        with pytest.raises(FakeWinError):
            store.delete("a")

    def test_list_names_filters_by_namespace(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        # Arrange
        store.set("b", "2")
        store.set("a", "1")
        cred.credentials["other:c"] = {"TargetName": "other:c"}

        # Act & Assert
        assert store.list_names() == ["a", "b"]
        assert cred.filters == ["myapp:*"]

    def test_list_names_empty(self, store: WindowsCredentialStore) -> None:
        assert store.list_names() == []

    def test_list_other_errors_propagate(
        self, store: WindowsCredentialStore, cred: FakeWin32Cred
    ) -> None:
        def denied(**_: Any) -> None:
            raise FakeWinError(5)

        cred.CredEnumerate = denied  # type: ignore[method-assign]
        with pytest.raises(FakeWinError):
            store.list_names()

    def test_missing_pywin32_names_the_extra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "win32cred":
                raise ImportError("no pywin32")
            return real_import(name, *args, **kwargs)

        monkeypatch.delitem(sys.modules, "win32cred", raising=False)
        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError, match=r"appkit-commons\[windows\]"):
            WindowsCredentialStore("myapp", platform="win32")
