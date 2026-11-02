"""Tests for middleware utilities."""

import pytest

from appkit_commons.middleware import (
    BASE_SECURITY_HEADERS,
    HSTS,
    ForceHTTPSMiddleware,
    SecurityHeadersMiddleware,
)


class MockApp:
    """Mock ASGI app for testing."""

    def __init__(self):
        self.last_scope = None

    async def __call__(self, scope, receive, send) -> None:  # noqa: ARG002
        """Store scope for assertions."""
        self.last_scope = scope


class TestForceHTTPSMiddleware:
    """Test suite for ForceHTTPSMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_init(self) -> None:
        """ForceHTTPSMiddleware can be initialized."""
        # Arrange
        mock_app = None

        # Act
        middleware = ForceHTTPSMiddleware(mock_app)

        # Assert
        assert middleware.app is None

    @pytest.mark.asyncio
    async def test_middleware_creates_with_app(self) -> None:
        """ForceHTTPSMiddleware stores the ASGI app."""
        # Arrange
        app = MockApp()

        # Act
        middleware = ForceHTTPSMiddleware(app)

        # Assert
        assert middleware.app is app

    @pytest.mark.asyncio
    async def test_middleware_http_scope(self) -> None:
        """ForceHTTPSMiddleware handles HTTP scope."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["type"] == "http"

    @pytest.mark.asyncio
    async def test_middleware_forces_https_on_x_forwarded_proto(self) -> None:
        """ForceHTTPSMiddleware forces HTTPS when X-Forwarded-Proto is https."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [(b"x-forwarded-proto", b"https")],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["scheme"] == "https"

    @pytest.mark.asyncio
    async def test_middleware_handles_websocket_scope(self) -> None:
        """ForceHTTPSMiddleware handles WebSocket scope."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "websocket",
            "scheme": "ws",
            "headers": [(b"x-forwarded-proto", b"https")],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["scheme"] == "https"

    @pytest.mark.asyncio
    async def test_middleware_ignores_non_https_forwarded_proto(self) -> None:
        """ForceHTTPSMiddleware ignores X-Forwarded-Proto if not https."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [(b"x-forwarded-proto", b"http")],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["scheme"] == "http"

    @pytest.mark.asyncio
    async def test_middleware_preserves_lifespan_scope(self) -> None:
        """ForceHTTPSMiddleware ignores non-http/websocket scopes."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "lifespan",
            "scheme": "http",
            "headers": [(b"x-forwarded-proto", b"https")],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        # lifespan scope should NOT have scheme modified
        assert app.last_scope["scheme"] == "http"

    @pytest.mark.asyncio
    async def test_middleware_handles_empty_headers(self) -> None:
        """ForceHTTPSMiddleware handles empty headers list."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["scheme"] == "http"

    @pytest.mark.asyncio
    async def test_middleware_http_scope_no_x_forwarded_header(self) -> None:
        """ForceHTTPSMiddleware leaves HTTP as-is without header."""
        # Arrange
        app = MockApp()
        middleware = ForceHTTPSMiddleware(app)

        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [(b"content-type", b"application/json")],
        }

        # Act
        await middleware(scope, None, None)  # noqa: ARG005

        # Assert
        assert app.last_scope is not None
        assert app.last_scope["scheme"] == "http"


async def _call_with_headers(
    scope: dict, response_headers: list[tuple[bytes, bytes]]
) -> dict[str, str]:
    sent: list[dict] = []

    async def inner(_scope, _receive, send) -> None:  # noqa: ANN001
        await send(
            {"type": "http.response.start", "status": 200, "headers": response_headers}
        )

    async def receive() -> dict:
        return {"type": "http.request"}

    async def send(message: dict) -> None:
        sent.append(message)

    await SecurityHeadersMiddleware(inner)(scope, receive, send)
    return {k.decode(): v.decode() for k, v in sent[0]["headers"]}


class TestSecurityHeadersMiddleware:
    """Test suite for SecurityHeadersMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_base_headers(self) -> None:
        headers = await _call_with_headers({"type": "http", "scheme": "http"}, [])

        assert {k: headers[k.lower()] for k in BASE_SECURITY_HEADERS} == (
            BASE_SECURITY_HEADERS
        )
        assert "strict-transport-security" not in headers

    @pytest.mark.asyncio
    async def test_adds_hsts_on_https(self) -> None:
        headers = await _call_with_headers({"type": "http", "scheme": "https"}, [])

        assert headers["strict-transport-security"] == HSTS

    @pytest.mark.asyncio
    async def test_keeps_headers_a_route_set(self) -> None:
        own = [(b"content-security-policy", b"default-src 'none'; sandbox")]

        headers = await _call_with_headers({"type": "http", "scheme": "http"}, own)

        assert headers["content-security-policy"] == "default-src 'none'; sandbox"

    @pytest.mark.asyncio
    async def test_passes_other_scopes_through(self) -> None:
        app = MockApp()

        await SecurityHeadersMiddleware(app)({"type": "websocket"}, None, None)

        assert app.last_scope == {"type": "websocket"}
