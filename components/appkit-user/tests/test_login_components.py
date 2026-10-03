"""Tests for the login page components."""

import re

import pytest
from reflex.config import get_config

from appkit_user.authentication.components.login import login_form

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
