"""Password reset state management for user-initiated and admin-forced resets."""

import logging
import re
from collections.abc import AsyncGenerator

import reflex as rx

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_commons.security import generate_password_hash
from appkit_user.authentication.backend.database.password_history_repository import (
    password_history_repo,
)
from appkit_user.authentication.backend.database.password_reset_repository import (
    password_reset_token_repo,
)
from appkit_user.authentication.backend.database.password_reset_request_repository import (
    password_reset_request_repo,
)
from appkit_user.authentication.backend.database.user_repository import user_repo
from appkit_user.authentication.backend.database.user_session_repository import (
    session_repo,
)
from appkit_user.authentication.backend.services.email_service import (
    PasswordResetType,
    get_email_service,
)
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Password validation (same as profile)
MIN_PASSWORD_LENGTH = 12
PASSWORD_REGEX = re.compile(
    r"^(?=.{"
    + str(MIN_PASSWORD_LENGTH)
    + r",})(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).*$"
)


class PasswordResetRequestState(rx.State):
    """State for handling password reset requests (email entry)."""

    email: str = ""
    email_error: str = ""
    is_loading: bool = False
    is_submitted: bool = False
    success_message: str = (
        "Wenn diese E-Mail-Adresse registriert ist, erhalten Sie eine Bestätigungsmail."
    )

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
                user_name = user_entity.name or user_entity.email.split("@")[0]

                # 4. Generate token
                token_entity = await password_reset_token_repo.create_token(
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
                        f"{config.server_url}/password-reset/confirm"
                        f"?token={token_entity.token}"
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

        except Exception as e:
            logger.exception("Error during password reset request: %s", e)
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
                    logger.warning("Invalid password reset token: %s", self.token)
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
                    self.user_name = user_entity.name or user_entity.email.split("@")[0]
                    self.user_id = user_entity.id
                else:
                    self.token_error = "Benutzer nicht gefunden."  # noqa: S105
                    yield rx.redirect("/password-reset")
                    return

        except Exception as e:
            logger.exception("Error validating token: %s", e)
            self.token_error = "Fehler bei der Token-Validierung."  # noqa: S105
            yield rx.redirect("/password-reset")

    @rx.event
    def set_new_password(self, value: str) -> None:
        """Set password and calculate strength."""
        self.new_password = value
        self.password_error = ""
        self.password_history_error = ""

        # Calculate strength indicators
        self.has_length = len(value) >= MIN_PASSWORD_LENGTH
        self.has_upper = any(c.isupper() for c in value)
        self.has_lower = any(c.islower() for c in value)
        self.has_digit = any(c.isdigit() for c in value)
        self.has_special = any(not c.isalnum() for c in value)

        criteria_met = sum(
            [
                self.has_upper,
                self.has_lower,
                self.has_digit,
                self.has_special,
                self.has_length,
            ]
        )

        if criteria_met == 1:
            self.strength_value = 20
        elif criteria_met == 2:  # noqa: PLR2004
            self.strength_value = 40
        elif criteria_met == 3:  # noqa: PLR2004
            self.strength_value = 60
        elif criteria_met == 4:  # noqa: PLR2004
            self.strength_value = 80
        elif criteria_met == 5:  # noqa: PLR2004
            self.strength_value = 100
        else:
            self.strength_value = 0

    @rx.event
    def set_confirm_password(self, value: str) -> None:
        """Set confirm password and validate match."""
        self.confirm_password = value
        if self.new_password and self.new_password != value:
            self.password_error = "Passwörter stimmen nicht überein."  # noqa: S105
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
                self.password_error = "Passwörter stimmen nicht überein."  # noqa: S105
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

        except Exception as e:
            logger.exception("Error during password reset confirmation: %s", e)
            yield rx.toast.error(
                "Fehler beim Zurücksetzen des Passworts.", position="top-right"
            )

        finally:
            self.is_loading = False
