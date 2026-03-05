"""Authentication service for MCP user analytics.

Extracts user identity from the reflex_session cookie and validates
session and role information against the database.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from appkit_commons.database.session import get_session_manager
from appkit_mcp_commons.context import UserContext
from appkit_mcp_commons.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


def authenticate_user(session_id: str) -> UserContext:
    """Authenticate a user from their session ID.

    Looks up the session in the database, validates it is not expired,
    and returns the associated user context.

    Args:
        session_id: The reflex_session cookie value.

    Returns:
        UserContext with user details.

    Raises:
        AuthenticationError: If the session is invalid or expired.
    """
    # Lazy imports to avoid circular dependency at module load time
    # appkit-user entities are needed for DB lookup
    try:
        from appkit_user.authentication.backend.database.entities import (  # noqa: PLC0415
            UserSessionEntity,
        )
    except ImportError as e:
        logger.error("Failed to import appkit-user entities: %s", e)
        raise AuthenticationError("Authentication backend unavailable") from e

    if not session_id:
        raise AuthenticationError("No session ID provided")

    with get_session_manager().session() as session:
        stmt = select(UserSessionEntity).where(
            UserSessionEntity.session_id == session_id
        )
        db_session = session.execute(stmt).scalar_one_or_none()

        if not db_session:
            logger.warning("Session not found: %.20s...", session_id)
            raise AuthenticationError("Invalid session")

        if _is_expired(db_session.expires_at):
            logger.warning("Expired session for user_id=%d", db_session.user_id)
            raise AuthenticationError("Session expired")

        user = db_session.user
        if not user:
            raise AuthenticationError("User not found for session")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        logger.debug(
            "Authenticated user_id=%d, is_admin=%s, roles=%s",
            user.id,
            user.is_admin,
            user.roles,
        )

        return UserContext(
            user_id=user.id,
            is_admin=user.is_admin,
            roles=user.roles or [],
        )


def _is_expired(expires_at: datetime) -> bool:
    """Check if a datetime is in the past."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return datetime.now(UTC) >= expires_at
