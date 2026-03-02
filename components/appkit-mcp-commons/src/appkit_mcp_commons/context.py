import logging
from typing import Any

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
    return UserContext(user_id=0, is_admin=False, roles=[])


def extract_session_id(ctx: Any) -> str | None:
    """Extract reflex_session cookie from context.

    Args:
        ctx: FastMCP context or request object.

    Returns:
        Session ID string or None.
    """
    if ctx is None:
        return None

    request: Request | None = None
    if hasattr(ctx, "request"):
        # FastMCP context wrapping Starlette request
        request = ctx.request
    elif isinstance(ctx, Request):
        # Direct Starlette request
        request = ctx

    if request and hasattr(request, "cookies"):
        return request.cookies.get("reflex_session")

    return None
