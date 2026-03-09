import logging

from pydantic import BaseModel, Field
from starlette.requests import Request

logger = logging.getLogger(__name__)


class UserContext(BaseModel):
    """Authenticated user context extracted from session."""

    user_id: int
    is_admin: bool = False
    roles: list[str] = Field(default_factory=list)


def get_user_context_default() -> UserContext:
    """Get a default unauthenticated user context."""
    return UserContext(user_id=-1, is_admin=False, roles=[])


def extract_session_id(request: Request) -> str | None:
    """Extract reflex_session cookie from the HTTP request.

    Args:
        request: Starlette request injected via ``CurrentRequest()``.

    Returns:
        Session ID string or None.
    """
    if hasattr(request, "cookies"):
        return request.cookies.get("reflex_session")

    return None


def extract_user_id(request: Request) -> int:
    """Extract user ID from ``x-user-id`` header or query parameter.

    Checks the HTTP header first, then falls back to URL query params.
    Returns -1 when the value is absent or invalid.

    Args:
        request: Starlette request injected via ``CurrentRequest()``.

    Returns:
        User ID integer or -1.
    """
    raw: str | None = request.headers.get("x-user-id")

    if raw is None:
        raw = request.query_params.get("x-user-id")

    if raw is None:
        logger.debug("No x-user-id in headers or query params")
        return -1

    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid x-user-id value: %s", raw)
        return -1
