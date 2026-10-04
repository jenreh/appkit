"""Transport-agnostic session validation.

Single source of truth for "is this session id still good?". Used by the
Reflex WebSocket filter, the ASGI page guard and the REST/MCP dependency, so
none of them re-implement the expiry rules.

This module must not import ``appkit_user.authentication.states`` — states
imports from here.
"""

import fnmatch
import functools
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.database import UserSessionEntity, session_repo
from appkit_user.authentication.backend.models import User
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

LOGIN_ROUTE: Final = "/login"


@functools.lru_cache(maxsize=1)
def _auth_config() -> AuthenticationConfiguration:
    """Resolve the authentication configuration lazily and cache it."""
    return service_registry().get(AuthenticationConfiguration)


class SessionStatus(StrEnum):
    """Outcome of a session validation."""

    VALID = "valid"
    EXPIRED = "expired"
    ABSENT = "absent"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SessionValidationResult:
    """Result of validating a session id against the session store."""

    status: SessionStatus
    user: User | None = None
    expires_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """Whether the session may be used to serve the request."""
        return self.status is SessionStatus.VALID


def _normalize_path(path: str) -> str:
    """Strip query/fragment and a trailing slash (except for the bare root)."""
    for separator in ("?", "#"):
        path = path.split(separator, 1)[0]
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return path


def is_public_route(path: str) -> bool:
    """Check whether a path is reachable without a valid session.

    The allowlist is ``AuthenticationConfiguration.public_routes``; everything
    not matched is default-deny. Patterns are fnmatch globs, so ``*`` also
    matches ``/`` — ``/oauth/*/callback`` therefore matches any provider
    segment, and a pattern such as ``/docs/*`` matches nested paths too.

    Args:
        path: Request path, with or without query string.

    Returns:
        True if the path matches one of the configured public routes.
    """
    normalized = _normalize_path(path)
    return any(
        fnmatch.fnmatchcase(normalized, pattern)
        for pattern in _auth_config().public_routes
    )


def safe_redirect_path(path: str) -> str:
    """Return ``path`` if it is a local path, otherwise an empty string.

    Post-login redirect targets come from the client (Reflex builds
    ``router.url.path`` from the browser's own ``asPath``), so they must not be
    trusted. A value starting with ``//`` or ``/\\`` is a protocol-relative URL
    that navigates off-site, which would make the login flow an open redirect.

    Args:
        path: Candidate redirect target.

    Returns:
        The path when it is a safe same-origin target, else "".
    """
    if not path.startswith("/") or path.startswith(("//", "/\\")):
        return ""
    return path


def session_cookie_name() -> str:
    """Name of the cookie mirroring the auth token."""
    return _auth_config().effective_session_cookie_name


def is_session_filter_enabled() -> bool:
    """Whether the session filter is active."""
    return _auth_config().session_filter_enabled


def _as_aware_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime (the DB column stores naive UTC)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _classify(row: UserSessionEntity | None) -> SessionValidationResult:
    """Turn a session row into a validation result."""
    if row is None:
        return SessionValidationResult(SessionStatus.ABSENT)

    if row.is_expired():
        return SessionValidationResult(SessionStatus.EXPIRED)

    if row.user is None:
        logger.warning("Session %s has no user row, denying", row.id)
        return SessionValidationResult(SessionStatus.EXPIRED)

    if not row.user.is_active:
        logger.warning(
            "Session %s belongs to inactive user_id=%s, denying", row.id, row.user_id
        )
        return SessionValidationResult(SessionStatus.EXPIRED)

    return SessionValidationResult(
        SessionStatus.VALID,
        user=User.model_validate(row.user),
        expires_at=_as_aware_utc(row.expires_at),
    )


class SessionValidator:
    """Looks a session id up in the session store and classifies it."""

    async def validate(
        self, session_id: str, user_id: int = 0
    ) -> SessionValidationResult:
        """Validate a session id, optionally scoped to a user.

        Never raises: an unreachable or failing database yields
        ``SessionStatus.ERROR`` so callers can fail closed.

        Args:
            session_id: The auth token identifying the session.
            user_id: Owning user id, when known, to scope the lookup.

        Returns:
            The validation result; ``user`` and ``expires_at`` are only set for
            a VALID session.
        """
        if not session_id or not session_id.strip():
            return SessionValidationResult(SessionStatus.ABSENT)

        try:
            async with get_asyncdb_session() as db:
                if user_id > 0:
                    row = await session_repo.find_by_user_and_session_id(
                        db, user_id, session_id
                    )
                else:
                    row = await session_repo.find_by_session_id(db, session_id)
                # Classified inside the session: ``row.user`` is a lazy-loaded
                # relationship and must be touched while the row is attached.
                return _classify(row)
        except Exception as e:
            logger.warning("Session validation failed for user_id=%s: %s", user_id, e)
            return SessionValidationResult(SessionStatus.ERROR)
