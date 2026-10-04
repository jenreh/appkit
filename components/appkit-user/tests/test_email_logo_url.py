"""The password reset email links the logo below the app's public prefix."""

from unittest.mock import AsyncMock, patch

import pytest

from appkit_commons.testing import set_public_path_prefix
from appkit_user.authentication.backend.services import MockEmailProvider
from appkit_user.configuration import AuthenticationConfiguration, MockEmailConfig

_SERVICE = "appkit_user.authentication.backend.services.email_service"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "port", "expected"),
    [
        ("https://x", 443, "https://x/knai"),
        ("http://localhost", 8080, "http://localhost:8080/knai"),
        ("https://x/knai", 443, "https://x/knai"),
    ],
)
async def test_logo_url_uses_public_origin_and_prefix(
    monkeypatch: pytest.MonkeyPatch, url: str, port: int, expected: str
) -> None:
    set_public_path_prefix(monkeypatch, "/knai")
    config = AuthenticationConfiguration(server_url=url, server_port=port)
    provider = MockEmailProvider(MockEmailConfig())
    with (
        patch(f"{_SERVICE}.service_registry") as registry,
        patch.object(provider, "_render_template", return_value="<html/>") as render,
        patch.object(provider, "send_email", AsyncMock(return_value=True)),
    ):
        registry.return_value.get.return_value = config
        assert await provider.send_password_reset_email("a@b.c", "link", "Name")

    assert render.call_args.kwargs["logo_url"] == expected
