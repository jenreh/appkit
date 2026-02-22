"""Tests for middleware utilities."""

import pytest

from appkit_commons.middleware import ForceHTTPSMiddleware


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
