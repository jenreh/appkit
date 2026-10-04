"""Service encapsulating password-reset business logic.

Owns all database/business logic for requesting and confirming password
resets so the Reflex states stay thin (UI vars + outcome-to-toast mapping).

Security property preserved: :meth:`request_reset` never reveals whether an
email exists — it returns a coarse outcome and the state always shows the
generic success message.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_commons.security import generate_password_hash
from appkit_user.authentication.backend.database import (
    password_history_repo,
    password_reset_request_repo,
    password_reset_token_repo,
    session_repo,
    user_repo,
)
from appkit_user.authentication.backend.database.user_repository import (
    get_name_from_email,
)
from appkit_user.authentication.backend.services.email_service import get_email_service
from appkit_user.authentication.backend.types import PasswordResetType
from appkit_user.authentication.password_policy import PASSWORD_REGEX
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Number of previous passwords checked for reuse.
_PASSWORD_HISTORY_DEPTH = 6


class RequestResetOutcome(Enum):
    """Coarse result of :meth:`PasswordResetService.request_reset`.

    All non-error outcomes are treated identically by the UI (generic success
    message) so the caller cannot infer whether the email exists.
    """

    INVALID_EMAIL = auto()
    ACCEPTED = auto()


class ConfirmResetOutcome(Enum):
    """Result of :meth:`PasswordResetService.confirm_reset`."""

    INVALID_PASSWORD = auto()
    PASSWORD_MISMATCH = auto()
    INVALID_TOKEN = auto()
    PASSWORD_REUSED = auto()
    USER_NOT_FOUND = auto()
    SUCCESS = auto()
    ERROR = auto()


class ChangePasswordOutcome(Enum):
    """Result of :meth:`PasswordResetService.change_password`."""

    INVALID_PASSWORD = auto()
    PASSWORD_MISMATCH = auto()
    INCORRECT_CURRENT_PASSWORD = auto()
    PASSWORD_REUSED = auto()
    USER_NOT_FOUND = auto()
    SUCCESS = auto()
    ERROR = auto()


@dataclass(frozen=True)
class ConfirmResetResult:
    """Typed result of confirming a password reset."""

    outcome: ConfirmResetOutcome


class PasswordResetService:
    """Business logic for password-reset request and confirmation flows."""

    async def request_reset(self, email: str) -> RequestResetOutcome:
        """Validate, rate-limit, create a token and send the reset email.

        Never raises for expected failures; on any unexpected error it logs and
        returns :attr:`RequestResetOutcome.ACCEPTED` so the caller can still
        show the generic success message (no information leak).

        Args:
            email: The (already normalized) email address to reset.

        Returns:
            :attr:`RequestResetOutcome.INVALID_EMAIL` when the format is bad,
            otherwise :attr:`RequestResetOutcome.ACCEPTED`.
        """
        if not EMAIL_REGEX.match(email):
            return RequestResetOutcome.INVALID_EMAIL

        try:
            config: AuthenticationConfiguration = service_registry().get(
                AuthenticationConfiguration
            )

            async with get_asyncdb_session() as db:
                request_count = await password_reset_request_repo.count_recent_requests(
                    db, email, hours=1
                )

                if request_count >= config.password_reset.max_requests_per_hour:
                    # Rate limited - silent response for security
                    logger.warning("Rate limit exceeded for password reset: %s", email)
                    return RequestResetOutcome.ACCEPTED

                user_entity = await user_repo.find_by_email(db, email)

                if not user_entity:
                    # Email not found - silent response for security
                    logger.info(
                        "Password reset requested for non-existent email: %s", email
                    )
                    # Still log the request for rate limiting
                    await password_reset_request_repo.log_request(db, email)
                    await db.commit()
                    return RequestResetOutcome.ACCEPTED

                # Eagerly load user attributes while in session context
                user_id = user_entity.id
                user_name = (
                    get_name_from_email(user_entity.email, user_entity.name) or ""
                )

                # Generate token (only its hash is persisted; raw token emailed)
                _, raw_token = await password_reset_token_repo.create_token(
                    db,
                    user_id=user_id,
                    email=email,
                    reset_type=PasswordResetType.USER_INITIATED,
                    expiry_minutes=config.password_reset.token_expiry_minutes,
                )

                await self._send_reset_email(
                    config, email, raw_token, user_name, user_id
                )

                # Log request for rate limiting
                await password_reset_request_repo.log_request(db, email)

                # Commit all changes: token creation and request logging
                await db.commit()

            return RequestResetOutcome.ACCEPTED

        except Exception:
            logger.exception("Error during password reset request")
            # Still report accepted for security (no information leak)
            return RequestResetOutcome.ACCEPTED

    async def _send_reset_email(
        self,
        config: AuthenticationConfiguration,
        email: str,
        raw_token: str,
        user_name: str,
        user_id: int,
    ) -> None:
        """Send the reset email via the configured email service."""
        email_service = get_email_service()
        if not email_service:
            logger.error("Email service not configured")
            return

        # public_base_url carries a non-default port and the app path prefix;
        # without them the link is dead (the OAuth redirect URLs and the email
        # logo_url are built the same way).
        reset_url = f"{config.public_base_url}/password-reset/confirm?token={raw_token}"

        # If the configured email service is a MockService (e.g. in tests/dev),
        # log the reset URL for debugging purposes.
        if getattr(email_service.__class__, "__name__", "") == "MockEmailProvider":
            logger.debug("Password reset URL (mock): %s", reset_url)

        success = await email_service.send_password_reset_email(
            to_email=email,
            reset_link=reset_url,
            user_name=user_name,
            reset_type=PasswordResetType.USER_INITIATED,
        )

        if success:
            logger.info("Password reset email sent to user_id=%d", user_id)
        else:
            logger.error("Failed to send password reset email to user_id=%d", user_id)

    async def confirm_reset(
        self, token: str, new_password: str, confirm_password: str
    ) -> ConfirmResetResult:
        """Validate and apply a new password for the given reset token.

        Args:
            token: The raw reset token from the emailed link.
            new_password: The candidate new password.
            confirm_password: The confirmation of the new password.

        Returns:
            A :class:`ConfirmResetResult` whose outcome the caller maps to a
            toast/redirect.
        """
        # 1. Validate password format
        if not PASSWORD_REGEX.match(new_password):
            return ConfirmResetResult(ConfirmResetOutcome.INVALID_PASSWORD)

        # 2. Verify passwords match
        if new_password != confirm_password:
            return ConfirmResetResult(ConfirmResetOutcome.PASSWORD_MISMATCH)

        try:
            async with get_asyncdb_session() as db:
                outcome = await self._apply_reset(db, token, new_password)
            return ConfirmResetResult(outcome)

        except Exception:
            logger.exception("Error during password reset confirmation")
            return ConfirmResetResult(ConfirmResetOutcome.ERROR)

    async def _apply_reset(
        self, db: AsyncSession, token: str, new_password: str
    ) -> ConfirmResetOutcome:
        """Apply the password change inside an open session/transaction.

        Returns the outcome so :meth:`confirm_reset` can wrap it; keeps the DB
        side effects (hash, history, token, session invalidation) in one place.
        """
        # 3. Re-validate token
        token_entity = await password_reset_token_repo.find_by_token(db, token)

        if not token_entity or not token_entity.is_valid():
            return ConfirmResetOutcome.INVALID_TOKEN

        # Eagerly load token attributes while in session context
        token_id = token_entity.id
        token_user_id = token_entity.user_id
        token_reset_type = token_entity.reset_type

        # 4. Check password history (last 6 passwords)
        is_reused = await password_history_repo.check_password_reuse(
            db, token_user_id, new_password, n=_PASSWORD_HISTORY_DEPTH
        )

        if is_reused:
            return ConfirmResetOutcome.PASSWORD_REUSED

        # 5. Get user entity
        user_entity = await user_repo.find_by_id(db, token_user_id)
        if not user_entity:
            return ConfirmResetOutcome.USER_NOT_FOUND

        # 6. Burn the token first (flush only) so the *same* commit that writes
        # the new password also retires the token — a crash in between must not
        # leave a used token replayable.
        await password_reset_token_repo.mark_as_used(db, token_id)

        # 7. Apply the password, record history and revoke sessions. This also
        # clears needs_password_reset, which covers the admin-forced case.
        await self._persist_new_password(
            db,
            user_entity,
            new_password,
            change_reason=token_reset_type,
            user_id=token_user_id,
        )

        logger.info(
            "Password reset completed for user_id=%d, type=%s",
            token_user_id,
            token_reset_type,
        )

        return ConfirmResetOutcome.SUCCESS

    async def _persist_new_password(
        self,
        db: AsyncSession,
        user_entity: Any,
        new_password: str,
        change_reason: str,
        user_id: int | None = None,
    ) -> None:
        """Write a new password, append it to history and revoke sessions.

        Single place where a password actually changes, so every entry point
        (emailed reset *and* profile change) enforces the same policy: the hash
        is computed once and reused for the history row, and all existing
        sessions are dropped so a stolen session cannot outlive the change.
        """
        # Hash EXACTLY ONCE and thread the same hash into both the user entity
        # and the password-history record. scrypt is deliberately CPU-heavy, so
        # keep it off the event loop.
        new_password_hash = await asyncio.to_thread(
            generate_password_hash, new_password
        )

        user_entity._password = new_password_hash  # noqa: SLF001
        user_entity.needs_password_reset = False

        target_user_id = user_id if user_id is not None else user_entity.id

        await password_history_repo.save_password_to_history(
            db,
            user_id=target_user_id,
            password_hash=new_password_hash,
            change_reason=change_reason,
        )

        await db.commit()

        # Force re-login everywhere (the caller's own session included).
        await session_repo.delete_all_by_user_id(db, target_user_id)
        await db.commit()

    async def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> ChangePasswordOutcome:
        """Change a signed-in user's password from the profile page.

        Enforces the same policy as the emailed-reset flow — complexity rules,
        the last-``_PASSWORD_HISTORY_DEPTH`` reuse check, a history entry and
        session revocation — so the policy cannot be sidestepped by choosing a
        different entry point.

        Args:
            user_id: The authenticated user changing their own password.
            current_password: The user's existing password, re-entered.
            new_password: The candidate new password.

        Returns:
            The outcome the caller maps to a toast.
        """
        if not PASSWORD_REGEX.match(new_password):
            return ChangePasswordOutcome.INVALID_PASSWORD

        if user_id <= 0:
            return ChangePasswordOutcome.USER_NOT_FOUND

        try:
            async with get_asyncdb_session() as db:
                outcome = await self._apply_password_change(
                    db, user_id, current_password, new_password
                )
        except Exception:
            logger.exception("Error during password change for user_id=%d", user_id)
            return ChangePasswordOutcome.ERROR

        if outcome is ChangePasswordOutcome.SUCCESS:
            logger.info("Password changed for user_id=%d", user_id)
        return outcome

    async def _apply_password_change(
        self,
        db: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> ChangePasswordOutcome:
        """Verify the current password and apply the new one.

        ``check_password`` runs scrypt, which is deliberately CPU-heavy, so it
        is pushed onto a worker thread rather than stalling the event loop.
        """
        user_entity = await user_repo.find_by_id(db, user_id)
        if not user_entity:
            return ChangePasswordOutcome.USER_NOT_FOUND

        if not await asyncio.to_thread(user_entity.check_password, current_password):
            return ChangePasswordOutcome.INCORRECT_CURRENT_PASSWORD

        if await password_history_repo.check_password_reuse(
            db, user_id, new_password, n=_PASSWORD_HISTORY_DEPTH
        ):
            return ChangePasswordOutcome.PASSWORD_REUSED

        await self._persist_new_password(
            db,
            user_entity,
            new_password,
            change_reason=PasswordResetType.USER_INITIATED,
            user_id=user_id,
        )
        return ChangePasswordOutcome.SUCCESS


# Stateless service — a single shared instance is safe to reuse.
_password_reset_service = PasswordResetService()


def get_password_reset_service() -> PasswordResetService:
    """Get the shared :class:`PasswordResetService` instance."""
    return _password_reset_service
