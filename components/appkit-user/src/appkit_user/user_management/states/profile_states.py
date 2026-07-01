import reflex as rx
from reflex.components.sonner.toast import Toaster

from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.database import user_repo
from appkit_user.authentication.password_policy import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_MISMATCH_MESSAGE,
    PASSWORD_REGEX,
    calculate_password_strength,
)
from appkit_user.authentication.states import UserSession


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
    async def handle_password_update(self) -> Toaster:
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
        user_id = user_session.user_id

        try:
            async with get_asyncdb_session() as session:
                await user_repo.update_password(
                    session,
                    user_id=user_id,
                    old_password=self.current_password,
                    new_password=self.new_password,
                )
        except ValueError:
            return rx.toast.error("Incorrect current password", position="top-right")

        self.current_password = ""
        self.new_password = ""
        self.confirm_password = ""
        self.has_digit = False
        self.has_length = False
        self.has_lower = False
        self.has_special = False
        self.has_upper = False
        self.strength_value = 0

        return rx.toast.info("Password updated successfully", position="top-right")
