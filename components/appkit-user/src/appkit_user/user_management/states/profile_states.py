import re
from typing import Final

import reflex as rx
from reflex.components.sonner.toast import Toaster

from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.user_repository import user_repo
from appkit_user.authentication.states import UserSession

MIN_PASSWORD_LENGTH: Final[int] = 12

# Compile a regex pattern that ensures the password has:
# - At least MIN_PASSWORD_LENGTH characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one digit
# - At least one special character (anything other than letters and digits)
PASSWORD_REGEX = re.compile(
    r"^(?=.{"
    + str(MIN_PASSWORD_LENGTH)
    + r",})(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).*$"
)


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

        if criteria_met == 1:  # noqa: PLR2004
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

    def set_name(self, name: str) -> None:
        self.name = name

    def set_confirm_password(self, password: str) -> None:
        self.confirm_password = password
        if self.new_password != password:
            self.password_error = "Passwörter stimmen nicht überein."  # noqa: S105 # gitleaks:allow
        else:
            self.password_error = ""

    def set_current_password(self, password: str) -> None:
        self.current_password = password

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
