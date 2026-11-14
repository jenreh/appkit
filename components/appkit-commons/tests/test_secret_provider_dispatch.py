"""Tests for provider selection, the shared namespace and backend dispatch."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from appkit_commons.configuration import secret_provider
from appkit_commons.configuration.secret_backends import (
    SecretStoreError,
    create_local_store,
    settings,
)
from appkit_commons.configuration.secret_backends.azure import (
    AzureKeyVaultBackend,
    azure_secret_name,
)
from appkit_commons.configuration.secret_backends.base import SecretNotFoundError
from appkit_commons.configuration.secret_provider import (
    SecretProvider,
    get_secret,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("SECRET_PROVIDER", raising=False)
    monkeypatch.delenv("SECRET_NAMESPACE", raising=False)
    secret_provider._get_azure_client.cache_clear()
    secret_provider._get_ssm_client.cache_clear()
    yield
    secret_provider._get_azure_client.cache_clear()
    secret_provider._get_ssm_client.cache_clear()


class TestSettings:
    def test_provider_defaults_to_local(self) -> None:
        assert settings.provider_name() == "local"

    def test_blank_provider_is_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "  ")
        assert settings.provider_name() == "local"

    def test_provider_is_lowercased(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", " MacOS ")
        assert settings.provider_name() == "macos"

    def test_namespace_unset_or_blank(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert settings.namespace() is None
        monkeypatch.setenv("SECRET_NAMESPACE", " ")
        assert settings.namespace() is None

    def test_local_namespace_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert settings.local_namespace() == "appkit"
        monkeypatch.setenv("SECRET_NAMESPACE", "myapp")
        assert settings.local_namespace() == "myapp"
        assert settings.local_namespace("explicit") == "explicit"


class TestProviderEnum:
    def test_all_values(self) -> None:
        assert [provider.value for provider in SecretProvider] == [
            "azure",
            "local",
            "aws_ssm",
            "macos",
            "windows",
        ]


class TestGetSecretDispatch:
    def test_unknown_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "vault")
        with pytest.raises(ValueError, match="Unknown SECRET_PROVIDER 'vault'"):
            get_secret("x")

    def test_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "local")
        monkeypatch.setenv("MY_KEY", "from-env")
        assert get_secret("my-key") == "from-env"

    def test_azure_without_namespace_keeps_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        client = MagicMock()
        client.get_secret.return_value.value = "v"

        # Act
        with patch.object(secret_provider, "_get_azure_client", return_value=client):
            value = get_secret("MN-DB-User")

        # Assert
        assert value == "v"
        client.get_secret.assert_called_once_with("mn-db-user")

    def test_azure_with_namespace_prefixes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        monkeypatch.setenv("SECRET_NAMESPACE", "track/prod")
        client = MagicMock()
        client.get_secret.return_value.value = "v"

        with patch.object(secret_provider, "_get_azure_client", return_value=client):
            get_secret("db-user")

        client.get_secret.assert_called_once_with("track-prod-db-user")

    def test_aws_ssm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "aws_ssm")
        monkeypatch.setenv("SECRET_NAMESPACE", "myapp/dev")
        client = MagicMock()
        client.get_parameter.return_value = {"Parameter": {"Value": "ssm-value"}}

        # Act
        with patch.object(secret_provider, "_get_ssm_client", return_value=client):
            value = get_secret("db-password")

        # Assert
        assert value == "ssm-value"
        client.get_parameter.assert_called_once_with(
            Name="/myapp/dev/db-password", WithDecryption=True
        )

    def test_ssm_client_is_cached(self) -> None:
        with patch.object(
            secret_provider, "create_ssm_client", return_value=object()
        ) as create:
            first = secret_provider._get_ssm_client()
            second = secret_provider._get_ssm_client()

        assert first is second
        create.assert_called_once_with()

    @pytest.mark.parametrize("provider", ["macos", "windows"])
    def test_local_stores_use_namespace(
        self, monkeypatch: pytest.MonkeyPatch, provider: str
    ) -> None:
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", provider)
        monkeypatch.setenv("SECRET_NAMESPACE", "myapp")
        store = MagicMock()
        store.get.return_value = "local-value"
        calls: list[tuple[str, str]] = []

        def fake_create(name: str, namespace: str) -> Any:
            calls.append((name, namespace))
            return store

        # Act
        with patch.object(secret_provider, "create_local_store", fake_create):
            value = get_secret("db-password")

        # Assert
        assert value == "local-value"
        assert calls == [(provider, "myapp")]
        store.get.assert_called_once_with("db-password")

    def test_local_store_defaults_namespace_to_appkit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SECRET_PROVIDER", "macos")
        calls: list[str] = []

        def fake_create(_: str, namespace: str) -> Any:
            calls.append(namespace)
            return MagicMock()

        with patch.object(secret_provider, "create_local_store", fake_create):
            get_secret("x")

        assert calls == ["appkit"]


class TestAzureBackend:
    @pytest.mark.parametrize(
        ("name", "namespace", "expected"),
        [
            ("Db-User", None, "db-user"),
            ("db-user", "MyApp", "myapp-db-user"),
            ("db-user", "track/prod", "track-prod-db-user"),
            ("db-user", "my_app.dev", "my-app-dev-db-user"),
            ("db-user", "/", "db-user"),
        ],
    )
    def test_name_mapping(
        self, name: str, namespace: str | None, expected: str
    ) -> None:
        assert azure_secret_name(name, namespace) == expected

    def test_resource_not_found_becomes_secret_not_found(self) -> None:
        class ResourceNotFoundError(Exception):
            pass

        client = MagicMock()
        client.get_secret.side_effect = ResourceNotFoundError("gone")

        with pytest.raises(SecretNotFoundError, match="not found in Azure"):
            AzureKeyVaultBackend(client).get("x")

    def test_other_errors_propagate(self) -> None:
        client = MagicMock()
        client.get_secret.side_effect = PermissionError("denied")

        with pytest.raises(PermissionError):
            AzureKeyVaultBackend(client).get("x")


class TestCreateLocalStore:
    def test_rejects_cloud_providers(self) -> None:
        with pytest.raises(SecretStoreError, match="not a local secret store"):
            create_local_store("azure", "appkit")

    def test_macos_store_checks_platform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.platform", "linux")
        with pytest.raises(SecretStoreError, match="macOS"):
            create_local_store("macos", "appkit")

    def test_windows_store_checks_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.platform", "darwin")
        with pytest.raises(SecretStoreError, match="Windows"):
            create_local_store("windows", "appkit")
