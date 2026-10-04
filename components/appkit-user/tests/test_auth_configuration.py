"""Tests for AuthenticationConfiguration: storage key prefix and public origin."""

import os
import subprocess
import sys
import textwrap

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from appkit_commons.testing import set_public_path_prefix
from appkit_user.authentication.states import storage_key
from appkit_user.configuration import AuthenticationConfiguration


def _auth(server_url: str = "http://x", server_port: int = 0, **kwargs: object):
    return AuthenticationConfiguration(
        server_url=server_url, server_port=server_port, **kwargs
    )


class _App(BaseModel):
    authentication: AuthenticationConfiguration


class _Root(BaseSettings):
    """Mirrors the ``APP__...`` nesting of the appkit Configuration."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="ignore")
    app: _App


class TestStorageKeyPrefix:
    def test_default_empty(self) -> None:
        assert _auth().storage_key_prefix == ""

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP__AUTHENTICATION__SERVER_URL", "http://x")
        monkeypatch.setenv("APP__AUTHENTICATION__SERVER_PORT", "0")
        monkeypatch.setenv("APP__AUTHENTICATION__STORAGE_KEY_PREFIX", "knai_")
        assert _Root().app.authentication.storage_key_prefix == "knai_"

    @pytest.mark.parametrize("value", ["knai-", "knai/", "a b"])
    def test_invalid_rejected(self, value: str) -> None:
        with pytest.raises(ValidationError):
            _auth(storage_key_prefix=value)

    @pytest.mark.parametrize(
        ("name", "prefix", "expected"),
        [
            ("_auth_token", "knai_", "knai__auth_token"),
            ("_auth_token", "", "_auth_token"),
        ],
    )
    def test_storage_key(self, name: str, prefix: str, expected: str) -> None:
        assert storage_key(name, prefix) == expected

    def test_state_storage_names_use_prefix(self) -> None:
        """The names are fixed at import time, so check a fresh interpreter."""
        script = textwrap.dedent(
            """
            from appkit_commons.registry import service_registry
            from appkit_user.configuration import AuthenticationConfiguration

            service_registry().register(
                AuthenticationConfiguration(
                    server_url="http://x", server_port=0, storage_key_prefix="knai_"
                )
            )
            from appkit_user.authentication.states import LoginState, UserSession

            fields = (
                UserSession.get_fields()["auth_token"],
                LoginState.get_fields()["redirect_to"],
                LoginState.get_fields()["oauth_state"],
            )
            print(",".join(f.default.name for f in fields))
            """
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONWARNINGS": "ignore"},
            timeout=120,
        )
        names = result.stdout.strip().splitlines()[-1].split(",")
        assert names == [
            "knai__auth_token",
            "knai_login_redirect_to",
            "knai__oauth_state",
        ]


class TestPublicOrigin:
    @pytest.mark.parametrize(
        ("url", "port", "expected"),
        [
            ("https://x", 443, "https://x"),
            ("http://x", 80, "http://x"),
            ("http://localhost", 8080, "http://localhost:8080"),
            ("https://x", 8443, "https://x:8443"),
            ("http://x", 443, "http://x:443"),
            ("https://x", 0, "https://x"),
            ("http://localhost:8080", 0, "http://localhost:8080"),
            ("https://x/", 443, "https://x"),
            ("https://x/", 0, "https://x"),
            # an explicit port in server_url wins over server_port
            ("http://localhost:8080", 443, "http://localhost:8080"),
            # the port goes into the host part, not after a path
            ("https://x/knai", 8443, "https://x:8443/knai"),
            ("https://x/knai/", 443, "https://x/knai"),
        ],
    )
    def test_public_origin(self, url: str, port: int, expected: str) -> None:
        assert _auth(url, port).public_origin == expected


class TestPublicBaseUrl:
    @pytest.mark.parametrize(
        ("url", "port", "expected"),
        [
            ("https://x", 443, "https://x/knai"),
            ("http://localhost", 8080, "http://localhost:8080/knai"),
            ("https://x/knai", 443, "https://x/knai"),
        ],
    )
    def test_with_prefix(
        self, monkeypatch: pytest.MonkeyPatch, url: str, port: int, expected: str
    ) -> None:
        set_public_path_prefix(monkeypatch, "/knai")
        assert _auth(url, port).public_base_url == expected

    def test_without_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_public_path_prefix(monkeypatch, "")
        assert _auth("https://x", 443).public_base_url == "https://x"


class TestDerivedNames:
    @pytest.mark.parametrize(
        ("frontend_path", "cookie", "storage"),
        [("", "reflex_session", ""), ("/knai", "knai_session", "knai_")],
    )
    def test_derived_from_prefix(
        self,
        monkeypatch: pytest.MonkeyPatch,
        frontend_path: str,
        cookie: str,
        storage: str,
    ) -> None:
        set_public_path_prefix(monkeypatch, frontend_path)
        config = _auth()
        assert config.effective_session_cookie_name == cookie
        assert config.effective_storage_key_prefix == storage

    def test_explicit_values_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_public_path_prefix(monkeypatch, "/knai")
        config = _auth(session_cookie_name="sid", storage_key_prefix="x_")
        assert config.effective_session_cookie_name == "sid"
        assert config.effective_storage_key_prefix == "x_"
