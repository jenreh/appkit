"""Tests for the macOS Keychain store (the `security` tool is mocked)."""

import os
import subprocess
import sys
import uuid
from typing import Any

import pytest

from appkit_commons.configuration.secret_backends.base import (
    SecretNotFoundError,
    SecretStoreError,
)
from appkit_commons.configuration.secret_backends.macos_keychain import (
    ITEM_NOT_FOUND,
    SECURITY,
    MacKeychainStore,
    parse_dump,
)

DUMP = """keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="mn-db-user"
    "acct"<blob>="appkit"
    "svce"<blob>="mn-db-user"
keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    "acct"<blob>=0x6170706B6974  "appkit"
    "svce"<blob>=0x6D6E2D64622D70617373776F726400  "mn-db-password\\000"
keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    "acct"<blob>="someone-else"
    "svce"<blob>="foreign"
keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: "inet"
attributes:
    "acct"<blob>="appkit"
    "svce"<blob>="internet-password"
keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    "acct"<blob>="appkit"
    "svce"<blob>=<NULL>
keychain: "/Users/me/Library/Keychains/login.keychain-db"
version: 512
class: 0x00000010
attributes:
    0x00000001 <blob>="certificate"
"""


class FakeSecurity:
    """Records `security` invocations and replays scripted results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.results: list[subprocess.CompletedProcess[str]] = []

    def queue(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.results.append(
            subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)
        )

    def __call__(self, args: list[str], **kwargs: Any) -> Any:
        self.calls.append({"args": args, **kwargs})
        return self.results.pop(0) if self.results else self.result_ok()

    @staticmethod
    def result_ok() -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")


@pytest.fixture
def security() -> FakeSecurity:
    return FakeSecurity()


@pytest.fixture
def store(security: FakeSecurity) -> MacKeychainStore:
    return MacKeychainStore(account="appkit", runner=security, platform="darwin")


class TestParseDump:
    def test_lists_generic_passwords_of_account(self) -> None:
        assert parse_dump(DUMP, "appkit") == ["mn-db-password", "mn-db-user"]

    def test_other_account(self) -> None:
        assert parse_dump(DUMP, "someone-else") == ["foreign"]

    def test_empty_dump(self) -> None:
        assert parse_dump("", "appkit") == []


class TestMacKeychainStore:
    def test_rejects_other_platforms(self) -> None:
        with pytest.raises(SecretStoreError, match="only available on macOS"):
            MacKeychainStore(account="appkit", platform="linux")

    def test_get_plain_password(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        # Arrange
        security.queue(stderr='password: "p@ss \\"x\\""\n')

        # Act
        value = store.get("mn-db-password")

        # Assert
        assert value == 'p@ss \\"x\\"'
        assert security.calls[0]["args"] == [
            SECURITY,
            "find-generic-password",
            "-a",
            "appkit",
            "-s",
            "mn-db-password",
            "-g",
        ]

    def test_get_hex_password(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        hex_value = "Grüße\nzwei".encode().hex().upper()
        security.queue(stderr=f'password: 0x{hex_value}  "Gr\\303\\274..."\n')

        assert store.get("x") == "Grüße\nzwei"

    def test_get_empty_password(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue(stderr="password: \n")
        assert store.get("x") == ""

    def test_get_unexpected_output(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue(stderr="something else\n")
        with pytest.raises(SecretStoreError, match="Unexpected output"):
            store.get("x")

    def test_get_missing_item(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue(returncode=ITEM_NOT_FOUND)
        with pytest.raises(SecretNotFoundError, match="account 'appkit'"):
            store.get("missing")

    def test_get_other_failure(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue(returncode=51)
        with pytest.raises(SecretStoreError, match="exit code 51"):
            store.get("x")

    def test_exists(self, store: MacKeychainStore, security: FakeSecurity) -> None:
        security.queue(returncode=0)
        security.queue(returncode=ITEM_NOT_FOUND)

        assert store.exists("a") is True
        assert store.exists("b") is False

    def test_set_sends_value_only_through_stdin(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        # Arrange
        secret = 'top "secret" \\ value'
        security.queue()  # security -i
        security.queue()  # exists check

        # Act
        store.set("mn-db-password", secret)

        # Assert
        write = security.calls[0]
        assert write["args"] == [SECURITY, "-i"]
        assert all(secret not in arg for arg in write["args"])
        assert secret not in write["input"]
        assert write["input"] == (
            'add-generic-password -a "appkit" -s "mn-db-password" '
            f"-U -X {secret.encode().hex()}\n"
        )

    def test_set_verifies_the_item_exists(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue()  # security -i reports success
        security.queue(returncode=ITEM_NOT_FOUND)  # but the item is missing

        with pytest.raises(SecretStoreError, match="Could not write"):
            store.set("x", "value")

    def test_delete(self, store: MacKeychainStore, security: FakeSecurity) -> None:
        store.delete("x")
        assert security.calls[0]["args"] == [
            SECURITY,
            "delete-generic-password",
            "-a",
            "appkit",
            "-s",
            "x",
        ]

    def test_delete_missing(
        self, store: MacKeychainStore, security: FakeSecurity
    ) -> None:
        security.queue(returncode=ITEM_NOT_FOUND)
        with pytest.raises(SecretNotFoundError):
            store.delete("x")

    def test_list_names(self, store: MacKeychainStore, security: FakeSecurity) -> None:
        security.queue(stdout=DUMP)
        assert store.list_names() == ["mn-db-password", "mn-db-user"]
        assert security.calls[0]["args"] == [SECURITY, "dump-keychain"]


@pytest.mark.skipif(
    sys.platform != "darwin" or os.getenv("APPKIT_KEYCHAIN_IT") != "1",
    reason="Real Keychain round trip; set APPKIT_KEYCHAIN_IT=1 on macOS",
)
@pytest.mark.parametrize(
    "value",
    ['Grüße "quoted" \\ backslash', 'ascii "quoted" \\ back $x', "multi\nline"],
)
def test_real_keychain_round_trip(value: str) -> None:
    store = MacKeychainStore(account=f"appkit-it-{uuid.uuid4().hex[:8]}")
    name = "roundtrip"
    try:
        store.set(name, value)
        assert store.exists(name)
        assert store.get(name) == value
        assert store.list_names() == [name]
    finally:
        if store.exists(name):
            store.delete(name)
    assert not store.exists(name)
