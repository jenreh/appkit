"""Service encapsulating password-reset business logic.

Owns all database/business logic for requesting and confirming password
resets so the Reflex states stay thin (UI vars + outcome-to-toast mapping).

Security property preserved: :meth:`request_reset` never reveals whether an
email exists — it returns a coarse outcome and the state always shows the
generic success message.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum, auto

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

        reset_url = f"{config.server_url}/password-reset/confirm?token={raw_token}"

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

        # 6. Hash new password EXACTLY ONCE and thread the same hash into
        # both the user entity and the password-history record.
        new_password_hash = generate_password_hash(new_password)

        # 7. Update password, log history, mark token, clear flag
        user_entity._password = new_password_hash  # noqa: SLF001

        await password_history_repo.save_password_to_history(
            db,
            user_id=token_user_id,
            password_hash=new_password_hash,
            change_reason=token_reset_type,
        )

        await password_reset_token_repo.mark_as_used(db, token_id)

        # Clear needs_password_reset flag if it was admin-forced
        if token_reset_type == PasswordResetType.ADMIN_FORCED:
            user_entity.needs_password_reset = False

        # Commit all changes: user password, history, and token
        await db.commit()

        # 8. Clear all existing sessions for user (force re-login)
        await session_repo.delete_all_by_user_id(db, token_user_id)
        await db.commit()

        logger.info(
            "Password reset completed for user_id=%d, type=%s",
            token_user_id,
            token_reset_type,
        )

        return ConfirmResetOutcome.SUCCESS


# Stateless service — a single shared instance is safe to reuse.
_password_reset_service = PasswordResetService()


def get_password_reset_service() -> PasswordResetService:
    """Get the shared :class:`PasswordResetService` instance."""
    return _password_reset_service
