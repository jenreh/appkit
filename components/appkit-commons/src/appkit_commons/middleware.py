from starlette.types import ASGIApp, Receive, Scope, Send


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
