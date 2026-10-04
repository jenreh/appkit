# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for the HTTP session guards.

Covers the ASGI page-load guard (``SessionGuardMiddleware``), the
``add_session_guard`` factory and the ``require_session`` REST dependency.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from reflex.config import get_config
from starlette.requests import Request
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from appkit_commons.testing import set_public_path_prefix
from appkit_user.authentication import http_guard
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.session_validation import (
    SessionStatus,
    SessionValidationResult,
)
from appkit_user.configuration import AuthenticationConfiguration

_VALIDATION = "appkit_user.authentication.session_validation"

_COOKIE = "reflex_session"
_PAGE_PATH = "/profile"

# Framework endpoints and static assets: never a page, never gated. ``/_event``
# is load-bearing — the login page needs a live socket to submit credentials.
_PASSTHROUGH_PATHS = [
    "/_event",
    "/_upload",
    "/ping",
    "/_health",
    "/api/images/1",
    "/assets/index.js",
    "/favicon.ico",
    "/css/appkit.css",
]


# ---------------------------------------------------------------------------
# Doubles and ASGI helpers
# ---------------------------------------------------------------------------


class _StubValidator:
    """Stands in for the module-level ``SessionValidator`` singleton."""

    def __init__(self, result: SessionValidationResult) -> None:
        self.result = result
        self.calls: list[str] = []

    async def validate(
        self, session_id: str, user_id: int = 0
    ) -> SessionValidationResult:
        self.calls.append(session_id)
        return self.result


class _StubApp:
    """Inner ASGI app recording whether the guard let the request through."""

    def __init__(self) -> None:
        self.scopes: list[Scope] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.scopes.append(scope)
        if scope["type"] != "http":
            return
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"page"})

    @property
    def called(self) -> int:
        return len(self.scopes)


def _http_scope(
    path: str = _PAGE_PATH, method: str = "GET", cookie: str | None = None
) -> dict[str, Any]:
    headers: list[tuple[bytes, bytes]] = [(b"host", b"example.com")]
    if cookie is not None:
        headers.append((b"cookie", cookie.encode()))
    return {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("example.com", 80),
        "client": ("1.2.3.4", 1234),
    }


async def _drive(app: Any, scope: dict[str, Any]) -> list[dict[str, Any]]:
    """Run an ASGI app against a scope and collect the sent messages."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    await app(scope, receive, send)
    return sent


def _start(sent: list[dict[str, Any]]) -> dict[str, Any]:
    return next(m for m in sent if m["type"] == "http.response.start")


def _headers(sent: list[dict[str, Any]]) -> dict[str, str]:
    return {k.decode().lower(): v.decode() for k, v in _start(sent)["headers"]}


def _valid_result(user_id: int = 7) -> SessionValidationResult:
    return SessionValidationResult(
        SessionStatus.VALID,
        user=User(user_id=user_id, name="Ada", email="ada@example.com"),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auth_config() -> Iterator[AuthenticationConfiguration]:
    """Pin the configuration the guard resolves through ``_auth_config``."""
    config = AuthenticationConfiguration(
        server_url="http://localhost", server_port=3031
    )
    with patch(f"{_VALIDATION}._auth_config", return_value=config):
        yield config


@pytest.fixture
def validator() -> Iterator[_StubValidator]:
    """Replace the singleton validator; defaults to "no such session"."""
    stub = _StubValidator(SessionValidationResult(SessionStatus.ABSENT))
    with patch.object(http_guard, "_VALIDATOR", stub):
        yield stub


@pytest.fixture
def inner() -> _StubApp:
    return _StubApp()


@pytest.fixture
def guard(inner: _StubApp) -> http_guard.SessionGuardMiddleware:
    return http_guard.SessionGuardMiddleware(inner)


# ---------------------------------------------------------------------------
# SessionGuardMiddleware — pass-through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _PASSTHROUGH_PATHS)
@pytest.mark.asyncio
async def test_framework_and_asset_paths_pass_through(
    path: str,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope(path))

    assert inner.called == 1
    assert _start(sent)["status"] == 200
    assert validator.calls == []


@pytest.mark.asyncio
async def test_websocket_scope_passes_through(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    scope: dict[str, Any] = {
        "type": "websocket",
        "path": "/_event/",
        "headers": [],
    }

    await _drive(guard, scope)

    assert inner.called == 1
    assert validator.calls == []


@pytest.mark.asyncio
async def test_public_page_without_cookie_passes_through(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope("/login"))

    assert inner.called == 1
    assert _start(sent)["status"] == 200
    assert validator.calls == []


@pytest.mark.asyncio
async def test_post_to_page_path_passes_through(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    await _drive(guard, _http_scope(_PAGE_PATH, method="POST"))

    assert inner.called == 1
    assert validator.calls == []


@pytest.mark.asyncio
async def test_disabled_filter_passes_everything_through(
    auth_config: AuthenticationConfiguration,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    auth_config.session_filter_enabled = False

    sent = await _drive(guard, _http_scope(_PAGE_PATH))

    assert inner.called == 1
    assert _start(sent)["status"] == 200
    assert validator.calls == []


@pytest.mark.asyncio
async def test_valid_cookie_passes_through(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    validator.result = _valid_result()

    sent = await _drive(
        guard, _http_scope(_PAGE_PATH, cookie=f"other=x; {_COOKIE}=tok-123")
    )

    assert inner.called == 1
    assert _start(sent)["status"] == 200
    assert validator.calls == ["tok-123"]


# ---------------------------------------------------------------------------
# SessionGuardMiddleware — denial
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_without_cookie_redirects_to_login(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope(_PAGE_PATH))

    assert _start(sent)["status"] == 302
    assert _headers(sent)["location"] == "/login"
    assert _headers(sent)["cache-control"] == "no-store"
    assert inner.called == 0
    assert validator.calls == [""]


@pytest.mark.parametrize(
    "status", [SessionStatus.EXPIRED, SessionStatus.ABSENT, SessionStatus.ERROR]
)
@pytest.mark.asyncio
async def test_page_with_unusable_cookie_redirects_to_login(
    status: SessionStatus,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    validator.result = SessionValidationResult(status)

    sent = await _drive(guard, _http_scope(_PAGE_PATH, cookie=f"{_COOKIE}=stale"))

    assert _start(sent)["status"] == 302
    assert _headers(sent)["location"] == "/login"
    assert inner.called == 0
    assert validator.calls == ["stale"]


@pytest.mark.asyncio
async def test_head_request_is_guarded(
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope(_PAGE_PATH, method="HEAD"))

    assert _start(sent)["status"] == 302
    assert inner.called == 0


# ---------------------------------------------------------------------------
# add_session_guard
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SessionGuardMiddleware — mount mode (backend_path) and public prefix
# ---------------------------------------------------------------------------


@pytest.fixture
def knai_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_config(), "backend_path", "/knai")


@pytest.mark.usefixtures("knai_mount")
@pytest.mark.parametrize(
    "path",
    [
        "/knai/ping",
        "/knai/_health",
        "/knai/_event/x",
        "/knai/api/x",
        "/knai/assets/a.js",
        "/knai/login",
    ],
)
@pytest.mark.asyncio
async def test_mounted_framework_paths_pass_through(
    path: str,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope(path))

    assert inner.called == 1
    assert _start(sent)["status"] == 200
    assert validator.calls == []


@pytest.mark.usefixtures("knai_mount")
@pytest.mark.parametrize("path", ["/knai/admin", "/knai", "/knaix/ping"])
@pytest.mark.asyncio
async def test_mounted_page_is_guarded(
    path: str,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    sent = await _drive(guard, _http_scope(path))

    assert _start(sent)["status"] == 302
    assert inner.called == 0


@pytest.mark.parametrize(
    ("path", "guarded"), [("/knai/login", False), ("/knai/profile", True)]
)
@pytest.mark.asyncio
async def test_prefixed_page_paths_single_port(
    path: str,
    guarded: bool,
    monkeypatch: pytest.MonkeyPatch,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    """Single-port prod with frontend_path serves pages under the prefix."""
    set_public_path_prefix(monkeypatch, "/knai")

    sent = await _drive(guard, _http_scope(path))

    assert (_start(sent)["status"] == 302) is guarded
    assert inner.called == (0 if guarded else 1)


@pytest.mark.asyncio
async def test_redirect_carries_public_prefix(
    monkeypatch: pytest.MonkeyPatch,
    guard: http_guard.SessionGuardMiddleware,
    inner: _StubApp,
    validator: _StubValidator,
) -> None:
    set_public_path_prefix(monkeypatch, "/knai")

    sent = await _drive(guard, _http_scope("/admin"))

    assert _start(sent)["status"] == 302
    assert _headers(sent)["location"] == "/knai/login"
    assert inner.called == 0


def test_add_session_guard_wraps_the_app(inner: _StubApp) -> None:
    wrapped = http_guard.add_session_guard(inner)

    assert isinstance(wrapped, http_guard.SessionGuardMiddleware)
    assert wrapped.app is inner


# ---------------------------------------------------------------------------
# require_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_session_returns_the_user(validator: _StubValidator) -> None:
    validator.result = _valid_result(user_id=7)
    request = Request(_http_scope("/api/me", cookie=f"{_COOKIE}=tok"))

    user = await http_guard.require_session(request)

    assert user.user_id == 7
    assert user.email == "ada@example.com"
    assert validator.calls == ["tok"]


@pytest.mark.asyncio
async def test_require_session_without_cookie_raises_401(
    validator: _StubValidator,
) -> None:
    request = Request(_http_scope("/api/me"))

    with pytest.raises(HTTPException) as exc_info:
        await http_guard.require_session(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid session."
    # Cookie auth, so no browser-triggering challenge header.
    assert exc_info.value.headers is None
    assert validator.calls == [""]


@pytest.mark.parametrize(
    "status", [SessionStatus.EXPIRED, SessionStatus.ERROR, SessionStatus.ABSENT]
)
@pytest.mark.asyncio
async def test_require_session_with_unusable_session_raises_401(
    status: SessionStatus, validator: _StubValidator
) -> None:
    validator.result = SessionValidationResult(status)
    request = Request(_http_scope("/api/me", cookie=f"{_COOKIE}=stale"))

    with pytest.raises(HTTPException) as exc_info:
        await http_guard.require_session(request)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_session_rejects_valid_status_without_user(
    validator: _StubValidator,
) -> None:
    """A VALID result carrying no user must still be refused, not returned."""
    validator.result = SessionValidationResult(SessionStatus.VALID, user=None)
    request = Request(_http_scope("/api/me", cookie=f"{_COOKIE}=tok"))

    with pytest.raises(HTTPException) as exc_info:
        await http_guard.require_session(request)

    assert exc_info.value.status_code == 401


def test_required_session_resolves_through_fastapi(
    validator: _StubValidator,
) -> None:
    """``RequiredSession`` must really wire the dependency into the route."""
    api = FastAPI()

    @api.get("/me")
    async def me(current: http_guard.RequiredSession) -> dict[str, Any]:
        return {"user_id": current.user_id, "name": current.name}

    client = TestClient(api)
    client.cookies.set(_COOKIE, "tok")

    validator.result = _valid_result(user_id=7)
    ok = client.get("/me")
    assert ok.status_code == 200
    assert ok.json() == {"user_id": 7, "name": "Ada"}

    validator.result = SessionValidationResult(SessionStatus.ABSENT)
    client.cookies.clear()
    denied = client.get("/me")
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Missing or invalid session."
    assert "www-authenticate" not in {k.lower() for k in denied.headers}
