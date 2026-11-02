import reflex as rx

from appkit_user.authentication.backend.services.password_reset_service import (
    ChangePasswordOutcome,
    get_password_reset_service,
)
from appkit_user.authentication.password_policy import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_MISMATCH_MESSAGE,
    PASSWORD_REGEX,
    calculate_password_strength,
)
from appkit_user.authentication.states import UserSession

_CHANGE_PASSWORD_ERRORS: dict[ChangePasswordOutcome, str] = {
    ChangePasswordOutcome.INCORRECT_CURRENT_PASSWORD: "Incorrect current password",
    ChangePasswordOutcome.PASSWORD_REUSED: (
        "This password was used before. Please choose a different one."
    ),
    ChangePasswordOutcome.USER_NOT_FOUND: "User not found",
    ChangePasswordOutcome.INVALID_PASSWORD: "Password does not meet the requirements",
}


class ProfileState(rx.State):
    new_password: str = ""
    confirm_password: str = ""
    current_password: str = ""
    password_error: str = ""
    name: str = ""

    # Strength meter example
    strength_value: int = 0
    has_length: bool = False
    has_upper: bool = False
    has_lower: bool = False
    has_digit: bool = False
    has_special: bool = False

    @rx.event
    def set_new_password(self, value: str) -> None:
        """Set password and calculate strength."""
        self.new_password = value
        result = calculate_password_strength(value)
        self.has_length = result.has_length
        self.has_upper = result.has_upper
        self.has_lower = result.has_lower
        self.has_digit = result.has_digit
        self.has_special = result.has_special
        self.strength_value = result.strength

    def set_name(self, name: str) -> None:
        self.name = name

    @rx.event
    def set_confirm_password(self, password: str) -> None:
        self.confirm_password = password
        if self.new_password != password:
            self.password_error = PASSWORD_MISMATCH_MESSAGE
        else:
            self.password_error = ""

    @rx.event
    def set_current_password(self, password: str) -> None:
        self.current_password = password

    @rx.event
    async def handle_password_update(self) -> rx.event.EventSpec:
        """Change the signed-in user's password.

        Delegates to :class:`PasswordResetService` so this path enforces the
        same policy as the emailed-reset flow: complexity rules, the password
        reuse check, a history entry, and revocation of existing sessions.
        """
        if not PASSWORD_REGEX.match(self.new_password):
            return rx.toast.error(
                "Password must meet the following criteria: "
                f"At least {MIN_PASSWORD_LENGTH} characters, "
                "one UPPERCASE letter, "
                "one lowercase letter, "
                "1 number, "
                "one special! character",
                position="top-right",
            )

        if self.new_password != self.confirm_password:
            return rx.toast.error("New passwords do not match", position="top-right")

        user_session = await self.get_state(UserSession)

        outcome = await get_password_reset_service().change_password(
            user_id=user_session.user_id,
            current_password=self.current_password,
            new_password=self.new_password,
        )

        if outcome is not ChangePasswordOutcome.SUCCESS:
            return rx.toast.error(
                _CHANGE_PASSWORD_ERRORS.get(outcome, "Password could not be updated"),
                position="top-right",
            )

        self.current_password = ""
        self.new_password = ""
        self.confirm_password = ""
        self.has_digit = False
        self.has_length = False
        self.has_lower = False
        self.has_special = False
        self.has_upper = False
        self.strength_value = 0

        return rx.toast.info(
            "Password updated successfully. Please sign in again.",
            position="top-right",
        )
