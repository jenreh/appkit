"""macOS Keychain store backed by the `security` command line tool.

Items are generic passwords with service = secret name and account = namespace.
Values are written as hex through stdin of `security -i`, so they never appear
in process listings or need shell quoting.
"""

import logging
import re
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from appkit_commons.configuration.secret_backends.base import (
    SecretNotFoundError,
    SecretStoreError,
)

logger = logging.getLogger(__name__)

SECURITY = "/usr/bin/security"
ITEM_NOT_FOUND = 44
_ATTRIBUTE = re.compile(r'^\s+"(acct|svce)"<blob>=(.*)$')
_CLASS = re.compile(r"^class: ")

Runner = Callable[..., subprocess.CompletedProcess[Any]]


def _decode_attribute(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("0x"):
        hex_part = raw.split()[0][2:]
        return bytes.fromhex(hex_part).decode("utf-8", errors="replace").rstrip("\0")
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:  # noqa: PLR2004
        return raw[1:-1]
    return None


def parse_dump(output: str, account: str) -> list[str]:
    """Service names of generic passwords owned by `account` in a keychain dump."""
    names: set[str] = set()
    is_generic = False
    item: dict[str, str | None] = {}

    def flush() -> None:
        if is_generic and item.get("acct") == account and item.get("svce"):
            names.add(str(item["svce"]))

    for line in output.splitlines():
        if line.startswith("keychain: "):
            flush()
            is_generic, item = False, {}
        elif _CLASS.match(line):
            is_generic = line.strip() == 'class: "genp"'
        elif match := _ATTRIBUTE.match(line):
            item[match.group(1)] = _decode_attribute(match.group(2))
    flush()
    return sorted(names)


def _parse_password(stderr: str) -> str:
    for line in stderr.splitlines():
        if not line.startswith("password:"):
            continue
        raw = line[len("password:") :].strip()
        if raw.startswith("0x"):
            return bytes.fromhex(raw.split()[0][2:]).decode("utf-8")
        if raw.startswith('"') and raw.endswith('"'):
            return raw[1:-1]
        return ""
    raise SecretStoreError("Unexpected output from 'security find-generic-password'")


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class MacKeychainStore:
    def __init__(
        self,
        account: str,
        runner: Runner = subprocess.run,
        platform: str | None = None,
    ) -> None:
        if (platform or sys.platform) != "darwin":
            raise SecretStoreError("The macOS Keychain is only available on macOS.")
        self._account = account
        self._run = runner

    def _security(
        self, *args: str, stdin: str | None = None
    ) -> subprocess.CompletedProcess[Any]:
        return self._run(
            [SECURITY, *args],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    def _find_args(self, name: str) -> list[str]:
        return ["-a", self._account, "-s", name]

    def exists(self, name: str) -> bool:
        result = self._security("find-generic-password", *self._find_args(name))
        return result.returncode == 0

    def get(self, name: str) -> str:
        logger.debug("Reading secret %s from macOS Keychain", name)
        result = self._security("find-generic-password", *self._find_args(name), "-g")
        if result.returncode == ITEM_NOT_FOUND:
            raise SecretNotFoundError(
                f"Secret '{name}' not found in macOS Keychain "
                f"(account '{self._account}')"
            )
        self._raise_on_error(result, "read", name)
        return _parse_password(result.stderr)

    def set(self, name: str, value: str) -> None:
        logger.debug("Writing secret %s to macOS Keychain", name)
        command = (
            f"add-generic-password -a {_quote(self._account)} -s {_quote(name)} "
            f"-U -X {value.encode('utf-8').hex()}\n"
        )
        result = self._security("-i", stdin=command)
        self._raise_on_error(result, "write", name)
        if not self.exists(name):
            raise SecretStoreError(f"Could not write secret '{name}' to the Keychain")

    def delete(self, name: str) -> None:
        logger.debug("Deleting secret %s from macOS Keychain", name)
        result = self._security("delete-generic-password", *self._find_args(name))
        if result.returncode == ITEM_NOT_FOUND:
            raise SecretNotFoundError(f"Secret '{name}' not found in macOS Keychain")
        self._raise_on_error(result, "delete", name)

    def list_names(self) -> list[str]:
        result = self._security("dump-keychain")
        self._raise_on_error(result, "list", "*")
        return parse_dump(result.stdout, self._account)

    @staticmethod
    def _raise_on_error(
        result: subprocess.CompletedProcess[Any], action: str, name: str
    ) -> None:
        if result.returncode != 0:
            raise SecretStoreError(
                f"Could not {action} secret '{name}' in the macOS Keychain "
                f"(security exit code {result.returncode})"
            )
