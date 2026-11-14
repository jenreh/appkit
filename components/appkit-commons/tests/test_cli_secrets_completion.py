"""Tests for shell completion of the appkit-secrets CLI."""

from pathlib import Path
from typing import Any

import click
import pytest
import yaml
from typer.testing import CliRunner

from appkit_commons.cli import secrets_app
from appkit_commons.cli.secrets_app import (
    COMPLETE_VAR,
    PROG_NAME,
    CompletionShell,
    app,
    complete_provider,
    detect_completion_shell,
)
from appkit_commons.configuration.secret_backends.base import SecretStoreError


class ListingStore:
    def __init__(self, names: list[str]) -> None:
        self.names = names

    def list_names(self) -> list[str]:
        return sorted(self.names)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    def fake_create(provider: str, namespace: str) -> ListingStore:
        calls.append((provider, namespace))
        return ListingStore(["mn-db-host", "mn-db-user", "other"])

    monkeypatch.setattr(secrets_app, "create_local_store", fake_create)
    monkeypatch.delenv("SECRET_PROVIDER", raising=False)
    monkeypatch.delenv("SECRET_NAMESPACE", raising=False)
    return calls


def complete(line: str, **env: str) -> list[str]:
    """Run the CLI the way the zsh completion script does and parse the result."""
    result = CliRunner().invoke(
        app,
        [],
        prog_name=PROG_NAME,
        env={COMPLETE_VAR: "complete_zsh", "_TYPER_COMPLETE_ARGS": line, **env},
    )
    assert result.exit_code == 0, result.output
    return [
        line.split('"')[1].split(":")[0]
        for line in result.output.splitlines()
        if '"' in line
    ]


def write_config(directory: Path, file: str, data: dict[str, Any]) -> None:
    directory.mkdir(exist_ok=True)
    (directory / file).write_text(yaml.safe_dump(data), encoding="utf-8")


class TestCompletionValues:
    def test_commands(self, opened: list[tuple[str, str]]) -> None:
        assert complete("appkit-secrets ") == [
            "add",
            "update",
            "delete",
            "list",
            "env",
            "check",
            "completion",
        ]

    def test_provider(self, opened: list[tuple[str, str]]) -> None:
        assert complete("appkit-secrets -p ") == ["macos", "windows"]
        assert complete_provider("w") == ["windows"]

    def test_delete_completes_stored_names_from_options(
        self, opened: list[tuple[str, str]]
    ) -> None:
        names = complete("appkit-secrets -p windows -n myapp delete mn-")

        assert names == ["mn-db-host", "mn-db-user"]
        assert opened == [("windows", "myapp")]

    def test_env_skips_names_already_given(self, opened: list[tuple[str, str]]) -> None:
        assert complete("appkit-secrets -p macos env mn-db-user ") == [
            "mn-db-host",
            "other",
        ]

    def test_add_suggests_configured_but_missing_names(
        self,
        opened: list[tuple[str, str]],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        write_config(
            tmp_path / "configuration",
            "config.yaml",
            {"db": {"host": "secret:mn-db-host", "pw": "secret:mn-db-password"}},
        )
        write_config(
            tmp_path / "configuration", "config.prod.yaml", {"x": "secret:mn-prod"}
        )
        monkeypatch.chdir(tmp_path)

        # Act & Assert
        assert complete("appkit-secrets -p macos add mn-") == [
            "mn-db-password",
            "mn-prod",
        ]

    def test_profiles_complete_after_last_comma(
        self,
        opened: list[tuple[str, str]],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for profile in ("local", "prod", "docker_test"):
            write_config(tmp_path / "configuration", f"config.{profile}.yaml", {})
        monkeypatch.chdir(tmp_path)

        assert complete("appkit-secrets check --profiles ") == [
            "docker_test",
            "local",
            "prod",
        ]
        assert complete("appkit-secrets check --profiles local,") == [
            "local,docker_test",
            "local,prod",
        ]

    def test_profiles_use_given_config_dir(
        self, opened: list[tuple[str, str]], tmp_path: Path
    ) -> None:
        write_config(tmp_path, "config.staging.yaml", {})

        line = f"appkit-secrets check --config-dir {tmp_path} --profiles s"
        assert complete(line) == ["staging"]

    def test_store_errors_complete_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_create(*_: Any) -> Any:
            raise SecretStoreError("locked")

        monkeypatch.setattr(secrets_app, "create_local_store", failing_create)

        assert complete("appkit-secrets -p macos delete ") == []
        assert complete("appkit-secrets -p macos add ") == []
        assert complete("appkit-secrets -p azure env ") == []


class TestCompletionCommand:
    @pytest.mark.parametrize(
        ("shell", "marker"),
        [
            ("zsh", "compdef _appkit_secrets_completion appkit-secrets"),
            ("bash", "complete -o default -F _appkit_secrets_completion"),
            ("fish", "complete --command appkit-secrets"),
            ("powershell", "Register-ArgumentCompleter"),
        ],
    )
    def test_prints_script(self, shell: str, marker: str) -> None:
        result = CliRunner().invoke(app, ["completion", shell])

        assert result.exit_code == 0, result.output
        assert marker in result.output
        assert COMPLETE_VAR in result.output

    def test_shell_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")

        result = CliRunner().invoke(app, ["completion"])

        assert "#compdef appkit-secrets" in result.output

    def test_does_not_need_a_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def failing_create(*_: Any) -> Any:
            raise AssertionError("store must not be opened")

        monkeypatch.setattr(secrets_app, "create_local_store", failing_create)
        monkeypatch.setattr(secrets_app.sys, "platform", "linux")

        result = CliRunner().invoke(app, ["completion", "bash"])

        assert result.exit_code == 0

    def test_unknown_shell_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/tcsh")

        result = CliRunner().invoke(app, ["completion"])

        assert result.exit_code == 1
        assert "Cannot detect the shell" in result.output

    def test_install_completion_option_exists(self) -> None:
        result = CliRunner().invoke(app, ["--help"])

        # Typer forces Rich styling on GitHub Actions; compare the plain text.
        assert "--install-completion" in click.unstyle(result.output)


class TestDetectCompletionShell:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/bin/zsh", CompletionShell.zsh),
            ("/usr/local/bin/bash", CompletionShell.bash),
            ("/opt/homebrew/bin/fish", CompletionShell.fish),
            (r"C:\\Program Files\\PowerShell\\7\\pwsh.exe", CompletionShell.pwsh),
        ],
    )
    def test_from_path(self, path: str, expected: CompletionShell) -> None:
        assert detect_completion_shell(path, platform="darwin") == expected

    def test_windows_without_shell_is_powershell(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SHELL", raising=False)
        assert detect_completion_shell(platform="win32") is CompletionShell.powershell
