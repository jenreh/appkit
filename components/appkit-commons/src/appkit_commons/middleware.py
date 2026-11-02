import logging
import os
from typing import Final

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

HSTS: Final = "max-age=31536000; includeSubDomains"
BASE_SECURITY_HEADERS: Final = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "frame-ancestors 'self'",
    "Permissions-Policy": "camera=(self), microphone=(self), geolocation=(self)",
    # Keeps window.opener for popups we open (OAuth) but isolates the page from
    # cross-origin windows that open it.
    "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
}


def trusted_proxy_hosts_from_env(name: str = "FORWARDED_ALLOW_IPS") -> set[str] | None:
    """Proxy addresses allowed to set ``X-Forwarded-Proto``, from the environment.

    Uses the same variable and comma-separated format as uvicorn. Unset, empty or
    ``*`` returns ``None``, which trusts every peer.
    """
    raw = os.environ.get(name, "").strip()
    if not raw or raw == "*":
        return None
    return {host.strip() for host in raw.split(",") if host.strip()}


class ForceHTTPSMiddleware:
    """Correct the ASGI request scheme to ``https`` behind a TLS-terminating proxy.

    The application is expected to run strictly behind a reverse proxy (e.g.
    Azure) that terminates TLS and forwards the original scheme in the
    ``X-Forwarded-Proto`` header. This middleware rewrites ``scope['scheme']``
    to ``https`` so downstream absolute-URL and websocket-URL generation is
    accurate. It does NOT itself redirect HTTP to HTTPS.

    Because ``X-Forwarded-Proto`` is client-controllable, honoring it from an
    untrusted peer would let a client spoof a secure scheme. When
    ``trusted_hosts`` is provided, the header is only honored if the immediate
    peer (``scope['client']``) is in that allow-list; otherwise the header is
    ignored. When ``trusted_hosts`` is ``None`` the header is honored
    unconditionally (legacy behavior) — pass the proxy's address set in any
    deployment where the app could be reached directly.
    """

    def __init__(self, app: ASGIApp, trusted_hosts: set[str] | None = None) -> None:
        self.app = app
        self.trusted_hosts = trusted_hosts
        if trusted_hosts is None:
            logger.warning(
                "X-Forwarded-Proto is trusted from every peer; set "
                "FORWARDED_ALLOW_IPS to the proxy addresses if the app can be "
                "reached directly"
            )

    def _peer_is_trusted(self, scope: Scope) -> bool:
        if self.trusted_hosts is None:
            return True
        client = scope.get("client")
        if not client:
            return False
        return client[0] in self.trusted_hosts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and self._peer_is_trusted(scope):
            headers = dict(scope["headers"])
            if headers.get(b"x-forwarded-proto") == b"https":
                scope["scheme"] = "https"
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Add baseline security response headers to every HTTP response.

    Sets ``X-Content-Type-Options``, ``Referrer-Policy`` and a
    ``frame-ancestors 'self'`` policy, plus ``Strict-Transport-Security`` when the
    request scheme is ``https``. A header a route already sets is kept, so a route
    can send its own Content-Security-Policy. A full Content-Security-Policy is
    left to the proxy, because Reflex pages need inline scripts.

    Wrap it inside ``ForceHTTPSMiddleware`` so the scheme is already corrected
    behind a TLS-terminating proxy when HSTS is decided.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        secure = scope.get("scheme") == "https"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in BASE_SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                if secure:
                    headers.setdefault("Strict-Transport-Security", HSTS)
            await send(message)

        await self.app(scope, receive, send_with_headers)
