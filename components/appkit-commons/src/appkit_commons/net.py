"""Outbound-request guard against server-side request forgery.

Use ``assert_public_http_url`` before fetching a URL that a third party chose
(generator responses, tool arguments). It refuses non-HTTP(S) schemes and hosts
that resolve to private, loopback, link-local or otherwise non-public addresses.

The name is resolved here and again by the HTTP client, so a DNS-rebinding host
could still switch between the lookups; callers should also disable redirects,
and an egress policy at the network level remains the complete defense.
"""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeURLError(ValueError):
    """Raised when a URL must not be fetched by the server."""


def _is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast


async def assert_public_http_url(url: str) -> None:
    """Raise ``UnsafeURLError`` unless ``url`` is an HTTP(S) URL to a public host."""
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES or not parts.hostname:
        raise UnsafeURLError("Only http(s) URLs are allowed")
    if parts.username or parts.password:
        raise UnsafeURLError("URLs with credentials are not allowed")

    port = parts.port or (443 if parts.scheme == "https" else 80)
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeURLError("URL host could not be resolved") from e

    for info in infos:
        address = ipaddress.ip_address(str(info[4][0]).split("%", 1)[0])
        if not _is_public(address):
            logger.warning(
                "Blocked request to non-public address for %s", parts.hostname
            )
            raise UnsafeURLError("URL resolves to a non-public address")
