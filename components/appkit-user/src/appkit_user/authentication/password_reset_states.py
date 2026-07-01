"""Password reset state management for user-initiated and admin-forced resets."""

import logging
import re
from collections.abc import AsyncGenerator

import reflex as rx

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
from appkit_user.authentication.backend.services import get_email_service
from appkit_user.authentication.backend.types import PasswordResetType
from appkit_user.authentication.password_policy import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_MISMATCH_MESSAGE,
    PASSWORD_REGEX,
    calculate_password_strength,
)
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class PasswordResetRequestState(rx.State):
    """State for handling password reset requests (email entry)."""

    email: str = ""
    email_error: str = ""
    is_loading: bool = False
    is_submitted: bool = False
    success_message: str = (
        "Wenn diese E-Mail-Adresse registriert ist, erhalten Sie eine Bestätigungsmail."
    )

    @rx.event
    def set_email(self, value: str) -> None:
        """Set email and clear errors."""
        self.email = value.strip().lower()
        self.email_error = ""

    @rx.event
    async def request_password_reset(self) -> AsyncGenerator:
        """Request password reset token and send email.

        Security: Always shows success message, never reveals if email exists.
        """
        self.is_loading = True
        self.email_error = ""
        self.is_submitted = False
        yield

        try:
            # 1. Validate email format
            if not EMAIL_REGEX.match(self.email):
                self.email_error = "Bitte geben Sie eine gültige E-Mail-Adresse ein."
                yield
                return

            config: AuthenticationConfiguration = service_registry().get(
                AuthenticationConfiguration
            )

            async with get_asyncdb_session() as db:
                # 2. Check rate limit (max 3/hour per email)
                request_count = await password_reset_request_repo.count_recent_requests(
                    db, self.email, hours=1
                )

                if request_count >= config.password_reset.max_requests_per_hour:
                    # Rate limited - silent response for security
                    logger.warning(
                        "Rate limit exceeded for password reset: %s", self.email
                    )
                    self.is_submitted = True
                    yield
                    return

                # 3. Find user by email
                user_entity = await user_repo.find_by_email(db, self.email)

                if not user_entity:
                    # Email not found - silent response for security
                    logger.info(
                        "Password reset requested for non-existent email: %s",
                        self.email,
                    )
                    # Still log the request for rate limiting
                    await password_reset_request_repo.log_request(db, self.email)
                    # Commit the request log
                    await db.commit()
                    self.is_submitted = True
                    yield
                    return

                # Eagerly load user attributes while in session context
                user_id = user_entity.id
                user_name = (
                    get_name_from_email(user_entity.email, user_entity.name) or ""
                )

                # 4. Generate token (only its hash is persisted)
                _, raw_token = await password_reset_token_repo.create_token(
                    db,
                    user_id=user_id,
                    email=self.email,
                    reset_type=PasswordResetType.USER_INITIATED,
                    expiry_minutes=config.password_reset.token_expiry_minutes,
                )

                # 5. Send email
                email_service = get_email_service()
                if email_service:
                    reset_url = (
                        f"{config.server_url}/password-reset/confirm?token={raw_token}"
                    )

                    # If the configured email service is a MockService (e.g. in
                    # tests/dev), log the reset URL for debugging purposes.
                    if (
                        getattr(email_service.__class__, "__name__", "")
                        == "MockEmailProvider"
                    ):
                        logger.debug("Password reset URL (mock): %s", reset_url)

                    success = await email_service.send_password_reset_email(
                        to_email=self.email,
                        reset_link=reset_url,
                        user_name=user_name,
                        reset_type=PasswordResetType.USER_INITIATED,
                    )

                    if success:
                        logger.info("Password reset email sent to user_id=%d", user_id)
                    else:
                        logger.error(
                            "Failed to send password reset email to user_id=%d",
                            user_id,
                        )
                else:
                    logger.error("Email service not configured")

                # 6. Log request for rate limiting
                await password_reset_request_repo.log_request(db, self.email)

                # Commit all changes: token creation and request logging
                await db.commit()

            # 7. Always show success message (security)
            self.is_submitted = True
            yield

        except Exception:
            logger.exception("Error during password reset request")
            # Still show success message for security
            self.is_submitted = True
            yield

        finally:
            self.is_loading = False


class PasswordResetConfirmState(rx.State):
    """State for confirming password reset with new password."""

    token: str = ""
    token_error: str = ""
    user_email: str = ""
    user_name: str = ""
    user_id: int = 0

    new_password: str = ""
    confirm_password: str = ""
    password_error: str = ""
    password_history_error: str = ""
    is_loading: bool = False

    # Password strength indicators
    strength_value: int = 0
    has_length: bool = False
    has_upper: bool = False
    has_lower: bool = False
    has_digit: bool = False
    has_special: bool = False

    @rx.event
    async def validate_token(self) -> AsyncGenerator:
        """Validate token from URL on page load."""
        # Extract token from URL query params
        self.token = self.router.page.params.get("token", "")

        if not self.token:
            self.token_error = "Kein gültiger Token gefunden."  # noqa: S105
            yield rx.redirect("/password-reset")
            return

        try:
            async with get_asyncdb_session() as db:
                token_entity = await password_reset_token_repo.find_by_token(
                    db, self.token
                )

                if not token_entity:
                    self.token_error = "Ungültiger oder abgelaufener Token."  # noqa: S105
                    logger.warning("Invalid password reset token presented")
                    yield rx.redirect("/password-reset")
                    return

                if not token_entity.is_valid():
                    if token_entity.is_used:
                        self.token_error = "Dieser Token wurde bereits verwendet."  # noqa: S105
                    else:
                        self.token_error = "Dieser Token ist abgelaufen."  # noqa: S105
                    logger.warning(
                        "Invalid token state: used=%s, expired=%s",
                        token_entity.is_used,
                        token_entity.is_expired(),
                    )
                    yield rx.redirect("/password-reset")
                    return

                # Load user info for display
                user_entity = await user_repo.find_by_id(db, token_entity.user_id)
                if user_entity:
                    self.user_email = user_entity.email or ""
                    self.user_name = (
                        get_name_from_email(user_entity.email, user_entity.name) or ""
                    )
                    self.user_id = user_entity.id
                else:
                    self.token_error = "Benutzer nicht gefunden."  # noqa: S105
                    yield rx.redirect("/password-reset")
                    return

        except Exception:
            logger.exception("Error validating token")
            self.token_error = "Fehler bei der Token-Validierung."  # noqa: S105
            yield rx.redirect("/password-reset")

    @rx.event
    def set_new_password(self, value: str) -> None:
        """Set password and calculate strength."""
        self.new_password = value
        self.password_error = ""
        self.password_history_error = ""

        # Calculate strength indicators
        result = calculate_password_strength(value)
        self.has_length = result.has_length
        self.has_upper = result.has_upper
        self.has_lower = result.has_lower
        self.has_digit = result.has_digit
        self.has_special = result.has_special
        self.strength_value = result.strength

    @rx.event
    def set_confirm_password(self, value: str) -> None:
        """Set confirm password and validate match."""
        self.confirm_password = value
        if self.new_password and self.new_password != value:
            self.password_error = PASSWORD_MISMATCH_MESSAGE
        else:
            self.password_error = ""

    @rx.event
    async def confirm_password_reset(self) -> AsyncGenerator:
        """Complete password reset with new password."""
        self.is_loading = True
        self.password_error = ""
        self.password_history_error = ""
        yield

        try:
            # 1. Validate password format
            if not PASSWORD_REGEX.match(self.new_password):
                self.password_error = (
                    f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen lang sein "
                    "und Großbuchstaben, Kleinbuchstaben, Zahlen und "
                    "Sonderzeichen enthalten."
                )
                yield
                return

            # 2. Verify passwords match
            if self.new_password != self.confirm_password:
                self.password_error = PASSWORD_MISMATCH_MESSAGE
                yield
                return

            async with get_asyncdb_session() as db:
                # 3. Re-validate token
                token_entity = await password_reset_token_repo.find_by_token(
                    db, self.token
                )

                if not token_entity or not token_entity.is_valid():
                    yield rx.toast.error(
                        "Token ist ungültig oder abgelaufen.", position="top-right"
                    )
                    yield rx.redirect("/password-reset")
                    return

                # Eagerly load token attributes while in session context
                token_id = token_entity.id
                token_user_id = token_entity.user_id
                token_reset_type = token_entity.reset_type

                # 4. Check password history (last 6 passwords)
                is_reused = await password_history_repo.check_password_reuse(
                    db, token_user_id, self.new_password, n=6
                )

                if is_reused:
                    self.password_history_error = (
                        "Dieses Passwort wurde bereits verwendet. "  # noqa: S105
                        "Bitte wählen Sie ein anderes Passwort."
                    )
                    yield
                    return

                # 5. Get user entity
                user_entity = await user_repo.find_by_id(db, token_user_id)
                if not user_entity:
                    yield rx.toast.error(
                        "Benutzer nicht gefunden.", position="top-right"
                    )
                    return

                # 6. Hash new password
                new_password_hash = generate_password_hash(self.new_password)

                # 7. Start transaction: update password, log history, mark token,
                # clear sessions
                user_entity._password = new_password_hash  # noqa: SLF001

                # Log to password history
                await password_history_repo.save_password_to_history(
                    db,
                    user_id=token_user_id,
                    password_hash=new_password_hash,
                    change_reason=token_reset_type,
                )

                # Mark token as used
                await password_reset_token_repo.mark_as_used(db, token_id)

                # Clear needs_password_reset flag if it was admin-forced
                if token_reset_type == PasswordResetType.ADMIN_FORCED:
                    user_entity.needs_password_reset = False

                # Commit all changes: user password, history, and token
                await db.commit()

                # 8. Clear all existing sessions for user (force re-login)
                await session_repo.delete_all_by_user_id(db, token_user_id)

                # Commit session deletion
                await db.commit()

                logger.info(
                    "Password reset completed for user_id=%d, type=%s",
                    token_user_id,
                    token_reset_type,
                )

            # 9. Show success and redirect to login
            yield rx.toast.success(
                "Passwort erfolgreich zurückgesetzt. Bitte melden Sie sich an.",
                position="top-right",
            )
            yield rx.redirect("/login")

        except Exception:
            logger.exception("Error during password reset confirmation")
            yield rx.toast.error(
                "Fehler beim Zurücksetzen des Passworts.", position="top-right"
            )

        finally:
            self.is_loading = False
