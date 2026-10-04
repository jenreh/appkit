"""Session guards for the HTTP transports: page loads and REST routes.

``SessionGuardMiddleware`` is a plain ASGI middleware that redirects anonymous
page loads to the login route before the app shell is served.
``require_session`` is the FastAPI dependency for REST routes.

Two caveats about the ASGI middleware:

* PROD-ONLY. In development Vite serves the pages on port 8080 and this
  middleware never sees them; only the single-port production deployment
  routes page HTML through the backend. It is a hardening layer for direct URL
  entry, bookmarks and hard refreshes — the primary gate is ``SessionFilter``
  on the WebSocket event stream.
* FRONT DOOR ONLY. ``StaticFiles(html=True)`` serves the same ``index.html``
  for every route, so this middleware cannot make per-route decisions about
  the response body. All it can do is redirect before the shell goes out.

``appkit_mcp_user.authentication.service.authenticate_user`` performs the same
check synchronously for the MCP mounts and goes live as soon as the session
cookie exists. It is not imported here: appkit-user must not depend on
appkit-mcp-user (wrong direction). ``SessionValidator`` is the shared
implementation on this side.
"""

import logging
from pathlib import PurePosixPath
from typing import Annotated, Final
from urllib.parse import unquote

from fastapi import Depends, HTTPException, status
from reflex.config import get_config
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from appkit_commons.public_path import public_path, strip_public_prefix
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.session_validation import (
    LOGIN_ROUTE,
    SessionValidator,
    is_public_route,
    is_session_filter_enabled,
    session_cookie_name,
)

logger = logging.getLogger(__name__)

_GUARDED_METHODS: Final = frozenset({"GET", "HEAD"})

# Framework and asset prefixes that never render a page. ``/_event`` is listed
# deliberately: the login page needs a live socket to submit credentials, so
# the Reflex event stream and its websocket handshake must NEVER be gated.
_PASSTHROUGH_PREFIXES: Final = (
    "/_event",
    "/_upload",
    "/ping",
    "/_health",
    "/api",
    "/.well-known",
    "/_next",
    "/assets",
    "/static",
)

_ASSET_SUFFIXES: Final = frozenset(
    {
        ".css",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".map",
        ".mjs",
        ".otf",
        ".png",
        ".svg",
        ".ttf",
        ".txt",
        ".webmanifest",
        ".webp",
        ".woff",
        ".woff2",
    }
)

_VALIDATOR: Final = SessionValidator()


def _has_passthrough_prefix(path: str) -> bool:
    """Whether the path is (or lives under) a framework/asset prefix."""
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in _PASSTHROUGH_PREFIXES
    )


def _is_asset_path(path: str) -> bool:
    """Whether the last path segment carries a static-asset file extension."""
    return PurePosixPath(path).suffix.lower() in _ASSET_SUFFIXES


def _app_relative_path(path: str) -> str:
    """Request path without the mount prefix and the app's frontend prefix.

    ``backend_path`` covers mount mode; the public prefix covers single-port
    deployments, where page requests carry ``frontend_path``.
    """
    backend_path = get_config().backend_path.rstrip("/")
    if backend_path and (path == backend_path or path.startswith(f"{backend_path}/")):
        return path[len(backend_path) :] or "/"
    return strip_public_prefix(path)


def _is_guarded_path(path: str) -> bool:
    """Whether a path addresses a page that requires a valid session."""
    if _has_passthrough_prefix(path) or _is_asset_path(path):
        return False
    return not is_public_route(path)


class SessionGuardMiddleware:
    """Redirect page loads without a valid session to the login route.

    Only ``GET``/``HEAD`` requests for page routes are inspected; framework
    endpoints, static assets and public routes pass straight through, as does
    every request when the session filter is disabled by configuration.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def _is_guarded(self, scope: Scope) -> bool:
        if scope["type"] != "http" or not is_session_filter_enabled():
            return False
        if scope.get("method", "").upper() not in _GUARDED_METHODS:
            return False
        return _is_guarded_path(_app_relative_path(scope.get("path", "/")))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_guarded(scope):
            await self.app(scope, receive, send)
            return

        result = await _VALIDATOR.validate(_session_id(Request(scope)))
        if result.is_valid:
            await self.app(scope, receive, send)
            return

        logger.warning(
            "Page load denied: path=%s status=%s",
            _app_relative_path(scope.get("path", "/")),
            result.status,
        )
        response = RedirectResponse(
            public_path(LOGIN_ROUTE),
            status_code=status.HTTP_302_FOUND,
            headers={"cache-control": "no-store"},
        )
        await response(scope, receive, send)


def _session_id(request: Request) -> str:
    """The session token from the cookie, percent-decoded.

    The frontend cookie library percent-encodes the value (tokens contain
    ``;``, ``%`` and the like) and Starlette does not decode cookies.
    """
    return unquote(request.cookies.get(session_cookie_name(), ""))


def add_session_guard(asgi_app: ASGIApp) -> ASGIApp:
    """Wrap an ASGI app with the page-load session guard."""
    return SessionGuardMiddleware(asgi_app)


async def require_session(request: Request) -> User:
    """Resolve the session cookie of a REST request to its user.

    Args:
        request: The incoming request carrying the session cookie.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: 401 when the session is missing, expired or
            unverifiable. Cookie auth, so no ``WWW-Authenticate`` challenge.
    """
    result = await _VALIDATOR.validate(_session_id(request))
    if result.is_valid and result.user is not None:
        return result.user

    logger.warning(
        "REST request denied: path=%s status=%s", request.url.path, result.status
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid session.",
    )


RequiredSession = Annotated[User, Depends(require_session)]
