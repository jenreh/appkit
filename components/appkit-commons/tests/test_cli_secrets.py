"""Tests for the appkit-secrets CLI with an in-memory store."""

import builtins
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from appkit_commons.cli import secrets as cli_entry
from appkit_commons.cli import secrets_app
from appkit_commons.cli.secrets_app import (
    Shell,
    app,
    env_var_name,
    export_line,
    resolve_provider,
)
from appkit_commons.configuration.secret_backends.base import (
    SecretNotFoundError,
    SecretStoreError,
)


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def exists(self, name: str) -> bool:
        return name in self.values

    def get(self, name: str) -> str:
        if name not in self.values:
            raise SecretNotFoundError(f"Secret '{name}' not found")
        return self.values[name]

    def set(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        if name not in self.values:
            raise SecretNotFoundError(f"Secret '{name}' not found")
        del self.values[name]

    def list_names(self) -> list[str]:
        return sorted(self.values)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MemoryStore:
    memory = MemoryStore()
    opened: list[tuple[str, str]] = []

    def fake_create(provider: str, namespace: str) -> MemoryStore:
        opened.append((provider, namespace))
        return memory

    monkeypatch.setattr(secrets_app, "create_local_store", fake_create)
    monkeypatch.delenv("SECRET_PROVIDER", raising=False)
    monkeypatch.delenv("SECRET_NAMESPACE", raising=False)
    monkeypatch.delenv("PROFILES", raising=False)
    memory.opened = opened  # type: ignore[attr-defined]
    return memory


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def invoke(runner: CliRunner, *args: str, stdin: str | None = None) -> Any:
    return runner.invoke(app, ["--provider", "macos", *args], input=stdin)


class TestResolveProvider:
    def test_explicit_local_store(self) -> None:
        assert resolve_provider("Windows") == "windows"

    def test_explicit_cloud_provider_is_rejected(self) -> None:
        with pytest.raises(SecretStoreError, match="only manages local stores"):
            resolve_provider("azure")

    def test_uses_local_secret_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "windows")
        assert resolve_provider(None, platform="darwin") == "windows"

    def test_falls_back_to_platform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        assert resolve_provider(None, platform="darwin") == "macos"
        assert resolve_provider(None, platform="win32") == "windows"

    def test_unknown_platform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SECRET_PROVIDER", raising=False)
        with pytest.raises(SecretStoreError, match="No local secret store"):
            resolve_provider(None, platform="linux")


class TestExportFormatting:
    def test_env_var_name(self) -> None:
        assert env_var_name("mn-db.user") == "MN_DB_USER"

    def test_posix(self) -> None:
        assert export_line("db-pw", "it's $x", Shell.posix) == (
            "export DB_PW='it'\"'\"'s $x'"
        )

    def test_powershell(self) -> None:
        assert export_line("db-pw", "it's", Shell.powershell) == (
            "$env:DB_PW = 'it''s'"
        )


class TestCrudCommands:
    def test_add_from_stdin(self, runner: CliRunner, store: MemoryStore) -> None:
        # Act
        result = invoke(runner, "add", "mn-db-password", "--stdin", stdin="s3cret\n")

        # Assert
        assert result.exit_code == 0, result.output
        assert store.values == {"mn-db-password": "s3cret"}
        assert "s3cret" not in result.output
        assert store.opened == [("macos", "appkit")]  # type: ignore[attr-defined]

    def test_add_with_prompt(self, runner: CliRunner, store: MemoryStore) -> None:
        result = invoke(runner, "add", "api-key", stdin="abc\nabc\n")

        assert result.exit_code == 0, result.output
        assert store.values == {"api-key": "abc"}

    def test_add_existing_fails(self, runner: CliRunner, store: MemoryStore) -> None:
        store.values["api-key"] = "old"

        result = invoke(runner, "add", "api-key", "--stdin", stdin="new")

        assert result.exit_code == 1
        assert "already exists" in result.output
        assert store.values["api-key"] == "old"

    def test_add_empty_value_fails(self, runner: CliRunner, store: MemoryStore) -> None:
        result = invoke(runner, "add", "api-key", "--stdin", stdin="\n")

        assert result.exit_code == 1
        assert "must not be empty" in result.output

    def test_invalid_name(self, runner: CliRunner, store: MemoryStore) -> None:
        result = invoke(runner, "add", "bad name!", "--stdin", stdin="x")

        assert result.exit_code != 0
        assert store.values == {}

    def test_update(self, runner: CliRunner, store: MemoryStore) -> None:
        store.values["api-key"] = "old"

        result = invoke(runner, "update", "api-key", "--stdin", stdin="new\r\n")

        assert result.exit_code == 0, result.output
        assert store.values["api-key"] == "new"

    def test_update_missing_fails(self, runner: CliRunner, store: MemoryStore) -> None:
        result = invoke(runner, "update", "api-key", "--stdin", stdin="new")

        assert result.exit_code == 1
        assert "use add" in result.output

    def test_delete_with_yes(self, runner: CliRunner, store: MemoryStore) -> None:
        store.values["api-key"] = "x"

        result = invoke(runner, "delete", "api-key", "--yes")

        assert result.exit_code == 0
        assert store.values == {}

    def test_delete_asks_for_confirmation(
        self, runner: CliRunner, store: MemoryStore
    ) -> None:
        store.values["api-key"] = "x"

        result = invoke(runner, "delete", "api-key", stdin="n\n")

        assert result.exit_code == 1
        assert store.values == {"api-key": "x"}

    def test_delete_missing(self, runner: CliRunner, store: MemoryStore) -> None:
        result = invoke(runner, "delete", "api-key", "-y")

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_list_prints_names_only(
        self, runner: CliRunner, store: MemoryStore
    ) -> None:
        store.values = {"b": "value-b", "a": "value-a"}

        result = invoke(runner, "list")

        assert result.exit_code == 0
        assert result.output.splitlines() == ["a", "b"]
        assert "value" not in result.output

    def test_namespace_option_and_env(
        self, runner: CliRunner, store: MemoryStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner.invoke(app, ["-p", "windows", "-n", "myapp", "list"])
        monkeypatch.setenv("SECRET_NAMESPACE", "from-env")
        runner.invoke(app, ["-p", "macos", "list"])

        assert store.opened == [  # type: ignore[attr-defined]
            ("windows", "myapp"),
            ("macos", "from-env"),
        ]

    def test_cloud_provider_is_rejected(
        self, runner: CliRunner, store: MemoryStore
    ) -> None:
        result = runner.invoke(app, ["--provider", "aws_ssm", "list"])

        assert result.exit_code == 1
        assert "only manages local stores" in result.output

    def test_store_errors_are_reported(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_create(*_: Any) -> Any:
            raise SecretStoreError("Keychain locked")

        monkeypatch.setattr(secrets_app, "create_local_store", failing_create)

        result = invoke(runner, "list")

        assert result.exit_code == 1
        assert "Error: Keychain locked" in result.output


class TestEnvCommand:
    def test_exports_all(self, runner: CliRunner, store: MemoryStore) -> None:
        store.values = {"mn-db-user": "postgres", "mn-db-password": "p w"}

        result = invoke(runner, "env", "--shell", "posix")

        assert result.exit_code == 0, result.output
        assert result.output.splitlines() == [
            "export MN_DB_PASSWORD='p w'",
            "export MN_DB_USER=postgres",
        ]

    def test_exports_selected_for_powershell(
        self, runner: CliRunner, store: MemoryStore
    ) -> None:
        store.values = {"a": "1", "b": "2"}

        result = invoke(runner, "env", "b", "--shell", "powershell")

        assert result.output.splitlines() == ["$env:B = '2'"]

    def test_missing_selected_secret(
        self, runner: CliRunner, store: MemoryStore
    ) -> None:
        result = invoke(runner, "env", "nope")

        assert result.exit_code == 1
        assert "not found" in result.output


class TestCheckCommand:
    @staticmethod
    def write(directory: Path, file: str, data: dict[str, Any]) -> None:
        (directory / file).write_text(yaml.safe_dump(data), encoding="utf-8")

    def test_reports_missing_and_exits_1(
        self, runner: CliRunner, store: MemoryStore, tmp_path: Path
    ) -> None:
        # Arrange
        self.write(
            tmp_path,
            "config.yaml",
            {"app": {"database": {"user": "secret:db-user", "pw": "secret:db-pw"}}},
        )
        store.values = {"db-user": "u"}

        # Act
        result = invoke(runner, "check", "--config-dir", str(tmp_path))

        # Assert
        assert result.exit_code == 1
        assert result.output.splitlines() == [
            "missing  db-pw",
            "ok       db-user",
            "1 of 2 secrets present",
        ]

    def test_all_present_with_profile(
        self, runner: CliRunner, store: MemoryStore, tmp_path: Path
    ) -> None:
        self.write(tmp_path, "config.yaml", {"a": "secret:base"})
        self.write(tmp_path, "config.prod.yaml", {"b": "secret:prod-only"})
        store.values = {"base": "1", "prod-only": "2"}

        result = invoke(
            runner, "check", "--config-dir", str(tmp_path), "--profiles", "prod"
        )

        assert result.exit_code == 0, result.output
        assert "2 of 2 secrets present" in result.output

    def test_profiles_from_env(
        self,
        runner: CliRunner,
        store: MemoryStore,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.write(tmp_path, "config.yaml", {})
        self.write(tmp_path, "config.local.yaml", {"b": "secret:local-only"})
        monkeypatch.setenv("PROFILES", "local")

        result = invoke(runner, "check", "--config-dir", str(tmp_path))

        assert "missing  local-only" in result.output

    def test_no_references(
        self, runner: CliRunner, store: MemoryStore, tmp_path: Path
    ) -> None:
        self.write(tmp_path, "config.yaml", {"a": "plain"})

        result = invoke(runner, "check", "--config-dir", str(tmp_path))

        assert result.exit_code == 0
        assert "No secret: references" in result.output

    def test_default_config_dir_is_cwd_configuration(
        self,
        runner: CliRunner,
        store: MemoryStore,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "configuration").mkdir()
        self.write(tmp_path / "configuration", "config.yaml", {"a": "secret:x"})
        monkeypatch.chdir(tmp_path)

        result = invoke(runner, "check")

        assert "missing  x" in result.output


class TestEntryPoint:
    def test_main_runs_app(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["appkit-secrets", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            cli_entry.main()
        assert exc_info.value.code == 0

    def test_missing_typer_prints_install_hint(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "appkit_commons.cli.secrets_app":
                raise ModuleNotFoundError("No module named 'typer'", name="typer")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(SystemExit) as exc_info:
            cli_entry.main()

        assert exc_info.value.code == 1
        assert "appkit-commons[cli]" in capsys.readouterr().err

    def test_other_import_errors_propagate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "appkit_commons.cli.secrets_app":
                raise ModuleNotFoundError("No module named 'other'", name="other")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ModuleNotFoundError):
            cli_entry.main()
