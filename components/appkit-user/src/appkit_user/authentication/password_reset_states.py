"""Password reset state management for user-initiated and admin-forced resets.

These states are intentionally thin: they own only UI vars (form fields,
toasts, redirects, strength indicators) and delegate all database/business
logic to :class:`PasswordResetService`.
"""

import logging
from collections.abc import AsyncGenerator

import reflex as rx

from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.database import (
    password_reset_token_repo,
    user_repo,
)
from appkit_user.authentication.backend.database.user_repository import (
    get_name_from_email,
)
from appkit_user.authentication.backend.services import (
    ConfirmResetOutcome,
    RequestResetOutcome,
    get_password_reset_service,
)

# Re-exported for backwards compatibility with existing imports/tests.
from appkit_user.authentication.backend.services.password_reset_service import (  # noqa: E501
    EMAIL_REGEX,
)
from appkit_user.authentication.password_policy import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_MISMATCH_MESSAGE,
    PASSWORD_REGEX,
    calculate_password_strength,
)

logger = logging.getLogger(__name__)

__all__ = [
    "EMAIL_REGEX",
    "MIN_PASSWORD_LENGTH",
    "PASSWORD_MISMATCH_MESSAGE",
    "PASSWORD_REGEX",
    "PasswordResetConfirmState",
    "PasswordResetRequestState",
]


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
            outcome = await get_password_reset_service().request_reset(self.email)

            if outcome == RequestResetOutcome.INVALID_EMAIL:
                self.email_error = "Bitte geben Sie eine gültige E-Mail-Adresse ein."
                yield
                return

            # Always show success message (security: no info leak).
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
            result = await get_password_reset_service().confirm_reset(
                self.token, self.new_password, self.confirm_password
            )

            match result.outcome:
                case ConfirmResetOutcome.INVALID_PASSWORD:
                    self.password_error = (
                        f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen "
                        "lang sein und Großbuchstaben, Kleinbuchstaben, Zahlen und "
                        "Sonderzeichen enthalten."
                    )
                    yield
                case ConfirmResetOutcome.PASSWORD_MISMATCH:
                    self.password_error = PASSWORD_MISMATCH_MESSAGE
                    yield
                case ConfirmResetOutcome.INVALID_TOKEN:
                    yield rx.toast.error(
                        "Token ist ungültig oder abgelaufen.", position="top-right"
                    )
                    yield rx.redirect("/password-reset")
                case ConfirmResetOutcome.PASSWORD_REUSED:
                    self.password_history_error = (
                        "Dieses Passwort wurde bereits verwendet. "  # noqa: S105
                        "Bitte wählen Sie ein anderes Passwort."
                    )
                    yield
                case ConfirmResetOutcome.USER_NOT_FOUND:
                    yield rx.toast.error(
                        "Benutzer nicht gefunden.", position="top-right"
                    )
                case ConfirmResetOutcome.SUCCESS:
                    yield rx.toast.success(
                        "Passwort erfolgreich zurückgesetzt. Bitte melden Sie sich an.",
                        position="top-right",
                    )
                    yield rx.redirect("/login")
                case _:
                    yield rx.toast.error(
                        "Fehler beim Zurücksetzen des Passworts.",
                        position="top-right",
                    )

        finally:
            self.is_loading = False
