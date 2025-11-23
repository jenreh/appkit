from starlette.types import ASGIApp, Receive, Scope, Send


# Redirect HTTP to HTTPS when behind a proxy (Azure) that sets X-Forwarded-Proto
class ForceHTTPSMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            # Read headers to find X-Forwarded-Proto
            headers = dict(scope["headers"])
            # If Azure says it was HTTPS, force the scope to HTTPS
            if (
                b"x-forwarded-proto" in headers
                and headers[b"x-forwarded-proto"] == b"https"
            ):
                scope["scheme"] = "https"
        await self.app(scope, receive, send)
