"""Tests for the app path prefix helpers (source: Reflex's frontend_path)."""

from unittest.mock import patch

import pytest

from appkit_commons.public_path import (
    app_slug,
    default_session_cookie_name,
    public_path,
    public_prefix,
    public_url,
    strip_public_prefix,
)
from appkit_commons.testing import set_public_path_prefix


@pytest.fixture
def knai(monkeypatch: pytest.MonkeyPatch) -> None:
    set_public_path_prefix(monkeypatch, "/knai")


class TestPublicPrefix:
    @pytest.mark.parametrize(
        ("frontend_path", "expected"),
        [("", ""), ("/", ""), ("/knai", "/knai"), ("knai/", "/knai")],
    )
    def test_normalized(
        self, monkeypatch: pytest.MonkeyPatch, frontend_path: str, expected: str
    ) -> None:
        set_public_path_prefix(monkeypatch, frontend_path)
        assert public_prefix() == expected

    def test_reflex_missing(self) -> None:
        with patch.dict("sys.modules", {"reflex.config": None}):
            assert public_prefix() == ""


class TestDerivedNames:
    @pytest.mark.parametrize(
        ("frontend_path", "slug", "cookie"),
        [
            ("", "", "reflex_session"),
            ("/knai", "knai", "knai_session"),
            ("/apps/my-app", "apps_my_app", "apps_my_app_session"),
        ],
    )
    def test_slug_and_cookie(
        self,
        monkeypatch: pytest.MonkeyPatch,
        frontend_path: str,
        slug: str,
        cookie: str,
    ) -> None:
        set_public_path_prefix(monkeypatch, frontend_path)
        assert app_slug() == slug
        assert default_session_cookie_name() == cookie


@pytest.mark.usefixtures("knai")
class TestPublicPath:
    def test_absolute_path_gets_prefix(self) -> None:
        assert public_path("/icons/a.svg") == "/knai/icons/a.svg"

    @pytest.mark.parametrize(
        "path",
        ["/knai/icons/a.svg", "/knai", "https://x/a.svg", "a.svg", "//cdn/a.svg", ""],
    )
    def test_unchanged(self, path: str) -> None:
        assert public_path(path) == path

    def test_similar_prefix_still_prefixed(self) -> None:
        assert public_path("/knaix/a.svg") == "/knai/knaix/a.svg"


def test_public_path_at_site_root() -> None:
    assert public_path("/icons/a.svg") == "/icons/a.svg"


class TestStripPublicPrefix:
    @pytest.mark.usefixtures("knai")
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/knai/login", "/login"),
            ("/knai", "/"),
            ("/knai/", "/"),
            ("/login", "/login"),
            ("/knaix/login", "/knaix/login"),
            ("", ""),
        ],
    )
    def test_with_prefix(self, path: str, expected: str) -> None:
        assert strip_public_prefix(path) == expected

    def test_at_site_root(self) -> None:
        assert strip_public_prefix("/knai/login") == "/knai/login"


class TestPublicUrl:
    @pytest.mark.usefixtures("knai")
    @pytest.mark.parametrize(
        ("base", "path", "expected"),
        [
            ("https://x", "/oauth/cb", "https://x/knai/oauth/cb"),
            ("https://x/", "/oauth/cb", "https://x/knai/oauth/cb"),
            ("https://x", "", "https://x/knai"),
            # base URL already carries the prefix: not added twice
            ("https://x/knai", "/oauth/cb", "https://x/knai/oauth/cb"),
            ("https://x/knai/", "", "https://x/knai"),
            ("http://localhost:8080", "/a", "http://localhost:8080/knai/a"),
        ],
    )
    def test_with_prefix(self, base: str, path: str, expected: str) -> None:
        assert public_url(base, path) == expected

    def test_at_site_root(self) -> None:
        assert public_url("https://x/", "/a") == "https://x/a"
        assert public_url("https://x") == "https://x"
