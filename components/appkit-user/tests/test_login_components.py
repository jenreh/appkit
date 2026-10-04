"""Tests for the login page components."""

import re
from unittest.mock import patch

import pytest
from reflex.config import get_config

from appkit_user.authentication.components.login import login_form, oauth_login_splash
from appkit_user.configuration import OAuthProvider
from appkit_user.user_management.pages import (
    create_login_page,
    create_password_reset_confirm_page,
    create_password_reset_request_page,
)

_PAGES = "appkit_user.user_management.pages"

OAUTH_ICONS = (
    "google.svg",
    "google_dark.svg",
    "apple.svg",
    "apple_dark.svg",
    "microsoft.svg",
    "microsoft_dark.svg",
    "GitHub_light.svg",
    "GitHub_dark.svg",
)


@pytest.fixture
def frontend_path(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(get_config(), "frontend_path", "/alloq")
    return "/alloq"


def test_oauth_icons_honor_frontend_path(frontend_path: str) -> None:
    rendered = str(login_form(logo="/logo.svg", logo_dark="/logo_dark.svg"))

    srcs = set(re.findall(r"[\w/]*/icons/[\w.]+\.svg", rendered))

    assert srcs == {f"{frontend_path}/icons/{name}" for name in OAUTH_ICONS}


def test_oauth_icons_at_site_root() -> None:
    rendered = str(login_form(logo="/logo.svg", logo_dark="/logo_dark.svg"))

    srcs = set(re.findall(r"[\w/]*/icons/[\w.]+\.svg", rendered))

    assert srcs == {f"/icons/{name}" for name in OAUTH_ICONS}


_LOGOS = {"/knai/img/appkit_logo.svg", "/knai/img/appkit_logo_dark.svg"}
_LOGO_RE = r"[\w/]*/img/appkit_logo(?:_dark)?\.svg"


@pytest.fixture
def knai_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_config(), "frontend_path", "/knai")


@pytest.mark.usefixtures("knai_prefix")
def test_oauth_login_splash_logo_has_prefix() -> None:
    rendered = str(oauth_login_splash(OAuthProvider.GITHUB))

    assert set(re.findall(_LOGO_RE, rendered)) == _LOGOS


@pytest.mark.usefixtures("knai_prefix")
@pytest.mark.parametrize(
    "factory",
    [
        create_login_page,
        create_password_reset_request_page,
        create_password_reset_confirm_page,
    ],
)
def test_page_logo_has_prefix(factory) -> None:  # noqa: ANN001
    with patch(f"{_PAGES}.default_layout", lambda **_: lambda page: page):
        rendered = str(factory()())

    assert set(re.findall(_LOGO_RE, rendered)) == _LOGOS
